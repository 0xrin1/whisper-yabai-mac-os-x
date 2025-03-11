#!/usr/bin/env python3
"""
Simplified standalone dictation daemon.
Uses core dictation functionality with simplified interface.
"""

import os
import sys
import time
import logging
import threading
import whisper
import tempfile
from typing import Optional
from pynput import keyboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("simple-dictation")

# Add import paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our core modules
from src.core.core_dictation import core_dictation
from src.audio.resource_manager import (
    audio_device,
    audio_stream,
    TempAudioFile,
    play_system_sound,
)
from src.config.config import config

# Global variables
RECORDING = False
MODEL = None

# Key tracking state
KEY_STATES = {"ctrl": False, "shift": False, "d": False}


class SimpleAudioRecorder:
    """Records audio from microphone with simplified interface."""

    def start_recording(self, duration: int = 5) -> Optional[str]:
        """
        Start recording audio for specified duration.

        Args:
            duration: Recording duration in seconds

        Returns:
            Path to the recorded audio file, or None if recording failed
        """
        global RECORDING

        if RECORDING:
            logger.warning("Recording already in progress")
            return None

        logger.info(f"Starting recording for {duration} seconds...")
        RECORDING = True

        # Play start sound
        play_system_sound("Tink")

        # Create a temporary WAV file
        temp_file = TempAudioFile(delete=False)

        try:
            with audio_device() as p:
                chunk_size = config.get("CHUNK_SIZE", 1024)

                with audio_stream(
                    p,
                    format=getattr(p, config.get("FORMAT", "paInt16")),
                    channels=config.get("CHANNELS", 1),
                    rate=config.get("RATE", 16000),
                    input=True,
                    frames_per_buffer=chunk_size,
                ) as stream:
                    # Record audio
                    frames = []
                    rate = config.get("RATE", 16000)
                    for i in range(0, int(rate / chunk_size * duration)):
                        if not RECORDING:
                            break
                        try:
                            data = stream.read(chunk_size)
                            frames.append(data)
                        except Exception as e:
                            logger.error(f"Error reading audio data: {e}")
                            RECORDING = False
                            return None

                # Save the recorded data as a WAV file
                import wave

                with wave.open(temp_file.filename, "wb") as wf:
                    wf.setnchannels(config.get("CHANNELS", 1))
                    wf.setsampwidth(
                        p.get_sample_size(getattr(p, config.get("FORMAT", "paInt16")))
                    )
                    wf.setframerate(config.get("RATE", 16000))
                    wf.writeframes(b"".join(frames))

                logger.info(f"Recording saved to {temp_file.filename}")

        except Exception as e:
            logger.error(f"Recording failed: {e}")
            RECORDING = False
            return None

        finally:
            RECORDING = False
            # Play stop sound
            play_system_sound("Basso")

        return temp_file.filename


def transcribe_and_type(audio_file: str) -> None:
    """
    Transcribe audio file using Whisper and type it.

    Args:
        audio_file: Path to audio file to transcribe
    """
    global MODEL

    if MODEL is None:
        logger.info("Loading Whisper model (tiny)...")
        MODEL = whisper.load_model(config.get("MODEL_SIZE", "tiny"))

    logger.info("Transcribing audio...")
    try:
        result = MODEL.transcribe(audio_file)
        text = result["text"].strip()

        logger.info(f"Transcribed: '{text}'")

        if len(text) < 2:
            logger.warning("Transcription too short or empty, ignoring.")
            return

        # Use core dictation to type the text
        success = core_dictation.type_text(text)

        if success:
            logger.info("Text typed successfully")
        else:
            logger.error("Failed to type text")

    except Exception as e:
        logger.error(f"Transcription or typing failed: {e}")
        import traceback

        logger.error(traceback.format_exc())

    finally:
        # Clean up
        try:
            if os.path.exists(audio_file):
                os.remove(audio_file)
                logger.debug(f"Removed temporary file: {audio_file}")
        except Exception as e:
            logger.error(f"Failed to remove temporary file: {e}")


def on_press(key):
    """
    Handle key press events.

    Args:
        key: The key that was pressed

    Returns:
        False to stop listener, None to continue
    """
    try:
        # Update key state
        if (
            key == keyboard.Key.ctrl
            or key == keyboard.Key.ctrl_l
            or key == keyboard.Key.ctrl_r
        ):
            KEY_STATES["ctrl"] = True
        elif (
            key == keyboard.Key.shift
            or key == keyboard.Key.shift_l
            or key == keyboard.Key.shift_r
        ):
            KEY_STATES["shift"] = True
        elif isinstance(key, keyboard.KeyCode):
            if hasattr(key, "char") and key.char and key.char.lower() == "d":
                KEY_STATES["d"] = True

        # Check for dictation hotkey (Ctrl+Shift+D)
        if KEY_STATES["ctrl"] and KEY_STATES["shift"] and KEY_STATES["d"]:
            logger.info("Dictation hotkey detected: Ctrl+Shift+D")

            # Start recording in a separate thread
            def record_and_transcribe():
                recorder = SimpleAudioRecorder()
                audio_file = recorder.start_recording(
                    duration=config.get("DICTATION_TIMEOUT", 5)
                )
                if audio_file:
                    transcribe_and_type(audio_file)

            threading.Thread(target=record_and_transcribe, daemon=True).start()

    except Exception as e:
        logger.error(f"Error in key press handler: {e}")
        import traceback

        logger.error(traceback.format_exc())


def on_release(key):
    """
    Handle key release events.

    Args:
        key: The key that was released

    Returns:
        False to stop listener, None to continue
    """
    try:
        # Update key state
        if (
            key == keyboard.Key.ctrl
            or key == keyboard.Key.ctrl_l
            or key == keyboard.Key.ctrl_r
        ):
            KEY_STATES["ctrl"] = False
        elif (
            key == keyboard.Key.shift
            or key == keyboard.Key.shift_l
            or key == keyboard.Key.shift_r
        ):
            KEY_STATES["shift"] = False
        elif isinstance(key, keyboard.KeyCode):
            if hasattr(key, "char") and key.char and key.char.lower() == "d":
                KEY_STATES["d"] = False
    except Exception as e:
        logger.error(f"Error in key release handler: {e}")

    # Stop listener if escape key is pressed
    if key == keyboard.Key.esc:
        return False


def show_banner():
    """Show application banner and instructions."""
    print("")
    print("┌────────────────────────────────────┐")
    print("│      Simple Dictation Daemon       │")
    print("│                                    │")
    print("│ Press Ctrl+Shift+D to dictate text │")
    print("│ Press ESC to exit                  │")
    print("└────────────────────────────────────┘")
    print("")
    print(f"Using Whisper model: {config.get('MODEL_SIZE', 'tiny')}")
    print(f"Recording duration: {config.get('DICTATION_TIMEOUT', 5)} seconds")
    print("")


if __name__ == "__main__":
    try:
        # Display banner
        show_banner()

        # Start keyboard listener
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)
