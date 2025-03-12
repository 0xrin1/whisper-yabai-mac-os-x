#!/bin/bash
# This script runs each test file individually to identify CI issues

# Set up mock environment variables
export MOCK_TEST_MODE=true
export SKIP_AUDIO_RECORDING=true
export SKIP_AUDIO_PLAYBACK=true
export USE_MOCK_SPEECH=true

# Directory containing test files
TEST_DIR="src/tests"

# Run each test file individually
for test_file in ${TEST_DIR}/test_*.py; do
  echo "===================================================="
  echo "Testing $test_file"
  echo "===================================================="
  python -m pytest "$test_file" -v || echo "FAILED: $test_file"
  echo ""
done

echo "Individual test runs completed"
