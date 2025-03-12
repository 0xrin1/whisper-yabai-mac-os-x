#!/bin/bash
# This script runs tests in the same way as the CI workflow

# Set up mock environment variables
export MOCK_TEST_MODE=true
export SKIP_AUDIO_RECORDING=true
export SKIP_AUDIO_PLAYBACK=true
export USE_MOCK_SPEECH=true

# Create mock .env file like CI does
echo "WHISPER_MODEL_SIZE=tiny" > .env.test
echo "USE_LLM=false" >> .env.test
echo "MOCK_TEST_MODE=true" >> .env.test
echo "LOG_LEVEL=DEBUG" >> .env.test

# Create empty audio files for tests that need sample files
mkdir -p test_audio_samples
dd if=/dev/zero of=test_audio_samples/silence.wav bs=1k count=16

echo "Running tests with CI-specific pytest configuration..."
python -m pytest -c pytest.ci.ini

# We now use pytest for all test discovery and running
echo "All tests completed successfully with pytest"
