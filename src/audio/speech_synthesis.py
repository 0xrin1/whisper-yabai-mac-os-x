#!/usr/bin/env python3
"""
External API-based speech synthesis module.
Provides TTS capabilities by calling an external API for speech generation.
"""

import os
import sys
import requests
import subprocess
import threading
import time
import random
import logging
import tempfile
from typing import Optional, Dict, Any, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("speech-synthesis")

# API configuration
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:6000")
TTS_ENDPOINT = f"{SERVER_URL}/tts"

# Track if speech is currently in progress
_speaking_lock = threading.Lock()
_currently_speaking = False

# Queue for speech requests to prevent overlapping
_speech_queue = []
_queue_lock = threading.Lock()
_queue_thread = None
_queue_running = False

# Casual responses for common interactions
CASUAL_RESPONSES = {
    "greeting": [
        "Hello there.",
        "Hi, how can I help?",
        "Hello. What can I do for you?",
        "Hey there. I'm listening.",
    ],
    "acknowledgment": [
        "Got it.",
        "I'm on it.",
        "Working on that now.",
        "Right away.",
        "Consider it done.",
    ],
    "confirmation": [
        "That's done.",
        "I've completed that task.",
        "All finished.",
        "Task complete.",
    ],
    "thinking": [
        "Let me think about that...",
        "Processing...",
        "Working on it...",
        "Give me a moment...",
        "Analyzing your request...",
    ],
    "uncertainty": [
        "I'm not sure about that.",
        "I didn't quite catch that.",
        "Could you rephrase that?",
        "I'm not sure how to help with that.",
    ],
    "farewell": [
        "Goodbye for now.",
        "Signing off.",
        "Let me know if you need anything else.",
        "I'll be here if you need me.",
    ],
}


def is_speaking() -> bool:
    """Check if speech is currently in progress.

    Returns:
        Boolean indicating if speech is in progress
    """
    with _speaking_lock:
        return _currently_speaking


def stop_speaking() -> None:
    """Stop all current and queued speech."""
    global _queue_running

    logger.info("Stopping all speech output")

    # Clear the speech queue
    with _queue_lock:
        _speech_queue.clear()
        _queue_running = False


def _call_speech_api(
    text: str,
    voice_id: str = "p230",
    speed: float = 1.0,
    use_high_quality: bool = True,
    enhance_audio: bool = True,
) -> Optional[str]:
    """Call external API to synthesize speech.

    Args:
        text: Text to synthesize
        voice_id: Speaker ID for the VITS model
        speed: Speech speed factor (0.5 to 2.0)
        use_high_quality: Whether to use highest quality settings
        enhance_audio: Whether to apply additional GPU-based audio enhancement

    Returns:
        Path to audio file or None if failed
    """
    if not text:
        return None

    try:
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        # Call the API using POST method with JSON body
        headers = {"Content-Type": "application/json"}
        payload = {
            "text": text,
            "voice_id": voice_id,
            "speed": speed,
            "use_high_quality": use_high_quality,
            "enhance_audio": enhance_audio,
        }

        logger.debug(f"Calling speech API with text: '{text}'")

        response = requests.post(
            TTS_ENDPOINT, headers=headers, json=payload, timeout=10
        )

        if response.status_code != 200:
            logger.error(
                f"API call failed with status {response.status_code}: {response.text}"
            )
            return None

        # Save the audio to the temporary file
        with open(temp_path, "wb") as f:
            f.write(response.content)

        logger.debug(f"Speech saved to {temp_path}")
        return temp_path

    except Exception as e:
        logger.error(f"Error in API call: {e}")
        return None


