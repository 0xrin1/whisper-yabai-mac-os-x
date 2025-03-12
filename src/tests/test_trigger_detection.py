#!/usr/bin/env python3
"""
Unit tests for the trigger detection module.
Tests the trigger detector's ability to detect trigger words and activate the appropriate mode.
"""

import os
import sys
import tempfile
import unittest
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Set testing mode
os.environ["TESTING"] = "true"

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import test utilities
from src.tests.test_utils import (
    MockSpeechRecognitionClient,
    mock_speech_recognition_client,
    mock_asyncio_new_event_loop
)

# Import the module
from src.audio.trigger_detection import TriggerDetector
from src.core.state_manager import state


class TestTriggerDetection(unittest.TestCase):
    """Test trigger word detection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create patches for dependencies
        self.patchers = []

        # Use the improved mock speech client from test_utils
        self.client_patch = mock_speech_recognition_client()
        self.MockClient = self.client_patch.start()
        self.mock_speech_client = MockSpeechRecognitionClient()
        self.patchers.append(self.client_patch)

        # Use the improved asyncio loop mock from test_utils
        self.loop_patch = mock_asyncio_new_event_loop()
        self.mock_loop_func = self.loop_patch.start()
        self.patchers.append(self.loop_patch)

        # State manager
        self.state_patch = patch("src.audio.trigger_detection.state")
        self.mock_state = self.state_patch.start()
        self.mock_state.dictation_trigger = "type"
        self.patchers.append(self.state_patch)

        # Audio recorder
        self.recorder_patch = patch("src.audio.trigger_detection.AudioRecorder")
        self.mock_recorder = MagicMock()
        self.recorder_patch.start().return_value = self.mock_recorder
        self.patchers.append(self.recorder_patch)

        # Import and mock CloudCodeHandler only during handle_detection
        # This avoids issues with importing in the setUp() method
        self.mock_cloud_code = MagicMock()

        # Speech synthesis (patched at the source module)
        self.speak_patch = patch("src.audio.speech_synthesis.speak")
        self.mock_speak = self.speak_patch.start()
        self.patchers.append(self.speak_patch)

        # Notifications (patched at the source module)
        self.send_notification_patch = patch("src.ui.toast_notifications.send_notification")
        self.mock_send_notification = self.send_notification_patch.start()
        self.patchers.append(self.send_notification_patch)

        # Error notifications
        self.notify_error_patch = patch("src.ui.toast_notifications.notify_error")
        self.mock_notify_error = self.notify_error_patch.start()
        self.patchers.append(self.notify_error_patch)

        # Now create the detector
        self.detector = TriggerDetector()

        # Create a temporary audio buffer for tests
        self.audio_buffer = [bytes([i % 256]) for i in range(1000)]

    def tearDown(self):
        """Clean up test fixtures."""
        # Stop all patches
        for patcher in self.patchers:
            patcher.stop()

    def test_detect_jarvis_trigger(self):
        """Test detection of the Jarvis trigger word."""
        # Test exact match
        result = self.detector.detect_triggers("jarvis help me with this")

        self.assertTrue(result["detected"])
        self.assertEqual(result["trigger_type"], "cloud_code")
        self.assertEqual(result["transcription"], "help me with this")

        # Test with prefix
        result = self.detector.detect_triggers("hey jarvis what time is it")

        self.assertTrue(result["detected"])
        self.assertEqual(result["trigger_type"], "cloud_code")
        self.assertEqual(result["transcription"], "what time is it")

    def test_default_dictation_mode(self):
        """Test the default dictation mode when no trigger is detected."""
        result = self.detector.detect_triggers("this is some dictation text")

        self.assertTrue(result["detected"])
        self.assertEqual(result["trigger_type"], "dictation")
        self.assertEqual(result["transcription"], "this is some dictation text")

    def test_process_audio_buffer(self):
        """Test processing an audio buffer for trigger detection."""
        # Configure the mock client response
        self.MockClient.return_value.transcribe_audio_data.return_value = {
            "text": "hey jarvis what is the weather",
            "confidence": 0.95,
            "processing_time": 0.2
        }

        # Process the buffer
        result = self.detector.process_audio_buffer(self.audio_buffer)

        # Verify results
        self.assertTrue(result["detected"])
        self.assertEqual(result["trigger_type"], "cloud_code")
        self.assertEqual(result["transcription"], "what is the weather")

    def test_process_audio_buffer_error(self):
        """Test error handling in process_audio_buffer."""
        # Make the mock client raise an exception
        self.MockClient.return_value.check_connection.side_effect = Exception("API unavailable")

        # Process the buffer - should handle the error gracefully
        result = self.detector.process_audio_buffer(self.audio_buffer)

        # Should return not detected
        self.assertFalse(result["detected"])

    def test_handle_jarvis_detection(self):
        """Test handling a detected Jarvis trigger."""
        # Create a detection result for Jarvis
        detection_result = {
            "detected": True,
            "trigger_type": "cloud_code",
            "transcription": "what's the weather today"
        }

        # Patch CloudCodeHandler at the point of use
        # This avoids issues with importing during setup
        with patch("src.utils.cloud_code.CloudCodeHandler") as cloud_code_mock:
            # Configure the mock
            cloud_code_mock.return_value = self.mock_cloud_code
            self.mock_cloud_code.submit_request.return_value = "request-123"
            self.mock_cloud_code._process_request.return_value = "Generated response"

            # Handle the detection
            self.detector.handle_detection(detection_result)

            # Verify the correct sound was played
            self.mock_recorder.play_sound.assert_called_with("command")

            # Verify notification was sent
            self.mock_send_notification.assert_called_once()

            # Verify Cloud Code was called
            self.mock_cloud_code.submit_request.assert_called_once()
            self.mock_cloud_code._process_request.assert_called_once()

            # Verify the response was spoken
            self.mock_speak.assert_called_once()

    def test_handle_dictation_detection(self):
        """Test handling a detected dictation trigger."""
        # Create a detection result for dictation
        detection_result = {
            "detected": True,
            "trigger_type": "dictation",
            "transcription": "some text to type"
        }

        # Handle the detection
        self.detector.handle_detection(detection_result)

        # Verify the correct sound was played
        self.mock_recorder.play_sound.assert_called_with("dictation")

        # Verify notification was sent
        self.mock_send_notification.assert_called_once()

        # Verify recording was started
        self.mock_recorder.start_recording.assert_called_once()


@pytest.mark.asyncio
class TestTriggerDetectionAsync:
    """Test async functionality of TriggerDetector with pytest-asyncio."""

    # Use the pytest_asyncio.fixture decorator explicitly
    from pytest_asyncio import fixture

    @fixture
    async def setup_detector(self):
        """Set up the test environment and return a detector."""
        # Create mock client with an async check_connection method
        client_mock = MagicMock()
        client_mock.check_connection = AsyncMock(return_value=True)

        # Patch the dependencies
        speech_client_patch = patch("src.api.speech_recognition_client.SpeechRecognitionClient", return_value=client_mock)
        speech_client_patch.start()

        state_patch = patch("src.audio.trigger_detection.state")
        state_mock = state_patch.start()
        state_mock.dictation_trigger = "type"

        recorder_patch = patch("src.audio.trigger_detection.AudioRecorder")
        recorder_mock = recorder_patch.start()
        recorder_instance = MagicMock()
        recorder_mock.return_value = recorder_instance

        # Create the detector after patching
        detector = TriggerDetector()

        # Yield the detector and needed mocks
        yield detector, client_mock, recorder_instance

        # Clean up patches
        speech_client_patch.stop()
        state_patch.stop()
        recorder_patch.stop()

    async def test_check_api_connection(self, setup_detector):
        """Test API connection check."""
        detector, client_mock, _ = setup_detector

        # Replace the loop.run_until_complete with a direct async call handler
        def mock_run(coro):
            if hasattr(coro, '__await__'):
                # Call the actual mock to track the call
                if hasattr(coro, '__self__') and hasattr(coro, '__name__'):
                    if coro.__name__ == 'check_connection':
                        # Actually call the AsyncMock to register the call
                        asyncio.create_task(client_mock.check_connection())
                        # Return the value directly
                        return client_mock.check_connection.return_value
            return coro

        # Replace the loop to avoid nested event loop issues
        with patch.object(detector.loop, 'run_until_complete', side_effect=mock_run):
            # Call the method - this will use our mock
            detector.check_api_connection()

            # Verify API call attempt was made
            client_mock.check_connection.assert_called_once()

            # Test error case
            client_mock.check_connection.return_value = False

            # Should raise an exception
            with pytest.raises(RuntimeError):
                detector.check_api_connection()
