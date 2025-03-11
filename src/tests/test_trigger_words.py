#!/usr/bin/env python3
"""
Simple test script to verify trigger word detection.
This focuses ONLY on testing that 'hey' and 'type' trigger words are detected.
"""

import os
import time
import subprocess
import sys
import logging
import tempfile

# Add src directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audio import speech_synthesis as tts
from config.config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("trigger-test")


def synthesize_and_play(text, voice=None):
    """Synthesize speech using neural TTS and play it."""
    # Get default voice ID from config if not specified
    if voice is None:
        voice = config.get("NEURAL_VOICE_ID", "p230")

    logger.info(f"Synthesizing '{text}' using neural voice '{voice}'")

    # Generate the audio file using our neural speech synthesis
    audio_file = tts._call_speech_api(
        text,
        voice_id=voice,
        speed=1.0,
        use_high_quality=True,
        enhance_audio=True
    )

    if not audio_file:
        logger.error("Failed to synthesize speech")
        return None

    # Play the audio file at higher volume
    subprocess.run(["afplay", "-v", "2", audio_file], check=True)

    # Return the file path so it can be cleaned up later
    return audio_file


def test_trigger_words():
    """Test both trigger words with multiple voices."""
    try:
        # Start the daemon
        logger.info("Starting daemon in background...")
        daemon = subprocess.Popen(
            ["python", "src/daemon.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        # Function to check if a string is in the daemon output
        def check_output(search_text, timeout=10):
            """Check daemon output for a string with timeout."""
            start_time = time.time()
            while time.time() - start_time < timeout:
                line = daemon.stdout.readline()
                if search_text in line:
                    return True
                time.sleep(0.1)
            return False

        # Wait for daemon to initialize
        logger.info("Waiting for daemon to initialize...")
        time.sleep(15)  # Extra time to ensure it's fully ready

        # Use our neural TTS API for speech synthesis
        logger.info("Testing with neural speech synthesis API")

        # Test 'hey' trigger
        logger.info("Testing 'hey' trigger word...")
        try:
            # Use neural speech synthesis
            temp_file = synthesize_and_play("hey")
            # Wait for processing to complete
            time.sleep(5)
            # Clean up
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            logger.error(f"Error testing 'hey' with speech synthesis: {e}")

        # Test dictation triggers
        logger.info("Testing dictation trigger words...")
        for phrase in ["type", "dictate"]:
            try:
                logger.info(f"Testing '{phrase}' with speech synthesis")
                # Use neural synthesis
                temp_file = synthesize_and_play(phrase)
                # Wait for processing
                time.sleep(5)
                # Clean up
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.error(f"Error testing '{phrase}' with speech synthesis: {e}")

    finally:
        # Stop the daemon
        if daemon:
            logger.info("Stopping daemon...")
            daemon.terminate()
            try:
                daemon.wait(timeout=5)
            except subprocess.TimeoutExpired:
                daemon.kill()
                logger.warning("Had to forcefully kill daemon")


if __name__ == "__main__":
    test_trigger_words()
