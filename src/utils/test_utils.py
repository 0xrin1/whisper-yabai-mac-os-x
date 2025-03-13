#!/usr/bin/env python3
"""
Test utilities for testing refactored LLM and greeting code.
"""

import logging
import unittest
from unittest.mock import MagicMock, patch

# Import modules to test
from src.utils.llm_client import LLMClient
from src.utils.greeting_generator import generate_greeting, GreetingGenerator

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-utils")

class TestLLMClient(unittest.TestCase):
    """Tests for the refactored LLM Client."""

    @patch('requests.get')
    def test_check_connection(self, mock_get):
        """Test that connection check works properly."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "test-model"}]}
        mock_get.return_value = mock_response

        # Test client
        client = LLMClient()
        self.assertTrue(client.server_available)
        self.assertEqual(client.api_format, "openai")

    @patch('requests.post')
    def test_generate(self, mock_post):
        """Test that text generation works."""
        # Mock successful generation
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_post.return_value = mock_response

        # Test with mocked successful connection
        client = LLMClient()
        client.server_available = True
        client.api_format = "openai"

        response = client.generate("Test prompt")
        self.assertEqual(response, "Test response")

class TestGreetingGenerator(unittest.TestCase):
    """Tests for the refactored greeting generator."""

    def test_base_greeting_generator(self):
        """Test that base greeting generator returns a valid greeting."""
        generator = GreetingGenerator()
        greeting = generator.get_greeting()
        self.assertIsNotNone(greeting)
        self.assertTrue(len(greeting) > 0)

    def test_greeting_cleaning(self):
        """Test that greeting cleaning works properly."""
        generator = GreetingGenerator()

        # Test with invalid greeting formats
        self.assertEqual("", generator._clean_greeting(""))
        self.assertEqual("", generator._clean_greeting("<think>This is thinking</think>"))
        self.assertEqual("", generator._clean_greeting("I should generate a witty greeting"))
        self.assertEqual("", generator._clean_greeting("Let me think about a good greeting"))
        self.assertEqual("", generator._clean_greeting("Okay, here's a greeting"))

        # Test with valid greeting
        valid = "System online. Sarcasm levels: optimal."
        self.assertEqual(valid, generator._clean_greeting(valid))

    @patch('src.utils.greeting_generator.get_greeting_generator')
    def test_generate_greeting(self, mock_get_generator):
        """Test the main greeting generation function."""
        # Mock generator
        mock_generator = MagicMock()
        mock_generator.get_greeting.return_value = "Test greeting"
        mock_get_generator.return_value = mock_generator

        # Test greeting generation
        greeting = generate_greeting()
        self.assertEqual(greeting, "Test greeting")

if __name__ == "__main__":
    unittest.main()
