# Utility Components

This directory contains utility modules that provide various functionality for the voice control system.

## Components

- **assistant.py**: Conversational assistant functionality
- **command_processor.py**: Voice command processing
- **dictation.py**: Main dictation implementation
- **direct_typing.py**: Direct typing utilities
- **hotkey_manager.py**: Keyboard hotkey handling
- **llm_interpreter.py**: Language model command interpretation
- **simple_dictation.py**: Simplified dictation implementation
- **ultra_simple_dictation.py**: Ultra simplified dictation implementation

## Usage

These modules provide specialized functionality that can be imported as needed:

```python
from src.utils.hotkey_manager import hotkeys
from src.utils.command_processor import process_command
from src.utils.dictation import dictation
```

## Design Principles

- **Modularity**: Each module focuses on a specific functional area
- **Extensibility**: Designed to be easily extended with new functionality
- **Compatibility**: Maintains backward compatibility with existing scripts
- **Fallback Mechanisms**: Multiple implementation options with different complexity levels
