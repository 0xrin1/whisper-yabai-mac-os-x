# error_handler

Error handling utilities for the voice control system.
Provides consistent error handling patterns across modules.

Source: `core/error_handler.py`

## Function: `handle_error(
    error: Exception,
    logger: logging.Logger,
    context: str = "",
    notification_text: Optional[str] = None,
    should_raise: bool = False,
    fallback_action: Optional[Callable[[], Any]] = None
)`

Standardized error handling across the application.

    Args:
        error: The exception that was raised
        logger: The module-specific logger to use
        context: Optional context about where the error occurred
        notification_text: Text to show in notification (if None, no notification)
        should_raise: Whether to re-raise the exception after handling
        fallback_action: Optional function to call as a fallback

## Function: `safe_execute(
    func: Callable,
    logger: logging.Logger,
    context: str = "",
    error_message: str = "Operation failed",
    notification: bool = False,
    should_raise: bool = False,
    fallback_action: Optional[Callable[[], Any]] = None,
    args: List = None,
    kwargs: Dict = None
)`

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
