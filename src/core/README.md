# Core Infrastructure

This directory contains core infrastructure components that form the foundation of the voice control system.

## Components

- **state_manager.py**: Centralized state management for the entire application
- **error_handler.py**: Standardized error handling utilities
- **logging_config.py**: Consistent logging configuration
- **core_dictation.py**: Common dictation functionality used by all dictation implementations

## Usage

These modules should be imported at the application startup and used throughout the codebase to ensure consistent behavior.

Example:
```python
from src.core.state_manager import state
from src.core.error_handler import handle_error, safe_execute
from src.core.logging_config import configure_logging
```

## Design Principles

- **Singleton Pattern**: Used for shared resources like state manager
- **Centralized Error Handling**: Consistent error reporting across modules
- **Standardized Logging**: Unified logging format and levels