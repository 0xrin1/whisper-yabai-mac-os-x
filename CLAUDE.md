# Whisper Voice Control Coding Guidelines

## Commands
- Run daemon: `python src/daemon.py`
- Run refactored daemon: `python src/daemon_refactored.py`
- Run simplified daemon: `python src/simple_dictation.py`
- Check permissions: `python src/permissions_check.py`
- Test specific module: `python src/test_*.py`
- Install deps: `pip install -r requirements.txt`

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

## Refactored System Architecture
- **Modular Components**:
  - `state_manager.py`: Centralized state management
  - `audio_recorder.py`: Audio recording functionality
  - `audio_processor.py`: Audio processing and transcription
  - `trigger_detection.py`: Trigger word detection
  - `dictation.py`: Dictation processing
  - `hotkey_manager.py`: Keyboard hotkey handling
  - `continuous_recorder.py`: Continuous audio recording with buffer
  - `daemon_refactored.py`: Main daemon with simplified logic

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

## Recent Refactoring Project
- **What we accomplished**:
  - Created modular architecture by splitting monolithic daemon.py
  - Enhanced LLM interpreter to support better models
  - Improved prompt engineering for command interpretation
  - Added better support for multiple model architectures
  - Fixed import statements to ensure proper module resolution

- **Files modified**:
  - Created/refactored: state_manager.py, audio_recorder.py, audio_processor.py, 
    trigger_detection.py, dictation.py, hotkey_manager.py, continuous_recorder.py, 
    daemon_refactored.py
  - Enhanced: llm_interpreter.py
  - Updated docs: models/README.md

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
  - Created: test_neural_voice.py for voice comparison testing
  - Created: create_voice_model.sh for streamlined model creation
  
- **Technical Approach**:
  - Voice sample analysis for characteristic extraction
  - Voice profile creation with optimal parameters
  - Base voice selection using extracted characteristics
  - Dynamic speech parameter adjustment based on context
  - Seamless fallback to system voices when needed

- **Future Extensions**:
  - GPU-accelerated neural voice cloning with RTX 3090
  - Server-based voice processing for higher quality
  - Coqui TTS integration for more natural voices
  - Voice style transfer for emotion-based responses

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