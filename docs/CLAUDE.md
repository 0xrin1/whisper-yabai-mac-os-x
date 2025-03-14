# Whisper Voice Control Essential Guidelines

## Commands

- Run daemon: `python src/daemon.py`
- Run daemon with API: `python src/daemon.py --api`
- Run onboarding: `python src/daemon.py --onboard`
- Run simplified daemon: `python src/utils/simple_dictation.py`
- Check permissions: `python src/permissions_check.py`
- Run tests with pytest: `python -m pytest`
- Run specific test module: `python -m pytest src/tests/audio/test_audio_processor.py`
- Run tests with mocks: `python src/tests/discover_tests.py --mock`
- Install deps: `pip install -r requirements.txt`
- Run Speech API: `./scripts/run_speech_api.sh`
- Run Cloud Code API: `./scripts/launch_cloud_api.sh`
- Test LLM Greetings: `python src/utils/ollama_greeting_generator.py`
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
- `speech_recognition_api.py`: Standalone speech recognition API
- `speech_recognition_client.py`: Client for the speech recognition API
- `api_server.py`: Cloud Code API server

## LLM Configuration

- OpenWebUI Server URL: (from environment) `LLM_SERVER_URL` (default: `http://192.168.191.55:7860`)
- OpenWebUI API Key: (from environment) `OPENWEBUI_API_KEY`
- Model Name: (from environment) `LLM_MODEL_NAME` (default: `unsloth/QwQ-32B-GGUF:Q4_K_M`)
- Dynamic greeting generation using direct LLM API calls
- Improved validation to detect and filter out internal "thinking" model responses
- Custom Jarvis-style greetings with the LLM's personality

### Recommended LLM Models

- QwQ-32B-GGUF: Main remote model via OpenWebUI
- Qwen2-0.5B-Instruct: Lightweight, fast response (local fallback)
- DeepSeek-Coder-1.3B-Instruct: Better command interpretation (local fallback)

## Neural Voice Configuration

- Server port: 6000 (default)
- IMPORTANT: Never implement fallback speech synthesis. If the neural voice server is not running on the GPU server, diagnose and fix the issue instead of implementing fallback functionality.

## Speech Recognition API Configuration

- API Server port: 8080 (default)
- Client environment variables:
  - `USE_SPEECH_API=true` - Enable API client
  - `SPEECH_API_URL=http://server-ip:8080` - API server URL
- Server environment variables:
  - `DEFAULT_MODEL_SIZE=large-v3` - Default Whisper model
  - `SPEECH_API_HOST=0.0.0.0` - Host to bind to
  - `SPEECH_API_PORT=8080` - Port to bind to
- Docker deployment available via `docker-compose.yml`

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

## Test Organization Guidelines

- Tests are organized in module-specific directories:

  - `src/tests/api/`: Tests for API components
  - `src/tests/audio/`: Tests for audio processing
  - `src/tests/config/`: Tests for configuration
  - `src/tests/core/`: Tests for core functionality
  - `src/tests/ui/`: Tests for UI components
  - `src/tests/utils/`: Tests for utilities
  - `src/tests/integration/`: Tests for end-to-end flows
  - `src/tests/common/`: Shared utilities for tests

- Use common test utilities:

  - `from src.tests.common.base import BaseTestCase` for standard test cases
  - `from src.tests.common.mocks import mock_speech_recognition_client` for mocks
  - `from src.tests.common.speech import synthesize_speech` for speech utilities

- CI Testing:
  - Use `python -m pytest -c pytest.ci.ini` for CI-specific test configurations
  - Mark tests that should be skipped in CI with `@pytest.mark.ci_skip`
  - Use environment variables to control test behavior:
    - `MOCK_TEST_MODE=true` to enable mock mode
    - `SKIP_AUDIO_RECORDING=true` to skip actual audio recording
    - `SKIP_AUDIO_PLAYBACK=true` to skip actual audio playback
    - `USE_MOCK_SPEECH=true` to use mock speech synthesis

## Claude Code Guidelines

- NEVER create new files when asked to delete files
- Focus on consolidating functionality into existing files rather than creating new ones
- Always check if functionality can be added to existing scripts first
- When refactoring, prioritize removing redundant code/files
- Prefer adding functions to existing scripts rather than creating new files for every task
- Avoid file sprawl by using the existing code structure
