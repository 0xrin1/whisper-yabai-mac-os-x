#!/usr/bin/env python3
"""
Configuration management system for the voice control application.
Centralizes configuration from environment variables, settings files, and defaults.
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from dotenv import load_dotenv

logger = logging.getLogger("config")


class Config:
    """
    Centralized configuration for voice control system.
    Implements the Singleton pattern to ensure consistent configuration across modules.
    """

    _instance = None

    def __new__(cls, reset=False):
        """
        Ensure only one instance exists (Singleton pattern).

        Args:
            reset: If True, reset the singleton instance (for testing)
        """
        if cls._instance is None or reset:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, reset=False):
        """
        Initialize configuration if not already initialized.

        Args:
            reset: If True, force reinitialization (for testing)
        """
        if self._initialized and not reset:
            return

        # Load environment variables
        load_dotenv()

        # Store configuration
        self._config = {}
        self._load_defaults()
        self._load_from_env()
        self._load_from_files()

        self._initialized = True
        logger.debug("Configuration initialized")

    def _load_defaults(self):
        """Load default configuration values."""
        self._config.update(
            {
                # Audio settings
                "CHUNK_SIZE": 1024,
                "FORMAT": "paInt16",
                "CHANNELS": 1,
                "RATE": 16000,
                # Whisper model
                "MODEL_SIZE": "tiny",
                # Triggers
                "COMMAND_TRIGGER": "hey",
                "DICTATION_TRIGGER": "type",
                "ASSISTANT_TRIGGER": "hey jarvis",
                # Timeouts
                "RECORDING_TIMEOUT": 7.0,
                "DICTATION_TIMEOUT": 10.0,
                "TRIGGER_TIMEOUT": 1.5,
                # Silence thresholds
                "COMMAND_SILENCE_THRESHOLD": 300,
                "DICTATION_SILENCE_THRESHOLD": 400,
                "TRIGGER_SILENCE_THRESHOLD": 500,
                # Audio buffer
                "BUFFER_SECONDS": 5,
                # LLM settings
                "USE_LLM": True,
                "LLM_MODEL_PATH": None,
                # Neural voice settings
                "NEURAL_SERVER": None,
                "NEURAL_VOICE_ID": "p230",
                # Logging
                "LOG_LEVEL": "INFO",
                "LOG_TO_FILE": False,
                "LOG_FILE": "voice_control.log",
            }
        )

    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Map environment variables to config
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
            "NEURAL_SERVER": "NEURAL_SERVER",
            "NEURAL_VOICE_ID": "NEURAL_VOICE_ID",
            "LOG_LEVEL": "LOG_LEVEL",
            "LOG_TO_FILE": ("LOG_TO_FILE", lambda v: v.lower() == "true"),
            "LOG_FILE": "LOG_FILE",
        }

        # Process environment variables with type conversion
        for env_var, config_key in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if isinstance(config_key, tuple):
                    # Apply type conversion if specified
                    config_key, converter = config_key
                    try:
                        env_value = converter(env_value)
                    except Exception as e:
                        logger.warning(
                            f"Failed to convert {env_var}='{env_value}': {e}"
                        )
                        continue
                self._config[config_key] = env_value

    def _load_from_files(self):
        """Load configuration from JSON files."""
        config_files = [
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config/config.json",
            ),
            os.path.expanduser("~/.config/whisper_voice_control/config.json"),
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        file_config = json.load(f)
                        self._config.update(file_config)
                        logger.info(f"Loaded configuration from {config_file}")
                except Exception as e:
                    logger.warning(
                        f"Failed to load configuration from {config_file}: {e}"
                    )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
        logger.debug(f"Configuration updated: {key}={value}")

    def as_dict(self) -> Dict[str, Any]:
        """
        Get full configuration as dictionary.

        Returns:
            Dictionary with all configuration values
        """
        return self._config.copy()

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        """
        Save current configuration to a JSON file.

        Args:
            filepath: Path to save configuration file (optional)

        Returns:
            True if saved successfully, False otherwise
        """
        if filepath is None:
            config_dir = os.path.expanduser("~/.config/whisper_voice_control")
            os.makedirs(config_dir, exist_ok=True)
            filepath = os.path.join(config_dir, "config.json")

        # Ensure directory exists
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        try:
            with open(filepath, "w") as f:
                json.dump(self._config, f, indent=4, sort_keys=True)
            logger.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration to {filepath}: {e}")
            return False


# Create a singleton instance
config = Config()
