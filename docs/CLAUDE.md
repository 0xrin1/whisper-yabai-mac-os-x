# Whisper Voice Control Coding Guidelines

## Commands
- Run daemon: `python src/daemon.py`  # Now uses unified modular architecture
- Run simplified daemon: `python src/simple_dictation.py`
- Run ultra simplified version: `python src/ultra_simple_dictation.py`
- Check permissions: `python src/permissions_check.py`
- Test specific module: `python src/test_*.py`
- Install deps: `pip install -r requirements.txt`

## Continuous Integration
- CI runs on GitHub Actions for all PRs and main branch pushes
- GitHub Actions workflows: 
  - `.github/workflows/ci.yml` - Main CI workflow
  - `.github/workflows/lint.yml` - Code quality checks
- Badge status: 
  - ![CI Status](https://github.com/0xrin1/whisper-yabai-mac-os-x/actions/workflows/ci.yml/badge.svg)
  - ![Lint Status](https://github.com/0xrin1/whisper-yabai-mac-os-x/actions/workflows/lint.yml/badge.svg)

### CI Process
- Runs on macOS environment
- Syntax and import checks for all Python files
- Module-specific import tests for core components
- Code quality checks (prints, TODOs, hardcoded paths)
- Neural voice tests with mock audio system
- Unit tests for all test_*.py modules with audio mocks

### Mock Testing Environment
- Uses src/test_utils.py for mock audio recording and playback
- Environment variables control mock behavior:
  - MOCK_TEST_MODE=true: Enable full mock environment
  - SKIP_AUDIO_RECORDING=true: Skip actual microphone recording
  - SKIP_AUDIO_PLAYBACK=true: Skip actual audio playback
  - USE_MOCK_SPEECH=true: Use mock speech synthesis
- Mock helpers available:
  - is_ci_environment(): Check if running in CI
  - mock_speech_synthesis(): Mock speech function
  - mock_whisper_transcription(): Mock transcription
  - mock_audio_recorder(): Mock recording device
  - setup_mock_environment(): Configure mock environment

## Code Style
- Use 4-space indentation
- Follow PEP 8 naming conventions (snake_case for functions/variables)
- Class names in PascalCase
- Constants in UPPER_SNAKE_CASE
- Import order: standard lib -> third-party -> local modules
- Type annotations for function parameters and returns
- Document classes and functions with docstrings
- Use context managers for resource handling (with statements)
- Exception handling with specific exception types
- Log errors with appropriate logging levels
- Use f-strings for string formatting
- Use absolute imports with `src.` prefix (e.g., `from src.module import X`)

## System Architecture
- **Dual-Mode Operation**:
  - **Command Mode**: Process speech as computer control commands
  - **Dictation Mode**: Type speech as text at the cursor position

- **Trigger Word Detection**:
  - System listens for "hey" to activate full command recording
  - Uses short 1.5 second recordings with lower processing power
  - After trigger detection, starts full 7-second command recording

- **Smart Recording**:
  - Records until silence detected (with mode-specific thresholds)
  - Command mode: min 3 seconds, timeout after 4s silence
  - Dictation mode: min 3 seconds, timeout after 3s silence
  - Different sensitivity thresholds for each mode

- **Audio Processing**:
  - Uses Whisper for speech recognition
  - Processes audio asynchronously in worker thread
  - Detects commands through multiple parsing methods

- **LLM Command Interpretation**:
  - Supports multiple model architectures (Qwen, DeepSeek, LLaMA)
  - Model-specific prompt formats
  - Improved JSON parsing and error handling
  - Supports 4096 token context window
  - GPU acceleration support

- **Key Parameters**:
  - Trigger word: "hey"
  - Default command recording: 7 seconds
  - Default dictation recording: 10 seconds 
  - Minimum recording duration: 3 seconds
  - Silence thresholds: 300 (command), 400 (dictation), 500 (trigger)

## Current System Architecture (Unified)
- **Core Infrastructure**:
  - `config.py`: Centralized configuration management
  - `error_handler.py`: Standardized error handling
  - `logging_config.py`: Consistent logging setup
  - `resource_manager.py`: System resource management
  - `state_manager.py`: Centralized state management
  
- **Functional Components**:
  - `audio_recorder.py`: Audio recording functionality
  - `audio_processor.py`: Audio processing and transcription
  - `trigger_detection.py`: Trigger word detection
  - `core_dictation.py`: Shared dictation functionality
  - `dictation.py`: Main dictation implementation
  - `hotkey_manager.py`: Keyboard hotkey handling
  - `continuous_recorder.py`: Continuous audio recording with buffer
  - `daemon.py`: Main daemon with modular architecture

- **Recommended LLM Models**:
  - Qwen2-0.5B-Instruct: Lightweight, fast response
  - DeepSeek-Coder-1.3B-Instruct: Better command interpretation
  - See models/README.md for installation instructions

## Troubleshooting
- Mute toggle with Ctrl+Shift+M if system gets stuck
- If system isn't responding to "hey", restart with ESC key
- Most common issues:
  - Audio device not available (check permissions)
  - Recording stops too early (fixed with longer min duration)
  - Whisper model loading issues (check installation)
  - Dictation not working (multiple fixes for "dictate" command recognition)
  - LLM response parsing errors (try different model architecture)

## Recent System Unification Project
- **What we accomplished**:
  - Unified daemon.py with modular architecture (removed duplicate code)
  - Created a simpler version for users who need minimal functionality
  - Ensured all tests work with the new unified architecture
  - Improved import path handling for better module resolution
  - Maintained backward compatibility with existing scripts

- **Files modified**:
  - Updated: daemon.py to use modular architecture
  - Created: ultra_simple_dictation.py for minimal functionality
  - Removed: daemon_refactored.py (merged into daemon.py)
  - Updated docs: docs/CLAUDE.md
  
## Testing and Quality Enhancement Project
- **What we accomplished**:
  - Added comprehensive unit tests for core components
  - Enhanced error handling throughout the audio subsystem
  - Improved documentation with detailed examples
  - Added resilience to hardware failures and permission issues
  - Implemented comprehensive mocking strategies for testing without audio hardware

- **Key test files added**:
  - test_state_manager.py: Tests for the state management singleton
  - test_audio_processor.py: Tests for audio processing with mocked Whisper
  - test_core_dictation.py: Tests for text typing functionality
  
- **Key enhancements**:
  - Enhanced error detection and recovery in audio_recorder.py
  - Added detailed troubleshooting information for microphone issues
  - Improved reliability of audio recording with better error handling
  - Created detailed component documentation in src/audio/README.md
  - Implemented mock-based testing strategy for audio components

## Codebase Streamlining Project
- **What we accomplished**:
  - Eliminated redundant files with overlapping functionality
  - Standardized on single implementation for each feature
  - Reduced complexity by removing stale code
  - Improved maintainability by reducing duplication
  - Added pre-commit hooks for code quality checks

- **Files removed**:
  - Removed: neural_speech_synthesis.py (replaced by neural_voice_client.py)
  - Removed: direct_dictation.py (functionality covered by direct_typing.py)
  - Kept: dictation.py, simple_dictation.py, ultra_simple_dictation.py (distinct use cases)

- **Pre-commit hooks**:
  - Added pre-commit hooks to catch common issues before committing
  - Checks for syntax errors, import problems, and code quality issues
  - Install with: `git config core.hooksPath .githooks`
  - See `.githooks/README.md` for more details

## Maintainability Enhancement Project
- **What we accomplished**:
  - Created centralized configuration system with multiple configuration sources
  - Implemented standardized error handling utilities
  - Added resource management utilities for audio resources
  - Created common dictation functionality to eliminate code duplication
  - Enhanced code with comprehensive type annotations
  - Added unit tests for new infrastructure components
  - Documented architectural improvements in README
  - Improved extensibility with clear module boundaries

- **Files created**:
  - Created: config.py for centralized configuration
  - Created: error_handler.py for standardized error handling
  - Created: resource_manager.py for audio resource management
  - Created: logging_config.py for consistent logging
  - Created: core_dictation.py for shared dictation logic
  - Created: test_error_handler.py and test_config.py for testing
  - Added: config/config.json for user configuration

- **Key improvements**:
  - Reduced code duplication across dictation implementations
  - Standardized error handling patterns across modules
  - Centralized configuration from environment variables and files
  - Improved resource management to prevent leaks
  - Enhanced type annotations for better IDE support and documentation
  - Added unit tests for core infrastructure components
  - Created consistent logging configuration
  - Implemented singleton pattern for shared resources

## Enhanced Voice Model Implementation

- **Voice Personalization Project**:
  - Created advanced voice analysis system for personalized speech
  - Implemented voice profile extraction from voice recordings
  - Developed context-aware speech synthesis with dynamic adjustments
  - Added intelligent base voice selection based on voice characteristics
  
- **Key Features**:
  - Voice profile analysis extracts personal speech patterns
  - Dynamic voice adjustments based on context (questions, statements, exclamations)
  - Context-sensitive pitch and rate modifications
  - Customizable voice parameters for fine-tuning

- **Files Created/Modified**:
  - Created: voice_models/ directory structure
  - Enhanced: speech_synthesis.py with custom voice capabilities
  - Enhanced: voice_training.py with voice profile extraction
  - Created: scripts/neural_voice/test_neural_voice.py for voice comparison testing
  - Created: scripts/neural_voice/create_voice_model.sh for streamlined model creation
  
- **Technical Approach**:
  - Voice sample analysis for characteristic extraction
  - Voice profile creation with optimal parameters
  - Base voice selection using extracted characteristics
  - Dynamic speech parameter adjustment based on context
  - Seamless fallback to system voices when needed

## Neural Voice Implementation

- **GPU-Accelerated Neural Voice System**:
  - Implemented high-performance neural voice training on RTX 3090
  - Created client-server architecture for efficient voice synthesis
  - Added automatic fallback to parameter-based voice when server unavailable
  - Developed modular system for easy deployment across machines

- **Neural Voice Key Components**:
  - `neural_voice_server.py`: GPU-accelerated voice synthesis server
  - `neural_voice_client.py`: Client that connects to GPU server
  - `train_neural_voice.py`: High-performance model training
  - `speech_synthesis.py`: Enhanced with neural voice support
  
- **Neural Training Parameters**:
  - Training epochs: 5000 (default), 10000 (extended quality)
  - Model: Tacotron2 with optimized parameters
  - Mixed precision for faster training
  - Dynamic batch sizing based on available GPU memory
  - Automatic phoneme generation and caching

- **Neural Server Configuration**:
  - Server port: 5001
  - Environment variable: `NEURAL_SERVER=http://gpu-server-ip:5001`
  - Caching system for frequently used phrases
  - Automatic fallback to parameter-based synthesis
  - GPU memory optimization

## Custom Voice Commands
- Create voice model: `./create_voice_model.sh`
- Test custom voice: `python test_neural_voice.py`
- Compare voices: `python src/speech_synthesis.py`
- Voice training: `python src/voice_training.py`

## Voice Model Parameters
- **Recommended base voices**: Daniel, Samantha, Alex
- **Pitch modifiers**: 0.92-0.98 range (lower = deeper voice)
- **Optimal sample count**: 40+ samples for best results
- **Context modifiers**:
  - Questions: +3% pitch
  - Exclamations: -2% pitch, +15% volume 
  - Statements: standard parameters

## Voice Model Guidelines
- Record in quiet environment with good microphone
- Include diverse speech patterns (commands, questions, statements)
- Use consistent speaking style and distance from microphone
- Include both trigger words and longer phrases
- Test with `test_neural_voice.py` after model creation