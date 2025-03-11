#!/usr/bin/env python3
"""
Unit tests for the Speech Recognition API Client.
Tests the client's ability to communicate with the Speech Recognition API.
"""

import os
import sys
import json
import base64
import tempfile
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module
from src.api.speech_recognition_client import SpeechRecognitionClient


# Sample test data
SAMPLE_TRANSCRIPTION = {
    "text": "This is a test transcription",
    "confidence": 0.92,
    "processing_time": 0.5
}

SAMPLE_MODELS = {
    "available_models": ["tiny", "base", "small", "medium", "large-v3"],
    "default_model": "large-v3",
    "loaded_models": ["large-v3"]
}

# Mock responses for aiohttp
class MockResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status

    async def json(self):
        return self.data

    async def text(self):
        if isinstance(self.data, dict):
            return json.dumps(self.data)
        return str(self.data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockClientSession:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.requests = []

    async def get(self, url, **kwargs):
        self.requests.append(("GET", url, kwargs))
        if url in self.responses:
            return self.responses[url]
        # Default response for root endpoint
        if url.endswith("/"):
            return MockResponse({"status": "ok"})
        # Default response for models endpoint
        if url.endswith("/models"):
            return MockResponse(SAMPLE_MODELS)
        return MockResponse({"error": "Not found"}, 404)

    async def post(self, url, **kwargs):
        self.requests.append(("POST", url, kwargs))
        if url in self.responses:
            return self.responses[url]
        # Default response for transcribe endpoint
        if url.endswith("/transcribe"):
            return MockResponse(SAMPLE_TRANSCRIPTION)
        # Default response for transcribe_file endpoint
        if url.endswith("/transcribe_file"):
            return MockResponse(SAMPLE_TRANSCRIPTION)
        return MockResponse({"error": "Not found"}, 404)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Mock for websockets
class MockWebSocket:
    def __init__(self, messages=None):
        self.messages = messages or []
        self.sent_messages = []
        self.closed = False

    async def send(self, message):
        self.sent_messages.append(message)

    async def recv(self):
        if not self.messages:
            # If no messages are queued, return a heartbeat response
            return "heartbeat"
        return self.messages.pop(0)

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
class TestSpeechRecognitionClient:
    """Test the Speech Recognition API Client."""

    @pytest.fixture
    def client(self):
        """Create a client for testing."""
        return SpeechRecognitionClient(api_url="http://test-api:8000")

    @pytest.fixture
    def mock_aiohttp_session(self, monkeypatch):
        """Mock aiohttp.ClientSession."""
        session = MockClientSession()

        @asyncio.coroutine
        def mock_session(*args, **kwargs):
            return session

        monkeypatch.setattr("aiohttp.ClientSession", mock_session)
        return session

    @pytest.fixture
    def mock_websocket(self, monkeypatch):
        """Mock websockets.connect."""
        ws = MockWebSocket()

        async def mock_connect(*args, **kwargs):
            return ws

        monkeypatch.setattr("websockets.connect", mock_connect)
        return ws

    async def test_check_connection_success(self, client, mock_aiohttp_session):
        """Test successful API connection check."""
        mock_aiohttp_session.responses["http://test-api:8000/"] = MockResponse({"status": "ok"})

        result = await client.check_connection()

        assert result is True
        assert ("GET", "http://test-api:8000/", {}) in mock_aiohttp_session.requests

    async def test_check_connection_failure(self, client, mock_aiohttp_session):
        """Test failed API connection check."""
        mock_aiohttp_session.responses["http://test-api:8000/"] = MockResponse({"error": "Service unavailable"}, 503)

        result = await client.check_connection()

        assert result is False
        assert ("GET", "http://test-api:8000/", {}) in mock_aiohttp_session.requests

    async def test_check_connection_exception(self, client, monkeypatch):
        """Test API connection check with exception."""
        async def mock_session(*args, **kwargs):
            raise Exception("Connection error")

        monkeypatch.setattr("aiohttp.ClientSession", mock_session)

        result = await client.check_connection()

        assert result is False

    async def test_list_models(self, client, mock_aiohttp_session):
        """Test listing available models."""
        mock_aiohttp_session.responses["http://test-api:8000/models"] = MockResponse(SAMPLE_MODELS)

        result = await client.list_models()

        assert result == SAMPLE_MODELS
        assert ("GET", "http://test-api:8000/models", {}) in mock_aiohttp_session.requests

    async def test_list_models_failure(self, client, mock_aiohttp_session):
        """Test listing models with API failure."""
        mock_aiohttp_session.responses["http://test-api:8000/models"] = MockResponse({"error": "Not found"}, 404)

        result = await client.list_models()

        assert result == {}
        assert ("GET", "http://test-api:8000/models", {}) in mock_aiohttp_session.requests

    async def test_transcribe(self, client, mock_aiohttp_session):
        """Test transcribing an audio file."""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"test audio data")
            audio_path = temp_file.name

        try:
            mock_aiohttp_session.responses["http://test-api:8000/transcribe"] = MockResponse(SAMPLE_TRANSCRIPTION)

            result = await client.transcribe(audio_path, model_size="large-v3", language="en")

            assert result == SAMPLE_TRANSCRIPTION
            assert len(mock_aiohttp_session.requests) == 1
            assert mock_aiohttp_session.requests[0][0] == "POST"
            assert mock_aiohttp_session.requests[0][1] == "http://test-api:8000/transcribe"

            # Verify request data contains required fields
            request_data = mock_aiohttp_session.requests[0][2].get("json", {})
            assert "audio_data" in request_data
            assert request_data.get("model_size") == "large-v3"
            assert request_data.get("language") == "en"
        finally:
            os.unlink(audio_path)

    async def test_transcribe_audio_data(self, client, mock_aiohttp_session):
        """Test transcribing raw audio data."""
        audio_data = b"test audio data"
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        mock_aiohttp_session.responses["http://test-api:8000/transcribe"] = MockResponse(SAMPLE_TRANSCRIPTION)

        result = await client.transcribe_audio_data(audio_data, model_size="large-v3", language="en")

        assert result == SAMPLE_TRANSCRIPTION
        assert len(mock_aiohttp_session.requests) == 1
        assert mock_aiohttp_session.requests[0][0] == "POST"
        assert mock_aiohttp_session.requests[0][1] == "http://test-api:8000/transcribe"

        # Verify request data contains required fields
        request_data = mock_aiohttp_session.requests[0][2].get("json", {})
        assert request_data.get("audio_data") == audio_base64
        assert request_data.get("model_size") == "large-v3"
        assert request_data.get("language") == "en"

    async def test_transcribe_error_handling(self, client, mock_aiohttp_session):
        """Test handling of transcription errors."""
        audio_data = b"test audio data"
        error_response = {"error": "Failed to process audio"}

        mock_aiohttp_session.responses["http://test-api:8000/transcribe"] = MockResponse(error_response, 500)

        result = await client.transcribe_audio_data(audio_data)

        assert "error" in result
        assert len(mock_aiohttp_session.requests) == 1

    async def test_upload_and_transcribe(self, client, mock_aiohttp_session):
        """Test uploading and transcribing a file."""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(b"test audio data")
            audio_path = temp_file.name

        try:
            mock_aiohttp_session.responses["http://test-api:8000/transcribe_file"] = MockResponse(SAMPLE_TRANSCRIPTION)

            result = await client.upload_and_transcribe(audio_path, model_size="large-v3", language="en")

            assert result == SAMPLE_TRANSCRIPTION
            assert len(mock_aiohttp_session.requests) == 1
            assert mock_aiohttp_session.requests[0][0] == "POST"
            assert mock_aiohttp_session.requests[0][1] == "http://test-api:8000/transcribe_file"

            # Verify request contains FormData with file and parameters
            assert "data" in mock_aiohttp_session.requests[0][2]
        finally:
            os.unlink(audio_path)

    async def test_websocket_connection(self, client, mock_websocket):
        """Test connecting to WebSocket for streaming transcription."""
        # Register a callback
        callback = MagicMock()
        client.register_transcription_callback(callback)

        # Connect to WebSocket
        await client.connect_websocket(model_size="large-v3", language="en")

        # Verify connection status
        assert client.ws_connected is True
        assert client.websocket is mock_websocket

        # Verify configuration message was sent
        assert len(mock_websocket.sent_messages) == 1
        config = json.loads(mock_websocket.sent_messages[0])
        assert config["model_size"] == "large-v3"
        assert config["language"] == "en"

        # Test sending audio data
        audio_data = b"test audio data"
        await client.send_audio_for_transcription(audio_data)

        # Verify audio data was sent
        assert len(mock_websocket.sent_messages) == 2
        message = json.loads(mock_websocket.sent_messages[1])
        assert "audio_data" in message

        # Test disconnecting
        await client.disconnect_websocket()
        assert client.ws_connected is False
        assert mock_websocket.closed is True

    async def test_websocket_callbacks(self, client, mock_websocket, monkeypatch):
        """Test WebSocket callbacks for transcription results."""
        # Use a controlled mock that we can manipulate for testing
        controlled_ws = MockWebSocket([
            json.dumps(SAMPLE_TRANSCRIPTION),
            json.dumps({"text": "Another transcription", "confidence": 0.85})
        ])

        async def mock_connect(*args, **kwargs):
            return controlled_ws

        monkeypatch.setattr("websockets.connect", mock_connect)

        # Register callbacks
        callback1 = MagicMock()
        callback2 = MagicMock()
        client.register_transcription_callback(callback1)
        client.register_transcription_callback(callback2)

        # Connect to WebSocket
        await client.connect_websocket()

        # Wait for messages to be processed (the _websocket_listen task)
        await asyncio.sleep(0.1)

        # Verify both callbacks were called with the message data
        callback1.assert_called_with(SAMPLE_TRANSCRIPTION)
        callback2.assert_called_with(SAMPLE_TRANSCRIPTION)

        # Wait for second message
        await asyncio.sleep(0.1)

        # Verify callbacks were called again with the second message
        assert callback1.call_count == 2
        assert callback2.call_count == 2

        # Test unregistering a callback
        client.unregister_transcription_callback(callback1)

        # Simulate another message by manually calling the processing function
        await client._websocket_listen()

        # Only callback2 should have been called for the third message
        assert callback1.call_count == 2  # Still just 2 calls
        assert callback2.call_count == 3  # Now 3 calls

        # Disconnect
        await client.disconnect_websocket()

    async def test_heartbeat_mechanism(self, client, mock_websocket, monkeypatch):
        """Test heartbeat mechanism to keep WebSocket connection alive."""
        # Create a mock sleep function that doesn't actually sleep
        original_sleep = asyncio.sleep

        async def fast_sleep(seconds):
            # Use a much shorter sleep time for testing
            await original_sleep(0.01)

        monkeypatch.setattr("asyncio.sleep", fast_sleep)

        # Connect to WebSocket
        await client.connect_websocket()

        # Wait a bit for the heartbeat to be sent
        await asyncio.sleep(0.02)

        # Verify heartbeat was sent
        assert "heartbeat" in mock_websocket.sent_messages

        # Disconnect
        await client.disconnect_websocket()

    async def test_error_handling_in_websocket(self, client, monkeypatch):
        """Test handling of errors in WebSocket connection."""
        # Create a websocket that raises an exception
        async def mock_connect(*args, **kwargs):
            raise Exception("Connection error")

        monkeypatch.setattr("websockets.connect", mock_connect)

        # Try to connect
        await client.connect_websocket()

        # Verify connection status is False
        assert client.ws_connected is False

    async def test_registering_duplicate_callback(self, client):
        """Test registering the same callback multiple times."""
        callback = MagicMock()

        # Register the same callback twice
        client.register_transcription_callback(callback)
        client.register_transcription_callback(callback)

        # Should only appear once in the list
        assert len(client.transcription_callbacks) == 1
        assert client.transcription_callbacks[0] is callback

    async def test_unregistering_nonexistent_callback(self, client):
        """Test unregistering a callback that wasn't registered."""
        callback = MagicMock()

        # Unregister a callback that wasn't registered
        client.unregister_transcription_callback(callback)

        # Should not raise an exception
        assert len(client.transcription_callbacks) == 0
