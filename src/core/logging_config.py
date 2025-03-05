#!/usr/bin/env python3
"""
Centralized logging configuration for the voice control system.
Configures consistent logging across all modules.
"""

import os
import logging
import logging.handlers
from typing import Optional

from src.config.config import config

def configure_logging(log_level: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """
    Configure logging for the entire application.
    
    Args:
        log_level: Override log level from config
        log_file: Override log file from config
    """
    # Get configuration from config system
    if log_level is None:
        log_level = config.get('LOG_LEVEL', 'INFO')
        
    if log_file is None:
        log_file = config.get('LOG_FILE', 'voice_control.log')
        
    log_to_file = config.get('LOG_TO_FILE', False)
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Add file handler if enabled
    if log_to_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logging.getLogger().addHandler(file_handler)
            logging.info(f"Logging to file: {os.path.abspath(log_file)}")
        except Exception as e:
            logging.error(f"Failed to set up file logging: {e}")
    
    # Configure specific loggers based on config settings
    # These modules might need different log levels
    configure_module_loggers({
        'audio-processor': config.get('AUDIO_PROCESSOR_LOG_LEVEL', log_level),
        'dictation': config.get('DICTATION_LOG_LEVEL', log_level),
        'command-processor': config.get('COMMAND_PROCESSOR_LOG_LEVEL', log_level),
        'hotkeys': config.get('HOTKEYS_LOG_LEVEL', log_level),
        'state-manager': config.get('STATE_MANAGER_LOG_LEVEL', log_level),
        'continuous-recorder': config.get('CONTINUOUS_RECORDER_LOG_LEVEL', log_level),
        'neural-voice': config.get('NEURAL_VOICE_LOG_LEVEL', log_level),
    })
    
    logging.info(f"Logging initialized at level: {log_level}")

def configure_module_loggers(module_levels):
    """Configure log levels for specific modules."""
    for module, level in module_levels.items():
        numeric_level = getattr(logging, level.upper(), None)
        if numeric_level is not None:
            logging.getLogger(module).setLevel(numeric_level)

def get_logger(name: str) -> logging.Logger:
    """
    Get a pre-configured logger for a module.
    
    Args:
        name: Name of the module/logger
        
    Returns:
        Logger instance configured for the module
    """
    return logging.getLogger(name)