# Testing Framework

This document describes the testing framework for the Voice Control System, with a specific focus on testing components that interact with the Speech Recognition API.

## Overview

The Voice Control System has a robust testing framework that ensures functionality works correctly, particularly for:

1. The API-based components (Speech Recognition API and Client)
2. The trigger detection system (for "jarvis" and dictation modes)
3. The audio processing pipeline

The tests are designed to work without requiring actual API connectivity, allowing for CI/CD and offline development.

## Key Components

### Speech Recognition API Testing

The `test_speech_recognition_client.py` file contains comprehensive tests for the Speech Recognition API client, including:

- Testing API connection checks
- Testing model listing
- Testing transcription (both file-based and raw audio data)
- Testing WebSocket functionality
- Testing error handling

### Audio Processor Testing

The `test_audio_processor.py` file tests the audio processor component that handles:

- Dictation mode (typing what users say)
- Cloud Code integration via the "jarvis" trigger
- API connectivity checking
- Error handling

### Trigger Detection Testing

The `test_trigger_detection.py` file tests the trigger detection system that:

- Detects the "jarvis" trigger to activate Cloud Code
- Handles dictation as the default mode when no trigger is detected
- Processes audio buffers using the Speech Recognition API

## Testing Utilities

The `test_utils.py` file provides several utilities to facilitate testing:

### Mock Classes

- `MockSpeechRecognitionClient`: A comprehensive mock for the Speech Recognition API client
- `AsyncMock`: A MagicMock subclass for mocking async functions
- `DaemonManager`: Manages daemon processes for integration tests

### Helper Functions

- `mock_speech_recognition_client()`: Creates a patch for the Speech Recognition API client
- `mock_asyncio_new_event_loop()`: Creates a mock event loop that handles coroutines
- `async_return()` and `async_exception()`: Create mock async functions with specific behaviors
- Environment check functions like `is_ci_environment()` and `should_skip_audio_recording()`

### Testing Async Code

The testing framework supports two approaches for testing asynchronous code:

1. **Using pytest-asyncio** (recommended):
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    # Test async code directly with await
    result = await my_async_function()
    assert result == expected_value
```

2. **Using AsyncTestCase**:
```python
from src.tests.test_utils import AsyncTestCase

class MyAsyncTest(unittest.TestCase, AsyncTestCase):
    def test_async_function(self):
        result = self.run_async(my_async_function())
        self.assertEqual(result, expected_value)
```

## Mocking Strategy

### Mocking the API Client

The testing framework uses a layered approach to mocking:

1. **Mock the SpeechRecognitionClient class** to return a controlled instance
2. **Mock specific async methods** like `check_connection()` and `transcribe_audio_data()`
3. **Mock the asyncio event loop** to properly handle coroutines

Example:
```python
# Create mock for the client
with mock_speech_recognition_client() as client_patch:
    mock_client = client_patch.return_value

    # Configure the mock client's behavior
    mock_client.transcribe_audio_data.return_value = {
        "text": "test transcription",
        "confidence": 0.95
    }

    # Create mock for the event loop
    with mock_asyncio_new_event_loop():
        # Run your test
        result = your_function_that_uses_the_client()
        assert result == expected_value
```

### Mocking Cloud Code

When testing components that integrate with Cloud Code:

1. Use a patch for the module that contains the CloudCodeHandler
2. Apply the patch at the point of use rather than in setUp to avoid import issues
3. Mock the submit_request and _process_request methods to control behavior

## Running Tests

Run all tests:
```bash
python -m pytest
```

Run specific test file:
```bash
python -m pytest src/tests/test_audio_processor.py
```

Run specific test:
```bash
python -m pytest src/tests/test_audio_processor.py::TestAudioProcessor::test_process_dictation
```

Run with verbose output:
```bash
python -m pytest -v
```

## API-Only Test Adaptations

The testing framework has been adapted to work with the API-only approach:

1. All tests now mock the Speech Recognition API client instead of local transcription
2. Tests no longer verify command processing (since we removed traditional commands)
3. Tests now verify:
   - Dictation functionality (default mode)
   - Cloud Code integration via "jarvis" trigger
   - API connectivity and error handling
   - Trigger detection for "jarvis" and defaulting to dictation

These adaptations ensure the tests remain relevant and accurate with the new system architecture.
