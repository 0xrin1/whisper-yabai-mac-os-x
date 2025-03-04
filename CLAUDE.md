# Whisper Voice Control Coding Guidelines

## Commands
- Run daemon: `python src/daemon.py`
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

- **Key Parameters**:
  - Trigger word: "hey"
  - Default command recording: 7 seconds
  - Default dictation recording: 10 seconds 
  - Minimum recording duration: 3 seconds
  - Silence thresholds: 300 (command), 400 (dictation), 500 (trigger)

## Troubleshooting
- Mute toggle with Ctrl+Shift+M if system gets stuck
- If system isn't responding to "hey", restart with ESC key
- Most common issues:
  - Audio device not available (check permissions)
  - Recording stops too early (fixed with longer min duration)
  - Whisper model loading issues (check installation)
  - Dictation not working (multiple fixes for "dictate" command recognition)