# User Interface Components

This directory contains modules related to the user interface of the voice control system.

## Components

- **toast_notifications.py**: Toast notification system for user feedback

## Usage

These modules provide the user interface functionality of the application:

```python
from src.ui.toast_notifications import send_notification, notify_command_executed, notify_error
```

## Design Principles

- **User Feedback**: Provide clear feedback to the user about system state
- **Non-intrusive**: Minimize disruption to the user's workflow
- **Consistent Style**: Maintain consistent UI style throughout the application