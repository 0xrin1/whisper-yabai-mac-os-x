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

echo "Running tests with pytest..."
python -m pytest

# Run unit tests individually like CI does
echo "Running individual test files..."
cd src
for test_file in tests/test_*.py; do
  if [ -f "$test_file" ]; then
    echo "Running $test_file..."
    python "$test_file" || echo "Test $test_file failed but continuing..."
  fi
done
