# Test Organization

This directory contains all the tests for the Whisper Voice Control system. The tests are organized into subdirectories that mirror the main project structure for better organization and maintainability.

## Directory Structure

- `api/`: Tests for API-related functionality
- `audio/`: Tests for audio processing, recording, and speech synthesis
- `common/`: Common utilities, mocks, and base classes for all tests
- `config/`: Tests for configuration management
- `core/`: Tests for core functionality like state management and error handling
- `ui/`: Tests for UI components like toast notifications
- `utils/`: Tests for utility modules
- `integration/`: End-to-end and integration tests that test multiple components together

## Running Tests

To run all tests:
```bash
pytest
```

To run tests for a specific module:
```bash
pytest src/tests/audio/
```

To run a specific test file:
```bash
pytest src/tests/audio/test_audio_processor.py
```

## Test Organization Principles

1. **DRY (Don't Repeat Yourself)**: Common utilities and fixtures are in `common/` directory.
2. **Module Grouping**: Tests are grouped by the module they're testing.
3. **Base Classes**: Base test classes are defined in `common/base.py` to share setup/teardown code.
4. **Mocking**: Common mocks are defined in `common/mocks.py` for consistent test behavior.
5. **Speech Utilities**: Common speech synthesis and playback functions are in `common/speech.py`.

## Test Environment

The test environment can be configured using environment variables:

- `MOCK_TEST_MODE=true`: Enable mock mode for all tests
- `SKIP_AUDIO_RECORDING=true`: Skip actual audio recording
- `SKIP_AUDIO_PLAYBACK=true`: Skip actual audio playback
- `USE_MOCK_SPEECH=true`: Use mock speech synthesis instead of actual TTS

These environment variables are automatically set in CI environments to ensure tests run without requiring actual audio hardware.

## CI Testing

For CI environments, tests are automatically configured to:

1. Skip tests marked with the `ci_skip` mark
2. Use mock implementations instead of real hardware
3. Run a reduced set of tests that are known to be reliable in CI

The `pytest.ci.ini` configuration file is used for CI test runs.

## Design Principles

- **Comprehensive Coverage**: Test all critical functionality
- **Isolation**: Tests should be independent of each other
- **Mock Dependencies**: Use mocks for external dependencies
- **Verification**: Verify behavior, not implementation details
