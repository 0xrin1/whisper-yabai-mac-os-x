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
import logging
import argparse
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

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
    loader = unittest.defaultTestLoader

    # First, check standard test directory for remaining tests
    if os.path.exists(start_dir):
        logger.info(f"Discovering tests in {start_dir}")
        standard_suite = loader.discover(start_dir, pattern="test_*.py", top_level_dir=start_dir)
        suite.addTest(standard_suite)

    # Now check subdirectories
    for subdir in ['api', 'audio', 'config', 'core', 'ui', 'utils', 'integration']:
        subdir_path = os.path.join(start_dir, subdir)
        if os.path.exists(subdir_path) and os.path.isdir(subdir_path):
            logger.info(f"Discovering tests in {subdir_path}")
            subdir_suite = loader.discover(subdir_path, pattern="test_*.py", top_level_dir=start_dir)
            suite.addTest(subdir_suite)

    test_count = suite.countTestCases()
    logger.info(f"Found {test_count} tests in total")

    return suite


if __name__ == "__main__":
    # Set up test environment
    os.environ["TESTING"] = "true"

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run tests with the new directory structure")
    parser.add_argument("--subdir", help="Only run tests in this subdirectory")
    parser.add_argument("--mock", action="store_true", help="Enable mock mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Configure mock environment if needed
    if args.mock:
        os.environ["MOCK_TEST_MODE"] = "true"
        os.environ["SKIP_AUDIO_RECORDING"] = "true"
        os.environ["SKIP_AUDIO_PLAYBACK"] = "true"
        os.environ["USE_MOCK_SPEECH"] = "true"
        logger.info("Mock mode enabled")

    # Get test suite
    if args.subdir:
        start_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.subdir)
        logger.info(f"Only running tests in {start_dir}")
        test_suite = discover_tests(start_dir)
    else:
        test_suite = discover_tests()

    # Run tests with verbosity level
    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    logger.info(f"Running {test_suite.countTestCases()} tests...")
    result = runner.run(test_suite)

    # Print summary
    logger.info(f"Tests completed: {result.testsRun} run, {len(result.failures)} failures, {len(result.errors)} errors")

    # Return non-zero exit code if tests failed
    sys.exit(not result.wasSuccessful())
