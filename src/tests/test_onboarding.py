#!/usr/bin/env python3
"""
Test suite for the onboarding conversation feature.
Tests the welcome dialog and onboarding flow.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import time
import asyncio
from io import StringIO

# Add the src directory to the path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Set testing mode
os.environ["TESTING"] = "true"

# Import test utils
from src.tests.test_utils import MockSpeechRecognitionClient, mock_speech_recognition_client, mock_asyncio_new_event_loop

# Mock dotenv to avoid file not found error
sys.modules["dotenv"] = MagicMock()
sys.modules["dotenv.main"] = MagicMock()

# Import the module to test
from src.core.state_manager import StateManager

# Create mock for the AudioProcessor
mock_processor = MagicMock()
sys.modules["src.audio.audio_processor"] = MagicMock()
sys.modules["src.audio.audio_processor"].processor = mock_processor
sys.modules["src.audio.audio_processor"].AudioProcessor = MagicMock()

# Apply patches before importing the daemon
with patch("src.daemon.load_dotenv"):
    from src.daemon import VoiceControlDaemon


class TestOnboarding(unittest.TestCase):
    """Test cases for onboarding conversation feature."""

    @patch("src.daemon.tts.speak")
    @patch("src.daemon.send_notification")
    def test_onboarding_conversation(self, mock_notify, mock_speak):
        """Test that onboarding conversation is triggered on first run."""
        # Apply patches for Speech Recognition API
        with mock_speech_recognition_client(), mock_asyncio_new_event_loop():
            # Create a daemon with onboarding enabled
            daemon = VoiceControlDaemon()

            # Mock first_run to be True
            with patch.object(daemon, "_is_first_run", return_value=True):
                # Mock the time.sleep function to speed up the test
                with patch("time.sleep"):
                    # Call the onboarding method directly
                    daemon._show_onboarding_conversation()

                    # Check that the welcome message was spoken
                    self.assertTrue(mock_speak.called)
                    welcome_call = mock_speak.call_args_list[0]
                    self.assertIn("Welcome to Voice Control", welcome_call[0][0])

                    # Verify notification was displayed
                    self.assertTrue(mock_notify.called)
                    self.assertIn("Voice Control Welcome", mock_notify.call_args[0][0])

    @patch("src.daemon.tts.speak")
    def test_skip_onboarding_on_subsequent_runs(self, mock_speak):
        """Test that onboarding is skipped on subsequent runs."""
        # Apply patches for Speech Recognition API
        with mock_speech_recognition_client(), mock_asyncio_new_event_loop():
            # Create a daemon instance
            daemon = VoiceControlDaemon()

            # Mock first_run to be False (subsequent run)
            with patch.object(daemon, "_is_first_run", return_value=False):
                # Call the onboarding method directly
                daemon._show_onboarding_conversation()

                # Check that welcome message was not spoken
                mock_speak.assert_not_called()

    @patch("os.path.exists")
    def test_first_run_detection(self, mock_exists):
        """Test the detection of first run."""
        # Apply patches for Speech Recognition API
        with mock_speech_recognition_client(), mock_asyncio_new_event_loop():
            # Create a daemon instance
            daemon = VoiceControlDaemon()

            # Test when first run file doesn't exist
            mock_exists.return_value = False
            self.assertTrue(daemon._is_first_run())

            # Test when first run file exists
            mock_exists.return_value = True
            self.assertFalse(daemon._is_first_run())

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("os.makedirs")
    def test_mark_as_introduced(
        self, mock_makedirs, mock_open, mock_exists
    ):
        """Test marking the system as introduced."""
        # Apply patches for Speech Recognition API
        with mock_speech_recognition_client(), mock_asyncio_new_event_loop():
            # Set up the test
            mock_exists.return_value = False

            # Create a daemon instance
            daemon = VoiceControlDaemon()

            # Call the method
            daemon._mark_as_introduced()

            # Verify the file was created
            mock_makedirs.assert_called_once()
            mock_open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
