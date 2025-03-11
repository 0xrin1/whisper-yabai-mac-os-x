# logging_config

Centralized logging configuration for the voice control system.
Configures consistent logging across all modules.

Source: `core/logging_config.py`

## Function: `configure_logging(log_level: Optional[str] = None, log_file: Optional[str] = None)`

Configure logging for the entire application.

    Args:
        log_level: Override log level from config
        log_file: Override log file from config

## Function: `configure_module_loggers(module_levels)`

Configure log levels for specific modules.