def _play_audio(file_path: str) -> bool:
    """Play an audio file using system commands.

    Args:
        file_path: Path to the audio file

    Returns:
        Boolean indicating success
    """
    if not file_path or not os.path.exists(file_path):
        return False

    try:
        # Use platform-specific commands to play audio
        if sys.platform == "darwin":  # macOS
            subprocess.run(["afplay", file_path], check=True)
        elif sys.platform.startswith("linux"):
            subprocess.run(["aplay", file_path], check=True)
        elif sys.platform == "win32":
            subprocess.run(
                [
                    "powershell",
                    "-c",
                    f"(New-Object Media.SoundPlayer '{file_path}').PlaySync();",
                ],
                check=True,
            )
        else:
            logger.error(f"Unsupported platform: {sys.platform}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        return False
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error removing temporary file: {e}")


def _process_speech_queue() -> None:
    """Process the speech queue in a background thread."""
    global _queue_running, _currently_speaking

    logger.debug("Starting speech queue processing thread")

    while True:
        speech_request = None

        # Get the next item from the queue
        with _queue_lock:
            if not _speech_queue:
                _queue_running = False
                break

            speech_request = _speech_queue.pop(0)

        if speech_request:
            # Mark as speaking
            with _speaking_lock:
                _currently_speaking = True

            # Generate and play speech
            try:
                # Handle both string and dict formats for backward compatibility
                if isinstance(speech_request, str):
                    audio_file = _call_speech_api(speech_request)
                else:
                    text = speech_request.get("text", "")
                    voice_id = speech_request.get("voice_id", "p230")
                    speed = speech_request.get("speed", 1.0)
                    use_high_quality = speech_request.get("use_high_quality", True)
                    enhance_audio = speech_request.get("enhance_audio", True)

                    audio_file = _call_speech_api(
                        text,
                        voice_id=voice_id,
                        speed=speed,
                        use_high_quality=use_high_quality,
                        enhance_audio=enhance_audio,
                    )

                if audio_file:
                    _play_audio(audio_file)

            except Exception as e:
                logger.error(f"Error in speech synthesis: {e}")

            # Mark as not speaking
            with _speaking_lock:
                _currently_speaking = False

    logger.debug("Speech queue processing thread finished")


def speak(
    text: str,
    voice: str = "p230",
    rate: float = 1.0,
    use_high_quality: bool = True,
    enhance_audio: bool = True,
    block: bool = False,
) -> bool:
    """Synthesize speech using the external API.

    Args:
        text: Text to speak
        voice: Voice ID for the model (default "p230")
        rate: Speaking rate factor (0.5 to 2.0)
        use_high_quality: Whether to use highest quality settings
        enhance_audio: Whether to apply additional GPU-based audio enhancement
        block: Whether to block until speech is complete

    Returns:
        Boolean indicating success
    """
    if not text:
        return False

    logger.debug(f"Adding to speech queue: '{text}'")

    # Store speech parameters with the text
    speech_request = {
        "text": text,
        "voice_id": voice,
        "speed": rate,
        "use_high_quality": use_high_quality,
        "enhance_audio": enhance_audio,
    }

    # Add to queue
    with _queue_lock:
        _speech_queue.append(speech_request)

        # Start queue processing thread if not already running
        global _queue_running, _queue_thread
        if not _queue_running:
            _queue_running = True
            _queue_thread = threading.Thread(target=_process_speech_queue, daemon=True)
            _queue_thread.start()

    # If blocking, wait until speech is complete
    if block:
        while is_speaking() or (_queue_running and len(_speech_queue) > 0):
            time.sleep(0.1)

    return True


def speak_random(
    category: str,
    voice: str = "p230",
    rate: float = 1.0,
    use_high_quality: bool = True,
    enhance_audio: bool = True,
    block: bool = False,
) -> bool:
    """Speak a random response from a category.

    Args:
        category: Response category (greeting, acknowledgment, etc.)
        voice: Voice ID for the model (default "p230")
        rate: Speaking rate factor (0.5 to 2.0)
        use_high_quality: Whether to use highest quality settings
        enhance_audio: Whether to apply additional GPU-based audio enhancement
        block: Whether to block until speech is complete

    Returns:
        Boolean indicating success
    """
    if category not in CASUAL_RESPONSES:
        logger.warning(f"Unknown response category: {category}")
        return False

    responses = CASUAL_RESPONSES[category]
    selected = random.choice(responses)

    return speak(
        selected,
        voice=voice,
        rate=rate,
        use_high_quality=use_high_quality,
        enhance_audio=enhance_audio,
        block=block,
    )


# Initialize module
logger.info(f"Speech synthesis module initialized with TTS endpoint: {TTS_ENDPOINT}")
