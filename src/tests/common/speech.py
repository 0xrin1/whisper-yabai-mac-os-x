"""
Speech synthesis and playback utilities for testing.
Provides common speech functions used across test cases.
"""

import os
import logging
import subprocess

from src.config.config import config
from src.tests.common.mocks import should_skip_audio_playback

logger = logging.getLogger(__name__)


def synthesize_speech(text, voice_id=None):
    """Generate speech audio file from text using neural TTS API.

    Args:
        text (str): Text to convert to speech
        voice_id (str, optional): Voice ID to use for synthesis (defaults to NEURAL_VOICE_ID from config)

    Returns:
        str: Path to generated audio file
    """
    from src.audio import speech_synthesis as tts

    # Get default voice ID from config if not specified
    if voice_id is None:
        voice_id = config.get("NEURAL_VOICE_ID", "p230")

    logger.info(f"Synthesizing '{text}' using neural voice '{voice_id}'")

    # Generate the audio file using our neural speech synthesis
    audio_file = tts._call_speech_api(
        text,
        voice_id=voice_id,
        speed=1.0,
        use_high_quality=True,
        enhance_audio=True
    )

    if not audio_file:
        logger.error("Failed to synthesize speech")
        return None

    logger.info(f"Generated speech for '{text}' at {audio_file}")
    return audio_file


def play_audio_file(file_path, volume=2):
    """Play an audio file with specified volume.

    Args:
        file_path (str): Path to the audio file
        volume (int, optional): Volume level (1-2)
    """
    logger.info(f"Playing audio file: {file_path} at volume {volume}")

    if should_skip_audio_playback():
        logger.info("Audio playback skipped based on environment setting")
        return

    # Use afplay for more reliable playback
    subprocess.run(["afplay", "-v", str(volume), file_path], check=True)


def synthesize_and_play(text, voice_id=None, volume=2):
    """Synthesize speech using neural TTS and play it.

    Args:
        text (str): Text to convert to speech
        voice_id (str, optional): Voice ID to use for synthesis
        volume (int, optional): Volume level for playback

    Returns:
        str: Path to the generated audio file
    """
    audio_file = synthesize_speech(text, voice_id)
    if audio_file:
        play_audio_file(audio_file, volume)
    return audio_file
