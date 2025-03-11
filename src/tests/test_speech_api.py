#!/usr/bin/env python3
"""
Tests for the Speech Recognition Client.
The API server tests are skipped if FastAPI is not installed.
"""

import asyncio
import base64
import json
import os
import unittest
import pytest
import tempfile
import time
from unittest.mock import MagicMock, patch

try:
    from fastapi.testclient import TestClient
    from src.api.speech_recognition_api import SpeechRecognitionAPI
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from src.api.speech_recognition_client import SpeechRecognitionClient
from src.tests.test_utils import MockSpeechRecognitionClient


class MockWhisperModel:
    """Mock Whisper model for testing."""

    def transcribe(self, audio_file, language=None, initial_prompt=None):
        """Mock transcription method."""
        return {
            "text": "This is a test transcription",
            "confidence": 0.95,
            "language": "en",
            "segments": [],
        }


# Skip all FastAPI tests if not available
if FASTAPI_AVAILABLE:
    @pytest.fixture
    def api_client():
        """Create a test client for the API."""
        api = SpeechRecognitionAPI()
        return TestClient(api.app)

    @pytest.fixture
    def mock_whisper_load():
        """Mock whisper.load_model function."""
        with patch("whisper.load_model") as mock_load:
            mock_load.return_value = MockWhisperModel()
            yield mock_load

    def test_api_root(api_client):
        """Test the root endpoint."""
        response = api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_list_models(api_client, mock_whisper_load):
        """Test the models endpoint."""
        response = api_client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert "available_models" in data
        assert "default_model" in data
        assert "loaded_models" in data
        assert len(data["available_models"]) > 0

    def test_transcribe_file(api_client, mock_whisper_load):
        """Test the transcribe_file endpoint."""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            temp_file.write(b"test audio data")
            temp_file.flush()

            # Reset file pointer to beginning
            temp_file.seek(0)

            # Send the file to the API
            response = api_client.post(
                "/transcribe_file",
                files={"file": ("test.wav", temp_file, "audio/wav")},
                data={"model_size": "large-v3"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "text" in data
            assert "confidence" in data
            assert "processing_time" in data
            assert data["text"] == "This is a test transcription"
            assert data["confidence"] == 0.95

    def test_transcribe(api_client, mock_whisper_load):
        """Test the transcribe endpoint."""
        # Create test audio data
        audio_data = b"test audio data"
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        # Send the data to the API
        response = api_client.post(
            "/transcribe",
            json={
                "audio_data": audio_base64,
                "model_size": "large-v3"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "confidence" in data
        assert "processing_time" in data
        assert data["text"] == "This is a test transcription"
        assert data["confidence"] == 0.95


# These tests don't depend on FastAPI
@pytest.mark.asyncio
async def test_client_transcribe():
    """Test the client's transcribe method."""
    # Mock the aiohttp.ClientSession.post method
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_response.json.return_value = asyncio.Future()
        mock_response.json.return_value.set_result({
            "text": "This is a test transcription",
            "confidence": 0.95,
            "language": "en",
            "segments": [],
            "processing_time": 0.5
        })
        mock_post.return_value = mock_response

        # Create a test client
        client = SpeechRecognitionClient(api_url="http://localhost:8080")

        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            temp_file.write(b"test audio data")
            temp_file.flush()

            # Test the transcribe method
            result = await client.transcribe(
                temp_file.name,
                model_size="large-v3"
            )

            assert "text" in result
            assert "confidence" in result
            assert "processing_time" in result
            assert result["text"] == "This is a test transcription"
            assert result["confidence"] == 0.95


@pytest.mark.asyncio
async def test_client_check_connection():
    """Test the client's check_connection method."""
    # Mock the aiohttp.ClientSession.get method
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Create a mock response for success
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_get.return_value = mock_response

        # Create a test client
        client = SpeechRecognitionClient(api_url="http://localhost:8080")

        # Test the check_connection method
        result = await client.check_connection()
        assert result is True

        # Now test with a failed connection
        mock_response.status = 500
        result = await client.check_connection()
        assert result is False


# Test the mock client implementation
class TestMockSpeechRecognitionClient(unittest.TestCase):
    """Test the MockSpeechRecognitionClient used in other tests."""

    def setUp(self):
        self.client = MockSpeechRecognitionClient()
        # Setup asyncio for testing
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_check_connection(self):
        """Test connection check returns True by default."""
        result = self.loop.run_until_complete(self.client.check_connection())
        self.assertTrue(result)

    def test_list_models(self):
        """Test list_models returns expected structure."""
        result = self.loop.run_until_complete(self.client.list_models())
        self.assertIn("available_models", result)
        self.assertIn("default_model", result)

    def test_transcribe(self):
        """Test transcribe returns expected structure."""
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            temp_file.write(b"test audio data")
            temp_file.flush()

            result = self.loop.run_until_complete(self.client.transcribe(temp_file.name))
            self.assertIn("text", result)
            self.assertIn("confidence", result)
            self.assertIn("processing_time", result)

    def test_transcribe_audio_data(self):
        """Test transcribe_audio_data returns expected structure."""
        audio_data = b"test audio data"
        result = self.loop.run_until_complete(self.client.transcribe_audio_data(audio_data))
        self.assertIn("text", result)
        self.assertIn("confidence", result)
        self.assertIn("processing_time", result)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
