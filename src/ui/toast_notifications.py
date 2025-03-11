#!/usr/bin/env python3
"""
Toast notification module for macOS.
Provides visual and audible feedback for voice control actions.
Uses osascript to display notifications for maximum compatibility.
"""

import os
import time
import subprocess
import threading
from typing import Optional

# Keep track of active notifications
active_notifications = {}
notification_lock = threading.Lock()


def send_notification(
    title: str,
    message: str,
    identifier: Optional[str] = None,
    timeout: int = 5,
    sound: bool = True,
) -> str:
    """
    Send a macOS notification.

    Args:
        title: The notification title
        message: The notification message
        identifier: Optional unique identifier for the notification (for updating/removing)
        timeout: Auto-dismiss after this many seconds (0 = don't auto-dismiss)
        sound: Whether to play a sound with the notification

    Returns:
        The notification identifier
    """
    try:
        # Generate a unique identifier if not provided
        if identifier is None:
            identifier = f"whisper-voice-control-{int(time.time())}"

        # Skip UserNotifications and go straight to osascript
        # Escape double quotes in title and message
        title_escaped = title.replace('"', '\\"')
        message_escaped = message.replace('"', '\\"')

        script = f"""
        display notification "{message_escaped}" with title "{title_escaped}"
        """

        subprocess.run(["osascript", "-e", script], capture_output=True, text=True)

        # Store in active notifications
        with notification_lock:
            active_notifications[identifier] = {
                "title": title,
                "message": message,
                "timestamp": time.time(),
            }

        # Auto-dismiss if timeout > 0
        if timeout > 0:
            threading.Timer(timeout, remove_notification, [identifier]).start()

        return identifier

    except Exception as e:
        print(f"Failed to send notification: {e}")
        return ""


def update_notification(
    identifier: str, title: str, message: str, timeout: int = 5, sound: bool = False
) -> str:
    """
    Update an existing notification or create a new one if it doesn't exist.

    Args:
        identifier: The notification identifier to update
        title: The new notification title
        message: The new notification message
        timeout: Reset auto-dismiss timer to this many seconds (0 = don't auto-dismiss)
        sound: Whether to play a sound with the notification

    Returns:
        The notification identifier
    """
    # Remove existing notification if it exists
    remove_notification(identifier)

    # Send new notification with same identifier
    return send_notification(title, message, identifier, timeout, sound)


def remove_notification(identifier: str) -> None:
    """
    Remove a notification by its identifier.

    Args:
        identifier: The notification identifier to remove
    """
    try:
        # With osascript, we can't directly remove notifications,
        # but we can track them internally
        with notification_lock:
            if identifier in active_notifications:
                del active_notifications[identifier]

    except Exception as e:
        print(f"Failed to remove notification: {e}")


def remove_all_notifications() -> None:
    """Remove all active notifications."""
    try:
        # With osascript, we can only track notifications internally
        with notification_lock:
            active_notifications.clear()

    except Exception as e:
        print(f"Failed to remove all notifications: {e}")


# Special notification types for voice control
def notify_listening(timeout: int = 10) -> str:
    """Show a notification that we're listening for commands."""
    return send_notification(
        "Voice Control Active",
        "Listening for your command...",
        "whisper-voice-listening",
        timeout,
        False,  # No sound when starting to listen
    )


def notify_processing(timeout: int = 30) -> str:
    """Show a notification that we're processing audio."""
    return update_notification(
        "whisper-voice-listening",
        "Processing Voice",
        "Transcribing and interpreting your command...",
        timeout,
        False,
    )


def notify_command_executed(command: str, timeout: int = 5) -> str:
    """Show a notification that a command was executed."""
    return update_notification(
        "whisper-voice-listening",
        "Command Executed",
        f"Executed: {command}",
        timeout,
        True,  # Sound when command executed
    )


def notify_error(error_msg: str, timeout: int = 10) -> str:
    """Show an error notification."""
    return send_notification(
        "Voice Control Error",
        error_msg,
        "whisper-voice-error",
        timeout,
        True,  # Sound for errors
    )


# Test function
def test_notifications():
    """Test the notification system."""
    print("Testing notifications...")

    # Send initial notification
    notify_id = send_notification(
        "Test Notification", "This is a test notification", timeout=10
    )
    print(f"Sent notification with ID: {notify_id}")

    # Wait 2 seconds
    time.sleep(2)

    # Update notification
    update_notification(
        notify_id,
        "Updated Notification",
        "This notification has been updated",
        timeout=10,
    )
    print(f"Updated notification with ID: {notify_id}")

    # Wait 2 seconds
    time.sleep(2)

    # Remove notification
    remove_notification(notify_id)
    print(f"Removed notification with ID: {notify_id}")

    # Test specific voice control notifications
    notify_listening()
    print("Sent 'listening' notification")

    time.sleep(2)

    notify_processing()
    print("Sent 'processing' notification")

    time.sleep(2)

    notify_command_executed("open Safari")
    print("Sent 'command executed' notification")

    time.sleep(2)

    notify_error("Failed to recognize command")
    print("Sent 'error' notification")


if __name__ == "__main__":
    test_notifications()
