#!/usr/bin/env python3
"""
Test discovery utility to find all tests in the new directory structure.
This script helps with the migration from flat structure to hierarchical structure.
"""

import os
import sys
import unittest
import importlib
import importlib.util
from pathlib import Path

# Ensure src is in the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def discover_tests(start_dir=None):
    """Discover all test modules in the test directory structure.

    Args:
        start_dir: Starting directory for discovery

    Returns:
        unittest.TestSuite: Suite containing all tests
    """
    if start_dir is None:
        start_dir = os.path.dirname(os.path.abspath(__file__))

    suite = unittest.TestSuite()

    # First, check standard test directory
    if os.path.exists(start_dir):
        loader = unittest.defaultTestLoader
        standard_suite = loader.discover(start_dir, pattern="test_*.py", top_level_dir=start_dir)
        suite.addTest(standard_suite)

    # Now check subdirectories
    for subdir in ['api', 'audio', 'config', 'core', 'ui', 'utils', 'integration']:
        subdir_path = os.path.join(start_dir, subdir)
        if os.path.exists(subdir_path) and os.path.isdir(subdir_path):
            subdir_suite = loader.discover(subdir_path, pattern="test_*.py", top_level_dir=start_dir)
            suite.addTest(subdir_suite)

    return suite


if __name__ == "__main__":
    # Set up test environment
    os.environ["TESTING"] = "true"

    # Get test suite
    test_suite = discover_tests()

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Return non-zero exit code if tests failed
    sys.exit(not result.wasSuccessful())
