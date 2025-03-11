#!/usr/bin/env python3
"""
Unit tests for the core_dictation module.
Tests text typing functionality with mocked dependencies.
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCoreDictation(unittest.TestCase):
    """Test core dictation functionality with mocked dependencies."""

    def setUp(self):
        """Set up test fixtures."""
        # Create patches for dependencies
        self.patchers = []

        # Patch config
        self.config_patch = patch("src.core.core_dictation.config")
        self.mock_config = self.config_patch.start()
        self.patchers.append(self.config_patch)

        # Configure mock config
        self.mock_config.get.side_effect = self._mock_config_get

        # Patch subprocesses
        self.subprocess_patch = patch("src.core.core_dictation.subprocess")
        self.mock_subprocess = self.subprocess_patch.start()
        self.patchers.append(self.subprocess_patch)

        # Patch pyautogui - need to patch it at the point of import in each method
        self.pyautogui_patch = patch("pyautogui.hotkey")
        self.mock_pyautogui_hotkey = self.pyautogui_patch.start()
        self.patchers.append(self.pyautogui_patch)

        # Patch pyautogui.write
        self.pyautogui_write_patch = patch("pyautogui.write")
        self.mock_pyautogui_write = self.pyautogui_write_patch.start()
        self.patchers.append(self.pyautogui_write_patch)

        # Patch open
        self.open_patch = patch("builtins.open", mock_open())
        self.mock_open = self.open_patch.start()
        self.patchers.append(self.open_patch)

        # Patch resource_manager
        self.resource_patch = patch("src.audio.resource_manager.play_system_sound")
        self.mock_play_sound = self.resource_patch.start()
        self.patchers.append(self.resource_patch)

        # Patch toast notifications
        self.toast_patch = patch("src.ui.toast_notifications.notify_command_executed")
        self.mock_notify = self.toast_patch.start()
        self.patchers.append(self.toast_patch)

        # Import the module after patching
        from src.core.core_dictation import CoreDictationProcessor

        self.dictation = CoreDictationProcessor()

        # Create a temporary directory for any file operations
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        """Clean up test fixtures."""
        # Stop all patches
        for patcher in self.patchers:
            patcher.stop()

        # Clean up temporary directory
        self.temp_dir.cleanup()

    def _mock_config_get(self, key, default=None):
        """Mock implementation of config.get."""
        config_values = {
            "DICTATION_COMPLETION_SOUND": "Pop",
            "DICTATION_LOG_FILE": "dictation_log.txt",
            "PLAY_COMPLETION_SOUND": True,
            "SHOW_DICTATION_NOTIFICATIONS": True,
            "CLIPBOARD_DELAY": 0.5,
            "TYPING_INTERVAL": 0.03,
        }
        return config_values.get(key, default)

    def test_type_text_applescript_success(self):
        """Test typing text using AppleScript method."""
        # Configure mock subprocess to indicate success
        self.mock_subprocess.run.return_value = MagicMock(returncode=0)

        # Call the function
        result = self.dictation.type_text("Test text")

        # Check results
        self.assertTrue(result)
        self.mock_subprocess.run.assert_called()
        self.mock_open.assert_called()
        self.mock_play_sound.assert_called_with("Pop")
        self.mock_notify.assert_called()

    def test_type_text_applescript_failure(self):
        """Test AppleScript failure with fallback to clipboard."""
        # First call fails, second call succeeds (clipboard method)
        self.mock_subprocess.run.side_effect = [
            MagicMock(returncode=1),  # AppleScript fails
            None,  # pbcopy succeeds
        ]

        # Call the function
        result = self.dictation.type_text("Test text")

        # Check results
        self.assertTrue(result)
        self.assertEqual(self.mock_subprocess.run.call_count, 1)
        self.mock_subprocess.Popen.assert_called()
        self.mock_pyautogui_hotkey.assert_called_with("command", "v")

    def test_type_text_clipboard_failure(self):
        """Test clipboard failure with fallback to pyautogui."""
        # First two methods fail
        self.mock_subprocess.run.return_value = MagicMock(
            returncode=1
        )  # AppleScript fails
        self.mock_subprocess.Popen.side_effect = Exception(
            "Failed to copy"
        )  # pbcopy fails

        # Call the function
        result = self.dictation.type_text("Test text")

        # Check results
        self.assertTrue(result)
        self.mock_pyautogui_write.assert_called_with("Test text", interval=0.03)

    def test_all_methods_fail(self):
        """Test handling when all typing methods fail."""
        # All methods fail
        self.mock_subprocess.run.return_value = MagicMock(
            returncode=1
        )  # AppleScript fails
        self.mock_subprocess.Popen.side_effect = Exception(
            "Failed to copy"
        )  # pbcopy fails
        self.mock_pyautogui_write.side_effect = Exception(
            "PyAutoGUI failed"
        )  # PyAutoGUI fails

        # Call the function
        result = self.dictation.type_text("Test text")

        # Check results
        self.assertFalse(result)

    def test_empty_text(self):
        """Test handling of empty text."""
        # Call with empty text
        result = self.dictation.type_text("")

        # Check results
        self.assertFalse(result)
        self.mock_subprocess.run.assert_not_called()

    def test_logging(self):
        """Test dictation logging functionality."""
        # Configure mocks for success
        self.mock_subprocess.run.return_value = MagicMock(returncode=0)

        # Call with text
        self.dictation.type_text("Test dictation")

        # Check that logging was performed
        self.mock_open.assert_called()
        file_handle = self.mock_open()
        # We now expect the write to be called multiple times due to implementation change
        file_handle.write.assert_called()

        # Check that notification was shown
        self.mock_notify.assert_called_once()

    def test_completion_sound_disabled(self):
        """Test behavior when completion sound is disabled."""
        # Configure config to disable sound
        original_side_effect = self.mock_config.get.side_effect
        self.mock_config.get.side_effect = (
            lambda key, default=None: False
            if key == "PLAY_COMPLETION_SOUND"
            else original_side_effect(key, default)
        )

        # Configure mock for success
        self.mock_subprocess.run.return_value = MagicMock(returncode=0)

        # Call with text
        self.dictation.type_text("Test text")

        # Check that sound was not played
        self.mock_play_sound.assert_not_called()

    def test_notification_disabled(self):
        """Test behavior when notifications are disabled."""
        # Configure config to disable notifications
        original_side_effect = self.mock_config.get.side_effect
        self.mock_config.get.side_effect = (
            lambda key, default=None: False
            if key == "SHOW_DICTATION_NOTIFICATIONS"
            else original_side_effect(key, default)
        )

        # Configure mock for success
        self.mock_subprocess.run.return_value = MagicMock(returncode=0)

        # Call with text
        self.dictation.type_text("Test text")

        # Check that notification was not shown
        self.mock_notify.assert_not_called()

    def test_sound_fallback(self):
        """Test sound playback fallback mechanism."""
        # Make resource_manager.play_system_sound raise an exception
        self.mock_play_sound.side_effect = Exception("Resource manager failed")

        # Configure mock for success
        self.mock_subprocess.run.return_value = MagicMock(returncode=0)

        # Call with text
        self.dictation.type_text("Test text")

        # Check that subprocess was used as fallback
        self.mock_subprocess.run.assert_any_call(
            ["afplay", "/System/Library/Sounds/Pop.aiff"], check=False
        )


if __name__ == "__main__":
    unittest.main()
