"""
Mock objects and functions for testing.
Provides common mocks used across all test modules.
"""

import os
import logging
from unittest.mock import MagicMock, AsyncMock, patch

logger = logging.getLogger(__name__)


def is_ci_environment():
    """Check if we're running in a CI environment"""
    return os.environ.get("MOCK_TEST_MODE", "false").lower() == "true"


def should_skip_audio_recording():
    """Check if audio recording should be skipped"""
    return os.environ.get("SKIP_AUDIO_RECORDING", "false").lower() == "true"


def should_skip_audio_playback():
    """Check if audio playback should be skipped"""
    return os.environ.get("SKIP_AUDIO_PLAYBACK", "false").lower() == "true"


def should_use_mock_speech():
    """Check if mock speech should be used"""
    return os.environ.get("USE_MOCK_SPEECH", "false").lower() == "true"


def setup_mock_environment():
    """Setup mock environment for testing"""
    logger.info("Setting up mock test environment")

    # Set environment variables for mocks
    if is_ci_environment():
        os.environ["MOCK_TEST_MODE"] = "true"
        os.environ["SKIP_AUDIO_RECORDING"] = "true"
        os.environ["SKIP_AUDIO_PLAYBACK"] = "true"
        os.environ["USE_MOCK_SPEECH"] = "true"

    # Return True if we're in a mock environment
    return is_ci_environment()


def get_mock_audio_data():
    """Get mock audio data for testing"""
    # Just return some empty bytes that can be used as fake audio data
    return bytes([0] * 16000)


def mock_speech_synthesis():
    """Get a mock speech synthesis function that matches our server-based API"""

    def mock_speak(
        text,
        voice=None,  # Will use config value
        rate=1.0,
        use_high_quality=True,
        enhance_audio=True,
        block=False,
        **kwargs,
    ):
        from src.config.config import config

        # Default to config value if None
        if voice is None:
            voice = config.get("NEURAL_VOICE_ID", "p230")
        # Just log the text, don't actually make API calls
        logger.info(f"MOCK SPEECH (server API): {text}")
        logger.info(
            f"MOCK SPEECH PARAMS: voice={voice}, rate={rate}, "
            f"use_high_quality={use_high_quality}, enhance_audio={enhance_audio}"
        )
        return True

    return mock_speak


def mock_whisper_transcription():
    """Get a mock whisper transcription function"""

    def mock_transcribe(audio_data, **kwargs):
        logger.info(f"MOCK TRANSCRIPTION: Using {len(audio_data)} bytes of audio data")
        # Return a mock transcription result
        return {"text": "this is a mock transcription"}

    return mock_transcribe


def mock_audio_recorder():
    """Get a mock audio recorder object"""
    mock_recorder = MagicMock()
    mock_recorder.record.return_value = get_mock_audio_data()
    return mock_recorder


def patch_module(module_name, mock_obj):
    """Patch a module with a mock object for testing"""
    import sys

    if module_name in sys.modules:
        original_module = sys.modules[module_name]
        sys.modules[module_name] = mock_obj
        return original_module
    else:
        sys.modules[module_name] = mock_obj
        return None


def restore_module(module_name, original_module):
    """Restore the original module after testing"""
    import sys

    if original_module is not None:
        sys.modules[module_name] = original_module
    else:
        del sys.modules[module_name]


