#!/usr/bin/env python3
"""
Example test file that demonstrates using the mock environment
"""

import os
import sys
import unittest
from unittest.mock import patch

# Add parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our test utilities
from src.tests.test_utils import (
    setup_mock_environment,
    mock_speech_synthesis,
    mock_whisper_transcription,
    mock_audio_recorder,
    get_mock_audio_data,
)


class MockExampleTest(unittest.TestCase):
    """Example test case using mock environment"""

    def setUp(self):
        """Set up the test environment"""
        # Set up the mock environment
        self.using_mocks = setup_mock_environment()

        # Create mocks
        self.mock_speech = mock_speech_synthesis()
        self.mock_transcribe = mock_whisper_transcription()
        self.mock_recorder = mock_audio_recorder()

        print(f"Running tests with mocks: {self.using_mocks}")

    def test_mock_speech(self):
        """Test mock speech synthesis"""
        # Call the mock speech function
        result = self.mock_speech("Hello, world!")

        # Check the result
        self.assertTrue(result)

    def test_mock_transcription(self):
        """Test mock transcription"""
        # Get mock audio data
        audio_data = get_mock_audio_data()

        # Call the mock transcribe function
        result = self.mock_transcribe(audio_data)

        # Check the result
        self.assertIn("text", result)
        self.assertIsInstance(result["text"], str)

    def test_mock_recorder(self):
        """Test mock audio recorder"""
        # Call the mock recorder
        audio_data = self.mock_recorder.record()

        # Check the result
        self.assertIsNotNone(audio_data)
        self.assertGreater(len(audio_data), 0)


if __name__ == "__main__":
    unittest.main()
