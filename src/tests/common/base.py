"""
Base test classes and utilities for test organization.
Provides common test classes with shared setup/teardown and utility methods.
"""

import os
import sys
import time
import tempfile
import logging
import subprocess
import unittest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.config.config import config
from src.tests.common.mocks import should_skip_audio_playback

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AsyncTestCase:
    """Base class for tests that need to run async code without pytest-asyncio."""

    def run_async(self, coro):
        """Run an async coroutine in a test."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)


# Daemon management utilities
class DaemonManager:
    """Manages a daemon process for testing"""

    def __init__(self, log_dir=None, capture_output=True):
        """Initialize the daemon manager

        Args:
            log_dir (str, optional): Directory for log files
            capture_output (bool): Whether to capture daemon output
        """
        self.daemon = None
        self.output_file = None
        self.log_dir = log_dir
        self.capture_output = capture_output

        if self.log_dir:
            self.daemon_output_file = os.path.join(self.log_dir, "daemon_output.log")
        else:
            self.daemon_output_file = os.path.join(
                tempfile.gettempdir(), f"daemon_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )

    def start(self, wait_time=8):
        """Start the daemon process

        Args:
            wait_time (int): Initial time to wait for initialization

        Returns:
            tuple: (subprocess.Popen, file_handle)
        """
        logger.info("Starting daemon in background...")

        if self.capture_output:
            # Open file for capturing output
            self.output_file = open(self.daemon_output_file, "w")

            # Start the daemon process
            self.daemon = subprocess.Popen(
                ["python", "src/daemon.py"],
                stdout=self.output_file,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
        else:
            # Start with pipe to read output in tests
            self.daemon = subprocess.Popen(
                ["python", "src/daemon.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

        # Initial wait for daemon to start loading models
        logger.info(f"Initial wait for {wait_time} seconds...")
        time.sleep(wait_time)

        # Now poll for readiness instead of just waiting
        logger.info("Checking if daemon is ready for input...")
        max_wait = 15  # Maximum additional wait time
        poll_interval = 1  # Check every second
        start_time = time.time()
        ready = False

        while time.time() - start_time < max_wait:
            # Check if the daemon output contains a listening indicator
            if self.capture_output:
                with open(self.daemon_output_file, "r") as f:
                    content = f.read()
                    if "speech recognition api connection successful" in content.lower() or "ready for input" in content.lower():
                        ready = True
                        break

            # Short sleep before checking again
            time.sleep(poll_interval)

        if ready:
            logger.info(f"Daemon ready after {time.time() - start_time + wait_time:.1f} seconds")
        else:
            logger.info("Proceeding with tests after waiting for daemon initialization")

        return self.daemon, self.output_file

    def stop(self):
        """Stop the daemon process"""
        if not self.daemon:
            return

        logger.info("Stopping daemon...")

        # Terminate the daemon
        self.daemon.terminate()
        try:
            self.daemon.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.daemon.kill()
            logger.warning("Had to forcefully kill daemon")

        # Close output file
        if self.output_file:
            try:
                if not self.output_file.closed:
                    self.output_file.close()
            except:
                pass

        self.daemon = None
        self.output_file = None

    def check_output(self, text, timeout=10):
        """Check if text appears in daemon output file.

        Args:
            text (str): Text to search for
            timeout (int, optional): Maximum time to wait

        Returns:
            bool: True if text found, False otherwise
        """
        start_time = time.time()

        if self.capture_output:
            # Read from output file
            while time.time() - start_time < timeout:
                with open(self.daemon_output_file, "r") as f:
                    content = f.read()

                if text in content:
                    logger.info(f"Found '{text}' in daemon output")
                    return True

                time.sleep(0.5)
        else:
            # Read from stdout pipe
            while time.time() - start_time < timeout:
                try:
                    line = self.daemon.stdout.readline()
                    if text in line:
                        return True
                except (IOError, AttributeError):
                    # Handle case where stdout might be closed
                    break
                time.sleep(0.1)

        logger.warning(f"Text '{text}' not found in daemon output after {timeout} seconds")
        return False

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


class BaseTestCase(unittest.TestCase):
    """Base class for all test cases with common setup/teardown"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests in the class."""
        # Save temp files for cleanup
        cls.temp_files = []

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests in the class."""
        # Clean up temp files
        for temp_file in cls.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_file}: {e}")


class BaseVoiceTest(BaseTestCase):
    """Base class for voice control tests with common setup/teardown"""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment"""
        super().setUpClass()

        # Create log directory structure
        logs_base_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "logs",
            "test_logs",
        )
        os.makedirs(logs_base_dir, exist_ok=True)

        cls.log_dir = os.path.join(
            logs_base_dir, f"test_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(cls.log_dir, exist_ok=True)

    def synthesize_speech(self, text, voice_id=None):
        """Generate speech audio file from text and track for cleanup.

        Args:
            text (str): Text to convert to speech
            voice_id (str, optional): Voice ID to use for synthesis

        Returns:
            str: Path to the generated audio file
        """
        from src.tests.common.speech import synthesize_speech

        audio_file = synthesize_speech(text, voice_id)
        if audio_file:
            self.temp_files.append(audio_file)
        return audio_file

    def play_audio_file(self, file_path, volume=2):
        """Play an audio file with specified volume.

        Args:
            file_path (str): Path to the audio file
            volume (int, optional): Volume level (1-2)
        """
        if should_skip_audio_playback():
            logger.info("Audio playback skipped based on environment setting")
            return

        from src.tests.common.speech import play_audio_file
        play_audio_file(file_path, volume)

    def synthesize_and_play(self, text, voice_id=None, volume=2):
        """Synthesize speech and play it, tracking the file for cleanup.

        Args:
            text (str): Text to convert to speech
            voice_id (str, optional): Voice ID to use for synthesis
            volume (int, optional): Volume level for playback

        Returns:
            str: Path to the generated audio file
        """
        audio_file = self.synthesize_speech(text, voice_id)
        if audio_file:
            self.play_audio_file(audio_file, volume)
        return audio_file
