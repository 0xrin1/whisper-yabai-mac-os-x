#!/usr/bin/env python3
"""
Unit tests for the error_handler module.
Tests error handling functionality and safe execution wrappers.
"""

import os
import sys
import logging
import unittest
from unittest.mock import MagicMock, patch

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to test
from src.core.error_handler import handle_error, safe_execute


class TestErrorHandler(unittest.TestCase):
    """Test error handling functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock logger
        self.mock_logger = MagicMock(spec=logging.Logger)

    def test_handle_error_logging(self):
        """Test that handle_error logs errors correctly."""
        test_error = ValueError("Test error")

        # Call the function with the mock logger
        handle_error(test_error, self.mock_logger)

        # Verify the mock logger was called correctly
        self.mock_logger.error.assert_any_call("Error: Test error")

        # Traceback is logged as the second error message, check that it was called twice
        self.assertEqual(self.mock_logger.error.call_count, 2)

    def test_handle_error_with_context(self):
        """Test handle_error with context."""
        test_error = ValueError("Test error")
        test_context = "Testing context"

        # Call the function with context
        handle_error(test_error, self.mock_logger, context=test_context)

        # Verify the mock logger was called with the right context
        self.mock_logger.error.assert_any_call(f"[{test_context}] Error: Test error")

    @patch("src.toast_notifications.notify_error")
    def test_handle_error_with_notification(self, mock_notify):
        """Test handle_error with notification."""
        test_error = ValueError("Test error")
        test_message = "Test notification message"

        # Call the function with notification
        handle_error(test_error, self.mock_logger, notification_text=test_message)

        # Verify notify_error was called
        mock_notify.assert_called_once_with(test_message)

    def test_handle_error_with_should_raise(self):
        """Test handle_error re-raises exception when should_raise is True."""
        test_error = ValueError("Test error")

        # Call the function with should_raise=True and verify it raises
        with self.assertRaises(ValueError):
            handle_error(test_error, self.mock_logger, should_raise=True)

    def test_handle_error_with_fallback(self):
        """Test handle_error calls fallback action."""
        test_error = ValueError("Test error")
        mock_fallback = MagicMock()

        # Call the function with fallback
        handle_error(test_error, self.mock_logger, fallback_action=mock_fallback)

        # Verify fallback was called
        mock_fallback.assert_called_once()

    def test_safe_execute_success(self):
        """Test safe_execute with successful function."""
        mock_func = MagicMock(return_value="Success")

        # Call safe_execute with the mock function
        result = safe_execute(mock_func, self.mock_logger)

        # Verify the function was called and the result returned
        mock_func.assert_called_once()
        self.assertEqual(result, "Success")

    def test_safe_execute_error(self):
        """Test safe_execute with failing function."""
        test_error = ValueError("Test error")
        mock_func = MagicMock(side_effect=test_error)

        # Call safe_execute with the mock function
        result = safe_execute(mock_func, self.mock_logger)

        # Verify the function was called and None was returned
        mock_func.assert_called_once()
        self.assertIsNone(result)

        # Verify the error was logged
        self.mock_logger.error.assert_any_call(f"Error: {test_error}")

    def test_safe_execute_with_args(self):
        """Test safe_execute passes args and kwargs correctly."""
        mock_func = MagicMock(return_value="Success")

        # Call safe_execute with args and kwargs
        test_args = ["arg1", "arg2"]
        test_kwargs = {"kwarg1": "value1", "kwarg2": "value2"}

        result = safe_execute(
            mock_func,
            self.mock_logger,
            context="Test context",
            error_message="Test error",
            args=test_args,
            kwargs=test_kwargs,
        )

        # Verify the function was called with the right args
        mock_func.assert_called_once_with(
            "arg1", "arg2", kwarg1="value1", kwarg2="value2"
        )
        self.assertEqual(result, "Success")


if __name__ == "__main__":
    unittest.main()
