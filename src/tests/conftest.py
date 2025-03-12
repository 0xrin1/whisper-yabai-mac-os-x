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

# Configure test environment
def pytest_configure(config):
    """Configure pytest environment."""
    # Set environment variables for testing
    os.environ["TESTING"] = "true"

    # Use mock environment if we're in CI or mock mode is enabled
    if (os.environ.get("CI") == "true" or
        os.environ.get("MOCK_TEST_MODE", "false").lower() == "true"):
        os.environ["MOCK_TEST_MODE"] = "true"
        os.environ["SKIP_AUDIO_RECORDING"] = "true"
        os.environ["SKIP_AUDIO_PLAYBACK"] = "true"
        os.environ["USE_MOCK_SPEECH"] = "true"
        os.environ["WHISPER_MODEL_SIZE"] = "tiny"
        os.environ["USE_LLM"] = "false"

# Skip tests marked as ci_skip when running in CI
def pytest_collection_modifyitems(config, items):
    """Skip tests marked with ci_skip in CI environment."""
    if os.environ.get("CI") == "true" or os.environ.get("MOCK_TEST_MODE", "false").lower() == "true":
        skip_marker = pytest.mark.skip(reason="Test skipped in CI environment")
        for item in items:
            if "ci_skip" in item.keywords:
                item.add_marker(skip_marker)

# Common fixtures
@pytest.fixture
def mock_audio_data():
    """Return mock audio data for testing."""
    return bytes([0] * 16000)

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
