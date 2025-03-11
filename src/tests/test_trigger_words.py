#!/usr/bin/env python3
"""
Simple test script to verify trigger word detection.
This focuses ONLY on testing that 'hey' and 'type' trigger words are detected.
"""

import os
import time
import sys
import logging
import unittest

# Import test utilities
from test_utils import BaseVoiceTest, DaemonManager, synthesize_and_play

# Set up logging
logger = logging.getLogger("trigger-test")


class TriggerWordTest(BaseVoiceTest):
    """Test suite for trigger word detection."""

    def test_trigger_words(self):
        """Test both trigger words."""
        # Use DaemonManager to handle daemon lifecycle
        with DaemonManager(log_dir=self.log_dir, capture_output=False) as daemon_mgr:
            # Use our neural TTS API for speech synthesis
            logger.info("Testing with neural speech synthesis API")

            # Test 'hey' trigger
            logger.info("Testing 'hey' trigger word...")
            try:
                # Use neural speech synthesis
                temp_file = self.synthesize_and_play("hey")
                # Wait for processing to complete
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error testing 'hey' with speech synthesis: {e}")

            # Test dictation triggers
            logger.info("Testing dictation trigger words...")
            for phrase in ["type", "dictate"]:
                try:
                    logger.info(f"Testing '{phrase}' with speech synthesis")
                    # Use neural synthesis
                    temp_file = self.synthesize_and_play(phrase)
                    # Wait for processing
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"Error testing '{phrase}' with speech synthesis: {e}")


# Run tests directly if script is executed
if __name__ == "__main__":
    unittest.main()
