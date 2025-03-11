# Configuration Components

This directory contains modules related to configuration management for the voice control system.

## Components

- **config.py**: Centralized configuration management system

## Usage

The configuration system provides a unified interface for accessing configuration values:

```python
from src.config.config import config

# Get configuration values
model_size = config.get('MODEL_SIZE', 'tiny')
recording_timeout = config.get('RECORDING_TIMEOUT', 7.0)
```

## Design Principles

- **Unified Access**: Single point of access for all configuration values
- **Hierarchical Loading**: Configuration loaded from multiple sources
  - Environment variables
  - Configuration files
  - Default values
- **Type Conversion**: Automatic conversion of configuration values to appropriate types
