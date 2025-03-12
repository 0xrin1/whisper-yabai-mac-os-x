#!/usr/bin/env python3
"""
Special test runner for CI environment.
Only runs a curated set of tests that are known to work in CI.
"""

import os
import sys
import unittest
import pytest

# Set environment variables for testing
os.environ["TESTING"] = "true"
os.environ["MOCK_TEST_MODE"] = "true"
os.environ["SKIP_AUDIO_RECORDING"] = "true"
os.environ["SKIP_AUDIO_PLAYBACK"] = "true"
os.environ["USE_MOCK_SPEECH"] = "true"

# List of tests that work reliably in CI
SAFE_TEST_FILES = [
    "src/tests/test_config.py",
    "src/tests/test_state_manager.py",
    "src/tests/test_mock_example.py"
]

if __name__ == "__main__":
    print("Running CI-safe tests only...")
    sys.exit(pytest.main(SAFE_TEST_FILES + ["-v"]))
