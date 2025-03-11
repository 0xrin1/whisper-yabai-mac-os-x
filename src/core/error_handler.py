#!/usr/bin/env python3
"""
Error handling utilities for the voice control system.
Provides consistent error handling patterns across modules.
"""

import logging
import traceback
from typing import Optional, Callable, Any, List, Dict

# Create a logger for this module
logger = logging.getLogger("error-handler")


def handle_error(
    error: Exception,
    logger: logging.Logger,
    context: str = "",
    notification_text: Optional[str] = None,
    should_raise: bool = False,
    fallback_action: Optional[Callable[[], Any]] = None,
) -> None:
    """
    Standardized error handling across the application.

    Args:
        error: The exception that was raised
        logger: The module-specific logger to use
        context: Optional context about where the error occurred
        notification_text: Text to show in notification (if None, no notification)
        should_raise: Whether to re-raise the exception after handling
        fallback_action: Optional function to call as a fallback
    """
    # Log the error with context and full traceback
    error_prefix = f"[{context}] " if context else ""
    logger.error(f"{error_prefix}Error: {error}")
    logger.error(traceback.format_exc())

    # Show notification if requested
    if notification_text:
        try:
            from src.ui.toast_notifications import notify_error

            notify_error(notification_text)
        except Exception as e:
            logger.error(f"Failed to show error notification: {e}")

    # Execute fallback action if provided
    if fallback_action:
        try:
            logger.info(f"Attempting fallback action for {context}")
            fallback_action()
        except Exception as fallback_err:
            logger.error(f"Fallback action failed: {fallback_err}")

    # Re-raise if requested
    if should_raise:
        raise error


def safe_execute(
    func: Callable,
    logger: logging.Logger,
    context: str = "",
    error_message: str = "Operation failed",
    notification: bool = False,
    should_raise: bool = False,
    fallback_action: Optional[Callable[[], Any]] = None,
    args: List = None,
    kwargs: Dict = None,
) -> Any:
    """
    Execute a function with standardized error handling.

    Args:
        func: The function to execute
        logger: The module-specific logger to use
        context: Optional context about the operation
        error_message: Message to log/notify on error
        notification: Whether to show notification on error
        should_raise: Whether to re-raise exception
        fallback_action: Optional function to call on error
        args: Positional arguments to pass to the function
        kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call, or None on error
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    try:
        return func(*args, **kwargs)
    except Exception as e:
        notification_text = error_message if notification else None
        handle_error(
            e,
            logger,
            context=context,
            notification_text=notification_text,
            should_raise=should_raise,
            fallback_action=fallback_action,
        )
        return None
