#!/usr/bin/env python3
"""
Trigger word detection module for voice control system.
Detects command and dictation trigger words in audio.
"""

import os
import time
import threading
import subprocess
import tempfile
import wave
import logging
import whisper
import torch
import numpy as np

from src.core.state_manager import state
from src.audio.audio_recorder import AudioRecorder

logger = logging.getLogger("trigger-detection")


class TriggerDetector:
    """Detects trigger words in audio to activate command or dictation modes."""

    def __init__(self, whisper_model=None):
        """Initialize the trigger detector.

        Args:
            whisper_model: Pre-loaded Whisper model to use (will load if not provided)
        """
        self.whisper_model = whisper_model
        self.recorder = AudioRecorder()

        # Trigger word variations for more robust detection
        # Command mode is now triggered by Jarvis
        self.command_variations = [
            "jarvis",
            "hey jarvis",
            "hi jarvis",
            "hello jarvis",
            "ok jarvis",
            "hey jarvis",
            "jarvis please",
        ]

        # Keep dictation variations for explicit dictation trigger
        # (though dictation is now the default mode)
        self.dictation_variations = [
            state.dictation_trigger.lower(),
            "typing",
            "write",
            "note",
            "text",
            "speech to text",
            "tight",
            "tipe",
            "types",
            "typed",
            "typ",
            "tape",
            "time",
            "tip",
            "tie",
            "type please",
            "please type",
            "start typing",
            "begin typing",
            "activate typing",
            "time please",
            "time this",
            "type this",
            "dictate",
            "dictation",
            "take dictation",
            "start dictation",
            "dictate this",
            "write this",
            "take notes",
            "ti",
            "ty",
            "tai",
        ]

        # Jarvis variations are now the same as command variations
        self.jarvis_variations = self.command_variations

    def ensure_model(self):
        """Ensure Whisper model is loaded."""
        if self.whisper_model is None:
            try:
                logger.info(f"Loading Whisper model: {state.model_size}")
                self.whisper_model = whisper.load_model(state.model_size)
                logger.info("Whisper model loaded successfully")
                # Update global state
                state.whisper_model = self.whisper_model
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise

    def process_audio_buffer(self, audio_buffer):
        """Process audio buffer to detect trigger words.

        Args:
            audio_buffer: List of audio frames to process

        Returns:
            dict: Detection results with trigger type and transcription
        """
        if not audio_buffer or len(audio_buffer) < 10:
            logger.debug("Buffer too small to process")
            return {"detected": False}

        # Ensure model is loaded
        self.ensure_model()

        logger.debug(f"Processing audio buffer with {len(audio_buffer)} frames")

        # Save buffer to a temporary WAV file
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_filename = temp_file.name
            temp_file.close()

            wf = wave.open(temp_filename, "wb")
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)  # 16kHz

            # Join frames and write to file
            joined_frames = b"".join(audio_buffer)
            wf.writeframes(joined_frames)
            wf.close()

            logger.debug(f"Audio buffer saved to {temp_filename}")

            # Use Whisper to transcribe the buffer with context clearing
            try:
                # Create fresh transcription options to prevent context accumulation
                result = self.whisper_model.transcribe(
                    temp_filename,
                    language="en",
                    fp16=False,
                    initial_prompt=None,  # Explicitly clear prompt context
                )
                # Force memory cleanup to prevent context accumulation
                torch.cuda.empty_cache() if hasattr(
                    torch, "cuda"
                ) and torch is not None else None
                transcription = result["text"].strip().lower()
            except Exception as e:
                logger.error(f"Error during buffer transcription: {e}")
                # Try to reload the model if transcription failed
                try:
                    logger.debug("Attempting to reload Whisper model due to error")
                    self.whisper_model = whisper.load_model(state.model_size)
                    state.whisper_model = self.whisper_model
                    # Retry transcription with fresh model
                    result = self.whisper_model.transcribe(
                        temp_filename, language="en", fp16=False
                    )
                    transcription = result["text"].strip().lower()
                except Exception as reload_err:
                    logger.error(f"Failed to reload model: {reload_err}")
                    return {"detected": False}

            logger.debug(f"Buffer transcription: '{transcription}'")

            # Check for trigger words
            detection_result = self.detect_triggers(transcription)

            # Clean up the temporary file
            try:
                os.unlink(temp_filename)
            except Exception as e:
                logger.debug(f"Failed to delete temp file: {e}")

            return detection_result

        except Exception as e:
            logger.error(f"Error processing audio buffer: {e}")
            return {"detected": False}

    def detect_triggers(self, transcription):
        """Detect trigger words in transcription.

        Args:
            transcription: Transcribed text to check for trigger words

        Returns:
            dict: Detection results with trigger type and transcription
        """
        result = {
            "detected": True,  # Default to detected as we'll use dictation by default
            "transcription": transcription,
            "trigger_type": "dictation",  # Default to dictation mode
        }

        # Check for command/JARVIS trigger (same list now)
        contains_command_trigger = any(
            variation in transcription.lower() for variation in self.command_variations
        )

        # Check for explicit dictation trigger (still supported but now optional)
        contains_dictation_trigger = False
        for variation in self.dictation_variations:
            # Full exact match
            if variation == transcription.lower().strip():
                logger.debug(f"EXACT MATCH found for '{variation}'")
                contains_dictation_trigger = True
                break

            # Word boundary match - the trigger word surrounded by spaces or at start/end
            if (
                f" {variation} " in f" {transcription.lower()} "
                or transcription.lower().startswith(f"{variation} ")
                or transcription.lower().endswith(f" {variation}")
            ):
                logger.debug(
                    f"WORD BOUNDARY MATCH found for '{variation}' in '{transcription}'"
                )
                contains_dictation_trigger = True
                break

            # Check for substring match
            if variation in transcription.lower():
                logger.debug(
                    f"SUBSTRING MATCH found for '{variation}' in '{transcription}'"
                )
                contains_dictation_trigger = True
                break

        # Process command/JARVIS trigger (has priority over the default dictation mode)
        if contains_command_trigger:
            logger.info(f"Command/JARVIS trigger detected: '{transcription}'")
            result["trigger_type"] = "command"
        # Process explicit dictation trigger (not strictly necessary since it's the default)
        elif contains_dictation_trigger:
            logger.info(f"Explicit dictation trigger detected: '{transcription}'")
            result["trigger_type"] = "dictation"
        # Otherwise use dictation as the default
        else:
            logger.info(f"No specific trigger detected, defaulting to dictation mode: '{transcription}'")
            result["trigger_type"] = "dictation"

        return result

    def handle_detection(self, detection_result):
        """Handle a detected trigger by starting appropriate mode.

        Args:
            detection_result: Dict with detection results

        Returns:
            bool: True if trigger was handled, False otherwise
        """
        if not detection_result["detected"]:
            return False

        trigger_type = detection_result["trigger_type"]
        transcription = detection_result["transcription"]

        # Now "command" and "jarvis" are the same - both activated by saying "jarvis"
        if trigger_type == "command":
            # Play a notification sound
            self.recorder.play_sound("command")

            # Add a notification to show we're listening for a command
            try:
                from src.ui.toast_notifications import send_notification

                send_notification(
                    "Command Mode Activated",
                    "Listening for your command...",
                    "whisper-command-direct",
                    3,
                    False,
                )
            except Exception as e:
                logger.error(f"Failed to show command notification: {e}")

            # Start command mode
            self._start_recording_thread("command", force=True)
            return True

        # Everything else defaults to dictation mode (including explicit dictation triggers)
        else:
            # Play the dictation sound
            self.recorder.play_sound("dictation")

            # Add a notification to clearly show we're entering dictation mode
            try:
                from src.ui.toast_notifications import send_notification

                send_notification(
                    "Dictation Mode Activated",
                    "Everything you say will be typed as text",
                    "whisper-dictation-direct",
                    3,
                    True,
                )
            except Exception as e:
                logger.error(f"Failed to show dictation notification: {e}")

            # Start dictation mode
            self._start_recording_thread("dictation", force=True)
            return True

    def _start_recording_thread(self, mode, force=False):
        """Start a recording thread with specified mode.

        Args:
            mode: Either 'command' or 'dictation'
            force: If True, will force start recording even if already recording
        """
        # Normalize the mode parameter
        if mode.lower() in ["dictate", "dictation", "typing"]:
            mode = "dictation"
        else:
            mode = "command"

        # Check if muted
        if state.is_muted():
            logger.debug(f"Microphone is muted, ignoring {mode} request")
            return

        is_dictation = mode == "dictation"
        mode_name = "Dictation" if is_dictation else "Command"

        logger.info(f"{mode_name} mode triggered - starting voice recording...")

        def recording_thread_func():
            logger.debug(f"Starting {mode_name.lower()} recording")

            try:
                # Ensure recording completes before this function returns
                result = self.recorder.start_recording(
                    dictation_mode=is_dictation, force=force
                )
                logger.debug(f"{mode_name} recording completed, audio file: {result}")
            except Exception as e:
                logger.error(f"Error in recording thread: {e}")
                import traceback

                logger.error(traceback.format_exc())

        # Create a thread that will block until recording is complete
        thread = threading.Thread(target=recording_thread_func)
        thread.daemon = True
        thread.start()

        logger.debug(f"{mode_name} recording thread started: {thread.name}")

        # Add a small delay to ensure thread starts properly
        time.sleep(0.7)
