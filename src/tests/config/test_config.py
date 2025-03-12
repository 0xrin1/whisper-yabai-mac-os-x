#!/usr/bin/env python3
"""
Unit tests for the config module.
Tests configuration management functionality.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, mock_open

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to test
# We'll import the Config class directly without initializing it
from src.config.config import Config as OriginalConfig


# Create a testable subclass
class TestableConfig(OriginalConfig):
    def _load_from_env(self):
        """Override to access environment directly without dotenv."""
        env_mapping = {
            "WHISPER_MODEL_SIZE": "MODEL_SIZE",
            "COMMAND_TRIGGER": "COMMAND_TRIGGER",
            "DICTATION_TRIGGER": "DICTATION_TRIGGER",
            "RECORDING_TIMEOUT": ("RECORDING_TIMEOUT", float),
            "DICTATION_TIMEOUT": ("DICTATION_TIMEOUT", float),
            "TRIGGER_TIMEOUT": ("TRIGGER_TIMEOUT", float),
            "COMMAND_SILENCE_THRESHOLD": ("COMMAND_SILENCE_THRESHOLD", int),
            "DICTATION_SILENCE_THRESHOLD": ("DICTATION_SILENCE_THRESHOLD", int),
            "TRIGGER_SILENCE_THRESHOLD": ("TRIGGER_SILENCE_THRESHOLD", int),
            "BUFFER_SECONDS": ("BUFFER_SECONDS", int),
            "USE_LLM": ("USE_LLM", lambda v: v.lower() == "true"),
            "LLM_MODEL_PATH": "LLM_MODEL_PATH",
            "VOICE_NAME": "VOICE_NAME",
            "VOICE_RATE": ("VOICE_RATE", int),
            "VOICE_VOLUME": ("VOICE_VOLUME", float),
            "SPEECH_API_URL": "SPEECH_API_URL",
            "SPEECH_API_KEY": "SPEECH_API_KEY",
            "LOG_LEVEL": "LOG_LEVEL",
            "LOG_TO_FILE": ("LOG_TO_FILE", lambda v: v.lower() == "true"),
            "LOG_FILE": "LOG_FILE",
        }

        for env_var, config_key in env_mapping.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                if isinstance(config_key, tuple):
                    config_key, converter = config_key
                    try:
                        env_value = converter(env_value)
                    except Exception:
                        continue
                self._config[config_key] = env_value

    def _load_from_files(self):
        """Override to do nothing in tests unless we want it to."""
        pass


class TestConfig(unittest.TestCase):
    """Test configuration management functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset the Config singleton for each test
        TestableConfig._instance = None
        OriginalConfig._instance = None

        # Create a temporary config file
        self.temp_config_dir = tempfile.TemporaryDirectory()
        self.temp_config_path = os.path.join(
            self.temp_config_dir.name, "config", "config.json"
        )
        # Create the config directory
        os.makedirs(os.path.dirname(self.temp_config_path), exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        self.temp_config_dir.cleanup()

    def test_singleton_pattern(self):
        """Test that Config follows the singleton pattern."""
        config1 = TestableConfig()
        config2 = TestableConfig()

        # Both should be the same instance
        self.assertIs(config1, config2)

    def test_default_values(self):
        """Test that default values are correctly loaded."""
        config = TestableConfig()

        # Check some default values
        self.assertEqual(config.get("MODEL_SIZE"), "tiny")
        self.assertEqual(config.get("COMMAND_TRIGGER"), "hey")
        self.assertEqual(config.get("DICTATION_TRIGGER"), "type")
        self.assertEqual(config.get("RECORDING_TIMEOUT"), 7.0)
        self.assertEqual(config.get("CHANNELS"), 1)
        self.assertEqual(config.get("RATE"), 16000)

    def test_environment_variables(self):
        """Test that environment variables override defaults."""
        # Set environment variables
        with patch.dict(
            os.environ,
            {
                "WHISPER_MODEL_SIZE": "base",
                "COMMAND_TRIGGER": "computer",
                "RECORDING_TIMEOUT": "10.5",
                "USE_LLM": "false",
            },
            clear=True,
        ):
            # Initialize configuration with our patched environment
            config = TestableConfig(reset=True)

            # Check environment variables were applied
            self.assertEqual(config.get("MODEL_SIZE"), "base")
            self.assertEqual(config.get("COMMAND_TRIGGER"), "computer")
            self.assertEqual(config.get("RECORDING_TIMEOUT"), 10.5)
            self.assertEqual(config.get("USE_LLM"), False)

    def test_type_conversion(self):
        """Test that type conversion works correctly for environment variables."""
        # Set environment variables with types to convert
        with patch.dict(
            os.environ,
            {
                "RECORDING_TIMEOUT": "12.5",  # float
                "COMMAND_SILENCE_THRESHOLD": "250",  # int
                "USE_LLM": "true",  # bool
                "VOICE_RATE": "180",  # int
            },
            clear=True,
        ):
            # Re-initialize config with our patched environment and force reset
            config = TestableConfig(reset=True)

            # Check type conversion
            self.assertEqual(config.get("RECORDING_TIMEOUT"), 12.5)
            self.assertIsInstance(config.get("RECORDING_TIMEOUT"), float)

            self.assertEqual(config.get("COMMAND_SILENCE_THRESHOLD"), 250)
            self.assertIsInstance(config.get("COMMAND_SILENCE_THRESHOLD"), int)

            self.assertEqual(config.get("USE_LLM"), True)
            self.assertIsInstance(config.get("USE_LLM"), bool)

            self.assertEqual(config.get("VOICE_RATE"), 180)
            self.assertIsInstance(config.get("VOICE_RATE"), int)

    def test_config_file_loading(self):
        """Test loading configuration from a file."""

        # Create a custom subclass of TestableConfig that can load from our test file
        class FileTestConfig(TestableConfig):
            def _load_from_files(self):
                """Override to load our test config file."""
                config_file = self.temp_config_path
                if os.path.exists(config_file):
                    try:
                        with open(config_file, "r") as f:
                            file_config = json.load(f)
                            self._config.update(file_config)
                    except Exception:
                        pass

        # Create a test config file
        test_config = {
            "MODEL_SIZE": "medium",
            "COMMAND_TRIGGER": "jarvis",
            "DICTATION_TIMEOUT": 15.0,
            "USE_NEURAL_VOICE": True,
        }

        with open(self.temp_config_path, "w") as f:
            json.dump(test_config, f)

        # Create a custom config instance with our temp_config_path
        FileTestConfig.temp_config_path = self.temp_config_path
        config = FileTestConfig(reset=True)

        # Check config file values were applied
        self.assertEqual(config.get("MODEL_SIZE"), "medium")
        self.assertEqual(config.get("COMMAND_TRIGGER"), "jarvis")
        self.assertEqual(config.get("DICTATION_TIMEOUT"), 15.0)
        self.assertEqual(config.get("USE_NEURAL_VOICE"), True)

    def test_get_with_default(self):
        """Test getting values with defaults."""
        config = TestableConfig()

        # Test with an existing key
        self.assertEqual(config.get("MODEL_SIZE"), "tiny")

        # Test with a non-existent key and default
        self.assertEqual(
            config.get("NON_EXISTENT_KEY", "default_value"), "default_value"
        )

        # Test with a non-existent key and no default
        self.assertIsNone(config.get("ANOTHER_NON_EXISTENT_KEY"))

    def test_set_value(self):
        """Test setting configuration values."""
        config = TestableConfig()

        # Set a new value
        config.set("CUSTOM_SETTING", "custom_value")
        self.assertEqual(config.get("CUSTOM_SETTING"), "custom_value")

        # Override an existing value
        config.set("MODEL_SIZE", "large")
        self.assertEqual(config.get("MODEL_SIZE"), "large")

    def test_as_dict(self):
        """Test getting the full configuration as a dictionary."""
        config = TestableConfig()

        # Set a custom value
        config.set("CUSTOM_SETTING", "custom_value")

        # Get the full config
        config_dict = config.as_dict()

        # Check it's a dictionary and contains our values
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict["MODEL_SIZE"], "tiny")  # default value
        self.assertEqual(config_dict["CUSTOM_SETTING"], "custom_value")  # custom value

    def test_save_to_file(self):
        """Test saving configuration to a file."""
        config = TestableConfig()

        # Set a custom value
        config.set("CUSTOM_SETTING", "custom_value")

        # Save to our temporary file
        success = config.save_to_file(self.temp_config_path)

        # Check the save was successful
        self.assertTrue(success)

        # Check the file was created and contains our configuration
        self.assertTrue(os.path.exists(self.temp_config_path))

        with open(self.temp_config_path, "r") as f:
            saved_config = json.load(f)

        self.assertEqual(saved_config["MODEL_SIZE"], "tiny")
        self.assertEqual(saved_config["CUSTOM_SETTING"], "custom_value")


if __name__ == "__main__":
    unittest.main()
