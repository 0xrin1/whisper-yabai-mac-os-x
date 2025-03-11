# toast_notifications

Toast notification module for macOS.
Provides visual and audible feedback for voice control actions.
Uses osascript to display notifications for maximum compatibility.

Source: `ui/toast_notifications.py`

## Function: `send_notification(title: str, message: str, identifier: Optional[str] = None,
                     timeout: int = 5, sound: bool = True)`

Send a macOS notification.

    Args:
        title: The notification title
        message: The notification message
        identifier: Optional unique identifier for the notification (for updating/removing)
        timeout: Auto-dismiss after this many seconds (0 = don't auto-dismiss)
        sound: Whether to play a sound with the notification

    Returns:
        The notification identifier

## Function: `update_notification(identifier: str, title: str, message: str,
                       timeout: int = 5, sound: bool = False)`

Update an existing notification or create a new one if it doesn't exist.

    Args:
        identifier: The notification identifier to update
        title: The new notification title
        message: The new notification message
        timeout: Reset auto-dismiss timer to this many seconds (0 = don't auto-dismiss)
        sound: Whether to play a sound with the notification

    Returns:
        The notification identifier

## Function: `remove_notification(identifier: str)`

Remove a notification by its identifier.

    Args:
        identifier: The notification identifier to remove

## Function: `remove_all_notifications()`

Remove all active notifications.

## Function: `notify_listening(timeout: int = 10)`

Show a notification that we're listening for commands.

## Function: `notify_processing(timeout: int = 30)`

Show a notification that we're processing audio.

## Function: `notify_command_executed(command: str, timeout: int = 5)`

Show a notification that a command was executed.

## Function: `notify_error(error_msg: str, timeout: int = 10)`

Show an error notification.

## Function: `test_notifications()`

Test the notification system.
