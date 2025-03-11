import os
import sys
import logging
from unittest.mock import MagicMock

# Set up logging
logging.basicConfig(level=logging.INFO)
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
    """Get a mock speech synthesis function that matches our new server-based API"""

    def mock_speak(
        text,
        voice="p230",
        rate=1.0,
        use_high_quality=True,
        enhance_audio=True,
        block=False,
        **kwargs,
    ):
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
    if module_name in sys.modules:
        original_module = sys.modules[module_name]
        sys.modules[module_name] = mock_obj
        return original_module
    else:
        sys.modules[module_name] = mock_obj
        return None


def restore_module(module_name, original_module):
    """Restore the original module after testing"""
    if original_module is not None:
        sys.modules[module_name] = original_module
    else:
        del sys.modules[module_name]
