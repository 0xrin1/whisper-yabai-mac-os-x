# config

Configuration management system for the voice control application.
Centralizes configuration from environment variables, settings files, and defaults.

Source: `config/config.py`

## Class: Config

Centralized configuration for voice control system.
    Implements the Singleton pattern to ensure consistent configuration across modules.

## Function: `__init__(self, reset=False)`

Initialize configuration if not already initialized.

        Args:
            reset: If True, force reinitialization (for testing)

## Function: `_load_defaults(self)`

Load default configuration values.

## Function: `_load_from_env(self)`

Load configuration from environment variables.

## Function: `_load_from_files(self)`

Load configuration from JSON files.

## Function: `get(self, key: str, default: Any = None)`

Get configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Configuration value or default

## Function: `set(self, key: str, value: Any)`

Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value

## Function: `save_to_file(self, filepath: Optional[str] = None)`

Save current configuration to a JSON file.

        Args:
            filepath: Path to save configuration file (optional)

        Returns:
            True if saved successfully, False otherwise
