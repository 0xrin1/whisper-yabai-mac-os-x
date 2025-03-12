"""
Common pytest configuration and fixtures.
This file is automatically loaded by pytest.
"""

import os
import sys
import time
import pytest
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import common test modules
from src.tests.common.mocks import (
    is_ci_environment,
    setup_mock_environment,
    get_mock_audio_data,
    mock_speech_recognition_client,
    MockSpeechRecognitionClient
)

# Configure test environment
def pytest_configure(config):
    """Configure pytest environment."""
    # Set environment variables for testing
    os.environ["TESTING"] = "true"

    # Use mock environment if we're in CI or mock mode is enabled
    if (os.environ.get("CI") == "true" or
        os.environ.get("MOCK_TEST_MODE", "false").lower() == "true"):
        setup_mock_environment()

# Skip tests marked as ci_skip when running in CI
def pytest_collection_modifyitems(config, items):
    """Skip tests marked with ci_skip in CI environment."""
    if is_ci_environment():
        skip_marker = pytest.mark.skip(reason="Test skipped in CI environment")
        for item in items:
            if "ci_skip" in item.keywords:
                item.add_marker(skip_marker)

# Common fixtures
@pytest.fixture
def mock_audio_data():
    """Return mock audio data for testing."""
    return get_mock_audio_data()

@pytest.fixture
def mock_transcription():
    """Return a mock transcription result."""
    return {"text": "this is a mock transcription", "confidence": 0.95}

@pytest.fixture
def temp_log_file(tmp_path):
    """Create a temporary log file for testing."""
    log_file = tmp_path / "test_log.txt"
    yield str(log_file)
    if log_file.exists():
        log_file.unlink()

@pytest.fixture
def mock_config():
    """Provide a mock config for tests."""
    mock_config = {
        "MODEL_SIZE": "tiny",
        "COMMAND_TRIGGER": "hey",
        "DICTATION_TRIGGER": "type",
        "ASSISTANT_TRIGGER": "hey jarvis",
        "RECORDING_TIMEOUT": 3.0,
        "DICTATION_TIMEOUT": 5.0,
        "LOG_LEVEL": "DEBUG",
        "PLAY_COMPLETION_SOUND": False,
        "SHOW_DICTATION_NOTIFICATIONS": False,
    }
    with patch("src.config.config.config") as config_mock:
        config_mock.get.side_effect = lambda key, default=None: mock_config.get(key, default)
        config_mock.__getitem__.side_effect = lambda key: mock_config.get(key)
        yield config_mock

@pytest.fixture
def mock_speech_client():
    """Provide a mock speech recognition client."""
    return MockSpeechRecognitionClient()

@pytest.fixture
def patch_speech_client():
    """Patch the speech recognition client."""
    with mock_speech_recognition_client() as mock:
        yield mock
