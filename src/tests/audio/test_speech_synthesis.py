#!/usr/bin/env python3
"""
Unit tests for speech synthesis module
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import sys
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from audio import speech_synthesis


class TestSpeechSynthesis(unittest.TestCase):
    """Tests for speech synthesis module"""

    def setUp(self):
        """Set up test environment"""
        # Ensure we have a clean state
        speech_synthesis.stop_speaking()

        # Create a temp file to simulate audio output
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.temp_file.close()

    def tearDown(self):
        """Clean up after tests"""
        # Clean up temp file
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    @patch("requests.post")
    def test_call_speech_api(self, mock_post):
        """Test the _call_speech_api function"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"dummy audio data"
        mock_post.return_value = mock_response

        # Call function
        result = speech_synthesis._call_speech_api("Test text")

        # Check if API was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check that the URL is correct (it's the first positional arg)
        self.assertEqual(call_args[0][0], speech_synthesis.TTS_ENDPOINT)

        # Check request payload
        payload = call_args[1]["json"]
        self.assertEqual(payload["text"], "Test text")
        self.assertEqual(payload["voice_id"], "p230")  # Default voice
        self.assertEqual(payload["speed"], 1.0)  # Default speed
        self.assertTrue(payload["use_high_quality"])  # Default quality
        self.assertTrue(payload["enhance_audio"])  # Default enhancement

        # Check that result is a file path
        self.assertTrue(os.path.exists(result))

        # Clean up temp file created by function
        os.remove(result)

    @patch("requests.post")
    def test_call_speech_api_with_params(self, mock_post):
        """Test the _call_speech_api function with custom parameters"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"dummy audio data"
        mock_post.return_value = mock_response

        # Call function with custom parameters
        result = speech_synthesis._call_speech_api(
            "Test text",
            voice_id="p230",  # Standardize on p230 voice
            speed=1.5,
            use_high_quality=False,
            enhance_audio=False,
        )

        # Check if API was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check request payload
        payload = call_args[1]["json"]
        self.assertEqual(payload["text"], "Test text")
        self.assertEqual(payload["voice_id"], "p230")  # Standardize on p230 voice
        self.assertEqual(payload["speed"], 1.5)
        self.assertFalse(payload["use_high_quality"])
        self.assertFalse(payload["enhance_audio"])

        # Clean up temp file created by function
        os.remove(result)

    def test_speak(self):
        """Test the speak function"""
        # Mock the queue thread
        with patch("threading.Thread") as mock_thread:
            # Set up mock thread
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            # Call function
            result = speech_synthesis.speak("Test text")

            # Check that it worked
            self.assertTrue(result)

            # Verify that a thread was started
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()

    def test_speak_with_params(self):
        """Test the speak function with custom parameters"""
        # Use a spy on _speech_queue
        with patch.object(speech_synthesis, "_speech_queue", []) as mock_queue:
            with patch("threading.Thread") as mock_thread:
                # Set up mock thread
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                # Call function with custom parameters
                result = speech_synthesis.speak(
                    "Test text",
                    voice="p230",  # Standardize on p230 voice
                    rate=1.5,
                    use_high_quality=False,
                    enhance_audio=False,
                )

                # Check that it worked
                self.assertTrue(result)

                # Check that the right request was added to queue
                self.assertEqual(len(mock_queue), 1)
                request = mock_queue[0]
                self.assertEqual(request["text"], "Test text")
                self.assertEqual(request["voice_id"], "p230")  # Standardize on p230 voice
                self.assertEqual(request["speed"], 1.5)
                self.assertFalse(request["use_high_quality"])
                self.assertFalse(request["enhance_audio"])

    def test_speak_random(self):
        """Test the speak_random function"""
        with patch.object(speech_synthesis, "speak") as mock_speak:
            mock_speak.return_value = True

            # Test with valid category
            result = speech_synthesis.speak_random("greeting")
            self.assertTrue(result)
            self.assertTrue(mock_speak.called)

            # Test with invalid category
            result = speech_synthesis.speak_random("nonexistent_category")
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
