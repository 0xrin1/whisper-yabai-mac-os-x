#!/usr/bin/env python3
"""
Test script for toast notifications in the voice control system.
"""

import time
import logging
import unittest
from src.ui.toast_notifications import (
    notify_listening,
    notify_processing,
    notify_command_executed,
    notify_error,
    send_notification,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("toast-test")


def main():
    """Run a sequence of test notifications."""
    logger.info("Starting toast notification test")

    # Show startup notification
    send_notification(
        "Voice Control Ready",
        "Press ctrl+shift+space to activate voice commands",
        "whisper-voice-ready",
        5,
        True,
    )

    # Wait a bit
    logger.info("Waiting 3 seconds...")
    time.sleep(3)

    # Show listening notification
    logger.info("Showing 'listening' notification")
    notify_listening(5)

    # Wait a bit
    time.sleep(3)

    # Show processing notification
    logger.info("Showing 'processing' notification")
    notify_processing()

    # Wait a bit
    time.sleep(3)

    # Show command execution notification
    logger.info("Showing 'command executed' notification")
    notify_command_executed("open Safari")

    # Wait a bit
    time.sleep(3)

    # Show error notification
    logger.info("Showing 'error' notification")
    notify_error("Failed to recognize command")

    logger.info("All notifications shown, test complete!")
    return 0


if __name__ == "__main__":
    main()
