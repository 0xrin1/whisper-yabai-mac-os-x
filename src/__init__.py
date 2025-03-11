#!/usr/bin/env python3
"""
Whisper Voice Control - Voice command system for macOS using Whisper and Yabai.

This package provides a voice control system that uses OpenAI's Whisper model for
speech recognition and integrates with the Yabai window manager for advanced
window control on macOS.

Modules:
- core: Core infrastructure components (state management, error handling, etc.)
- audio: Audio recording, processing and speech synthesis
- utils: Utility modules for various functionality
- ui: User interface components
- config: Configuration management
- tests: Test modules
"""

# Version information
__version__ = "1.0.0"
__author__ = "Whisper Voice Control Team"

# Add convenient imports
from src.core.state_manager import state
from src.config.config import config

# Make main components easily accessible
import src.audio.speech_synthesis as speech
import src.utils.assistant as assistant
