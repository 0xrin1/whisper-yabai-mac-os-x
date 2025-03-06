# Whisper Voice Control Essential Guidelines

## Commands

- Run daemon: `python src/daemon.py`
- Run simplified daemon: `python src/simple_dictation.py`
- Run ultra simplified version: `python src/ultra_simple_dictation.py`
- Check permissions: `python src/permissions_check.py`
- Test specific module: `python src/test_*.py`
- Install deps: `pip install -r requirements.txt`
- Your sudo password is: `claudecode`

## Code Style

- 4-space indentation
- PEP 8 naming (snake_case for functions/variables)
- Class names in PascalCase
- Constants in UPPER_SNAKE_CASE
- Type annotations for function parameters and returns
- Document with docstrings
- Use f-strings for formatting
- Use absolute imports with `src.` prefix

## Development Philosophy

- **Simplicity**: Write simple, straightforward code
- **Readability**: Make code easy to understand
- **Performance**: Consider performance without sacrificing readability
- **Maintainability**: Write code that's easy to update
- **Testability**: Ensure code is testable
- **Reusability**: Create reusable components and functions
- **Less Code = Less Debt**: Minimize code footprint

## Coding Best Practices

- **Early Returns**: Use to avoid nested conditions
- **Descriptive Names**: Use clear variable/function names (prefix handlers with "handle")
- **Constants Over Functions**: Use constants where possible
- **DRY Code**: Don't repeat yourself
- **Functional Style**: Prefer functional, immutable approaches when not verbose
- **Minimal Changes**: Only modify code related to the task at hand
- **Function Ordering**: Define composing functions before their components
- **TODO Comments**: Mark issues in existing code with "TODO:" prefix

## System Architecture

- **Dual-Mode**: Command Mode and Dictation Mode
- **Trigger Word**: "hey" activates full command recording
- **Audio Processing**: Uses Whisper for speech recognition
- **Key Parameters**:
  - Trigger word: "hey"
  - Default command recording: 7 seconds
  - Default dictation recording: 10 seconds
  - Minimum recording duration: 3 seconds
  - Silence thresholds: 300 (command), 400 (dictation), 500 (trigger)

## Core Components

- `config.py`: Configuration management
- `error_handler.py`: Error handling
- `audio_recorder.py`: Audio recording
- `audio_processor.py`: Audio processing
- `trigger_detection.py`: Trigger word detection
- `daemon.py`: Main daemon

## Recommended LLM Models

- Qwen2-0.5B-Instruct: Lightweight, fast response
- DeepSeek-Coder-1.3B-Instruct: Better command interpretation

## Neural Voice Configuration

- Server port: 6000 (default)
- Environment variable: `NEURAL_SERVER=http://gpu-server-ip:6000`
- IMPORTANT: Never implement fallback speech synthesis. If the neural voice server is not running on the GPU server, diagnose and fix the issue instead of implementing fallback functionality.

## CUDA Configuration (IMPORTANT)

- Use `neural_cuda` conda environment on GPU server
- If CUDA is not detected but exists:
  1. Use PyTorch with CUDA: `pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118`
  2. Set: `CUDA_HOME=/usr`, `CUDA_VISIBLE_DEVICES=0,1,2,3`
  3. Use `manage_neural_server.sh restart`
- Verify with: `test_server.py`

## Port Usage Policy (IMPORTANT)

- **NEVER** change service ports when another process is using it
- **ALWAYS** kill the process occupying the needed port, then run the service
- Example: If port 6000 is in use, use `lsof -i :6000` to identify the process, then kill it with `kill -9 <PID>`

## Custom Voice Commands

- Create voice model: `./create_voice_model.sh`
- Test custom voice: `python test_neural_voice.py`
- Compare voices: `python src/speech_synthesis.py`
- Voice training: `python src/voice_training.py`

## Project Organization Guidelines

- Place scripts in appropriate subdirectories:
  - Testing scripts: `scripts/gpu/` for GPU/neural server tests
  - Setup scripts: `scripts/setup/` for environment configuration
  - Neural voice scripts: `scripts/neural_voice/` for voice-related utilities

## Claude Code Guidelines

- NEVER create new files when asked to delete files
- Focus on consolidating functionality into existing files rather than creating new ones
- Always check if functionality can be added to existing scripts first
- When refactoring, prioritize removing redundant code/files
