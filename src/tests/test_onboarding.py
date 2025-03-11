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
from io import StringIO

# Add the src directory to the path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Mock dotenv to avoid file not found error
sys.modules["dotenv"] = MagicMock()
sys.modules["dotenv.main"] = MagicMock()

# Import the module to test
from src.core.state_manager import StateManager

# Need to patch load_dotenv before importing the daemon
with patch("src.daemon.load_dotenv"):
    from src.daemon import VoiceControlDaemon


class TestOnboarding(unittest.TestCase):
    """Test cases for onboarding conversation feature."""

    @patch("src.daemon.load_dotenv")
    @patch("src.daemon.tts.speak")
    @patch("src.daemon.send_notification")
    def test_onboarding_conversation(self, mock_notify, mock_speak, mock_dotenv):
        """Test that onboarding conversation is triggered on first run."""
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

    @patch("src.daemon.load_dotenv")
    @patch("src.daemon.tts.speak")
    def test_skip_onboarding_on_subsequent_runs(self, mock_speak, mock_dotenv):
        """Test that onboarding is skipped on subsequent runs."""
        # Create a daemon instance
        daemon = VoiceControlDaemon()

        # Mock first_run to be False (subsequent run)
        with patch.object(daemon, "_is_first_run", return_value=False):
            # Call the onboarding method directly
            daemon._show_onboarding_conversation()

            # Check that welcome message was not spoken
            mock_speak.assert_not_called()

    @patch("src.daemon.load_dotenv")
    @patch("os.path.exists")
    def test_first_run_detection(self, mock_exists, mock_dotenv):
        """Test the detection of first run."""
        # Create a daemon instance
        daemon = VoiceControlDaemon()

        # Test when first run file doesn't exist
        mock_exists.return_value = False
        self.assertTrue(daemon._is_first_run())

        # Test when first run file exists
        mock_exists.return_value = True
        self.assertFalse(daemon._is_first_run())

    @patch("src.daemon.load_dotenv")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("os.makedirs")
    def test_mark_as_introduced(
        self, mock_makedirs, mock_open, mock_exists, mock_dotenv
    ):
        """Test marking the system as introduced."""
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