# Mock Speech Recognition API client
class MockSpeechRecognitionClient:
    """Mock SpeechRecognitionClient for testing."""

    def __init__(self, api_url=None):
        """Initialize with a mock that always succeeds."""
        self.api_url = api_url or "http://localhost:8080"
        self.connected = True
        self.ws_connected = False
        self.websocket = None
        self.transcription_callbacks = []

    async def check_connection(self):
        """Mock connection check that always succeeds by default."""
        return self.connected

    async def list_models(self):
        """Return dummy list of models."""
        return {
            "available_models": ["tiny", "base", "small", "medium", "large-v3"],
            "default_model": "large-v3",
            "loaded_models": ["large-v3"]
        }

    async def transcribe(self, audio_file, model_size="large-v3", language="en", prompt=None):
        """Mock transcription that returns pre-defined text."""
        return {
            "text": "this is a mock transcription",
            "confidence": 0.95,
            "processing_time": 0.1
        }

    async def transcribe_audio_data(self, audio_data, model_size="large-v3", language="en", prompt=None):
        """Mock transcription for raw audio data."""
        return {
            "text": "this is a mock transcription from audio data",
            "confidence": 0.95,
            "processing_time": 0.1
        }

    async def upload_and_transcribe(self, audio_file, model_size="large-v3", language="en", prompt=None):
        """Mock file upload and transcription."""
        return {
            "text": "this is a mock transcription from uploaded file",
            "confidence": 0.95,
            "processing_time": 0.1
        }

    async def connect_websocket(self, model_size=None, language=None, prompt=None):
        """Mock websocket connection."""
        self.ws_connected = True
        logger.info("Mock WebSocket connected")

    async def disconnect_websocket(self):
        """Mock websocket disconnection."""
        self.ws_connected = False
        logger.info("Mock WebSocket disconnected")

    async def send_audio_for_transcription(self, audio_data):
        """Mock sending audio data via websocket."""
        # Call all registered callbacks with a mock result
        for callback in self.transcription_callbacks:
            try:
                callback({
                    "text": "this is a mock transcription from websocket",
                    "confidence": 0.95,
                    "processing_time": 0.1,
                    "is_final": True
                })
            except Exception as e:
                logger.error(f"Error in transcription callback: {e}")

    def register_transcription_callback(self, callback):
        """Register a callback for transcription events."""
        if callback not in self.transcription_callbacks:
            self.transcription_callbacks.append(callback)

    def unregister_transcription_callback(self, callback):
        """Unregister a callback for transcription events."""
        if callback in self.transcription_callbacks:
            self.transcription_callbacks.remove(callback)


def mock_speech_recognition_client():
    """Return a patch for the SpeechRecognitionClient."""
    return patch("src.api.speech_recognition_client.SpeechRecognitionClient",
                 return_value=MockSpeechRecognitionClient())


def mock_asyncio_new_event_loop():
    """Return a patch for asyncio.new_event_loop().

    This returns a mock event loop with run_until_complete method to handle coroutines.
    """
    loop = MagicMock()

    # Define a special run_until_complete method that can handle coroutines
    def mock_run_until_complete(coro):
        """Special run_until_complete that extracts values from coroutines.

        For regular coroutines from our mock classes, run it and get the result.
        For anything else, just return True as a default success value.
        """
        # If it's not awaitable, just return it
        if not hasattr(coro, '__await__'):
            return coro

        # For mock coroutines, try to resolve them
        try:
            # For our mock async methods (they're not real coroutines)
            if hasattr(coro, '__self__') and isinstance(coro.__self__, MockSpeechRecognitionClient):
                # This is a method call on our mock client - extract the method name
                method_name = coro.__name__
                # Check if it's one of our async methods
                if method_name in ['check_connection', 'list_models', 'transcribe',
                                  'transcribe_audio_data', 'upload_and_transcribe',
                                  'connect_websocket', 'disconnect_websocket',
                                  'send_audio_for_transcription']:
                    # Return the hard-coded result for this method
                    result = coro.__self__.__getattribute__(method_name)(*coro.__args__, **coro.__kwdefaults__ or {})
                    return result
        except (AttributeError, TypeError):
            pass

        # We need to return a sensible default for all coroutines used in testing
        return True

    loop.run_until_complete = mock_run_until_complete

    # Create a patch that returns our pre-configured mock loop
    return patch("asyncio.new_event_loop", return_value=loop)


# Async test utilities
class AsyncMockCustom(MagicMock):
    """A MagicMock that works with async functions."""

    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def async_return(value):
    """Create a mock async function that returns the specified value."""
    async def mock_func(*args, **kwargs):
        return value
    return mock_func


def async_exception(exc):
    """Create a mock async function that raises the specified exception."""
    async def mock_func(*args, **kwargs):
        raise exc
    return mock_func
