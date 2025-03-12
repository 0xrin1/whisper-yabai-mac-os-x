# Whisper Voice Control for macOS with Yabai

![CI Status](https://github.com/0xrin1/whisper-yabai-mac-os-x/actions/workflows/ci.yml/badge.svg)
![Lint Status](https://github.com/0xrin1/whisper-yabai-mac-os-x/actions/workflows/lint.yml/badge.svg)

A voice dictation system with Code Agent integration, leveraging the Speech Recognition API for dictation and "jarvis" triggered queries to Claude Code.

## Features

- Voice control for your Mac with two simple modes:
  - **Dictation mode (default)** - speak naturally to type text at cursor position without any trigger word
  - **Code Agent mode** - say "jarvis" followed by your question or request to interact with Claude Code
- **Speech Recognition API** - distributed processing architecture:
  - Standalone API server that can run on a separate machine with GPU
  - Efficient client-server communication via REST and WebSocket interfaces
  - Support for multiple Whisper models with automatic selection
- **Conversational AI** with natural speech synthesis:
  - Text-to-speech feedback for AI assistant responses
  - Automatic dictation startup with welcome message
  - Contextual responses from AI assistant
- **Audio processing** with feedback sounds for recording states
- Support for non-standard keyboard layouts during dictation
- Modular, clean architecture for easier maintenance and extension
- Comprehensive, modular test suite organized by component
- Simple, intuitive user experience with just two modes

## Prerequisites

- macOS
- Python 3.8+ installed
- Required Python packages (see requirements.txt)
- Microphone and speakers for audio input/output
- Internet connection for neural voice synthesis (optional)
- [Yabai](https://github.com/koekeishiya/yabai) window manager (optional, for window control commands)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/YOUR_USERNAME/whisper-yabai-mac-os-x.git
   cd whisper-yabai-mac-os-x
   ```

2. Create and activate a virtual environment (recommended):
   ```
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up the Speech Recognition API:
   ```
   # Ensure you have the ffmpeg dependency installed
   # On macOS with Homebrew:
   brew install ffmpeg

   # The API will automatically download the Whisper model on first run
   ```

5. Copy the example environment file and customize as needed:
   ```
   cp .env.example .env
   ```

6. Configure environment variables for the Speech API:
   ```
   # Set environment variables
   export USE_SPEECH_API=true
   export SPEECH_RECOGNITION_API_URL=http://localhost:8080

   # Or use the provided configuration file
   source config/speech_api.env
   ```

## Usage

### Permissions Setup (Important!)

On macOS, you must grant permissions for both microphone access and keyboard monitoring before the daemon will work properly.

1. Run the permissions check utility:
   ```
   python src/permissions_check.py
   ```

2. Follow the prompts to grant the necessary permissions:
   - System Settings > Privacy & Security > Microphone
   - System Settings > Privacy & Security > Accessibility

The script will help guide you through this process and verify if the permissions have been granted correctly.

### Setting Up the Speech Recognition API (Required)

The system now uses a separate Speech Recognition API for transcription:

1. Start the Speech Recognition API server:
   ```bash
   ./scripts/run_speech_api.sh
   ```

   This will start the API server on port 8080 by default. For more options:
   ```bash
   ./scripts/run_speech_api.sh --help
   ```

2. Configure the client to use the API:
   ```bash
   # Set environment variables
   export USE_SPEECH_API=true
   export SPEECH_RECOGNITION_API_URL=http://localhost:8080

   # Or use the provided configuration file
   source config/speech_api.env
   ```

### Running the Voice Control Daemon

1. Start the daemon:
   ```
   python -m src.daemon
   ```

2. The system starts in dictation mode by default - just speak and your words will be converted to text.

3. Say "jarvis" followed by your question or request to interact with the AI assistant.

4. To exit, press Ctrl+C in the terminal or press ESC to exit gracefully.

### Configuring the Speech Synthesis API

The system uses an external API for speech synthesis:

1. Set the API URL and key in your environment:
   ```
   export SPEECH_API_URL="https://api.example.com/synthesize"
   export SPEECH_API_KEY="your_api_key_here"
   ```

2. Test the speech synthesis:
   ```
   python -c "from src.audio.speech_synthesis import speak; speak('Hello, testing speech synthesis')"
   ```

For detailed API configuration instructions, see `docs/NEURAL_VOICE_SETUP.md`

## Voice Interactions

The voice control system now has two main modes:

### Dictation Mode (Default)
- Just speak naturally and your words will be typed at the cursor position
- No trigger word needed - dictation is the default behavior
- Useful for writing emails, messages, documents, etc.

### Code Agent Mode
- Say "jarvis" followed by your question or request
- Interact directly with Claude Code AI assistant
- Get answers to questions, coding help, creative content, etc.
- Example: "Jarvis, what's the weather today?"
- Example: "Jarvis, help me debug this Python code"

### Hotkeys
- `Ctrl+Shift+Space` - Activate dictation mode
- `Ctrl+Shift+D` - Alternative hotkey for dictation mode
- `Ctrl+Shift+M` - Toggle microphone mute
- `ESC` - Stop the daemon

For more details about the Code Agent integration and dictation features, see `docs/COMMANDS_CHEATSHEET.md` and `docs/CODE_AGENT_API.md`.

## Customization

### Code Agent Integration

The system now uses Code Agent integration to process all "jarvis" commands. This provides a more natural way to interact with the assistant:

```
"Jarvis, what's the capital of France?"
"Jarvis, can you help me with my Python code?"
"Jarvis, write a short story about a robot"
```

The response will be spoken aloud using the configured voice synthesis.
### Changing Settings

The application now uses a centralized configuration system with multiple configuration sources:

1. **Environment Variables**: Set in the `.env` file or system environment
2. **Configuration File**: Edit `config.json` in the project root or `~/.config/whisper_voice_control/config.json`
3. **Default Values**: Built-in defaults for all settings

#### Using the Configuration File (Recommended)

Edit `config.json` to customize settings:

```json
{
  "MODEL_SIZE": "large-v3",
  "COMMAND_TRIGGER": "jarvis",
  "DICTATION_TRIGGER": "type",
  "RECORDING_TIMEOUT": 7.0,
  "USE_LLM": true,
  "LOG_LEVEL": "INFO"
}
```

#### Using Environment Variables

Edit the `.env` file to set environment variables:

```
WHISPER_MODEL_SIZE=tiny
COMMAND_TRIGGER=jarvis
DICTATION_TRIGGER=type
RECORDING_TIMEOUT=7.0
USE_LLM=true
LOG_LEVEL=INFO
```

#### Key Configuration Options

- `MODEL_SIZE` - The size of the Whisper model to use (tiny, base, small, medium, large)
- `COMMAND_TRIGGER` - The trigger word for command mode (default: "jarvis")
- `DICTATION_TRIGGER` - The trigger word for explicit dictation mode (default: "type", but not required as dictation is now the default mode)
- `RECORDING_TIMEOUT` - How long to record after trigger detection (in seconds)
- `DICTATION_TIMEOUT` - How long to record for dictation (in seconds)
- `USE_LLM` - Enable or disable LLM-based command interpretation (true/false)
- `LLM_MODEL_PATH` - Path to the local LLM model in GGUF format
- `LOG_LEVEL` - Set logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `VOICE_NAME` - System voice to use for speech synthesis
- `SPEECH_API_URL` - URL for the speech synthesis API
- `SPEECH_API_KEY` - Authentication key for the speech synthesis API

## Running as a Service

To run the daemon as a background service that starts automatically:

1. Create a launchd plist file:
   ```
   cp com.example.whispervoicecontrol.plist ~/Library/LaunchAgents/
   ```

2. Edit the plist file to point to your installation directory

3. Load the service:
   ```
   launchctl load ~/Library/LaunchAgents/com.example.whispervoicecontrol.plist
   ```

## Code Agent API

The system includes a built-in API server that allows external applications to interact with the speech recognition system, providing a way to create cloud-based assistants that leverage the local speech processing capabilities.

### Starting the API Server

To start the daemon with the API server enabled:

```
python src/daemon.py --api --api-port 8000 --api-host 127.0.0.1
```

### API Endpoints

- `GET /status`: Get the current status of the voice control system
- `POST /speak`: Synthesize speech from text
- `POST /code-agent`: Process a code agent request
- `WebSocket /ws/transcription`: Real-time transcription stream

### Using the API Client

A test client is included to demonstrate API usage:

```
# Test API status
python src/api/client.py --status

# Connect to real-time transcription WebSocket
python src/api/client.py --ws

# Test speech synthesis
python src/api/client.py --speak "Hello, world"

# Test code agent integration
python src/api/client.py --prompt "What's the weather like today?"
```

### Integration Example

To integrate with your own application, connect to the WebSocket endpoint to receive transcriptions in real-time, and use the code-agent endpoint to send responses back to the user via speech synthesis.

## Natural Language Commands with LLM

The LLM interpreter enables more fluid command processing beyond simple keyword matching. When enabled, it:

1. Interprets natural language commands using prompt engineering
2. Extracts commands and arguments from complex phrases
3. Provides dynamic response generation for ambiguous commands
4. Falls back to simple command parsing if no match is found

Examples of commands that work with LLM interpretation:
- "Can you please open my Safari browser?"
- "I'd like to focus on the terminal window"
- "Move this window a bit to the left"
- "Make this window take up the full screen"
- "I need to resize this window to make it smaller"

## Code Architecture and Maintainability

The codebase has been restructured for improved maintainability and extensibility:

### System Architecture

The system uses a modular architecture with key components including:

- Audio recording and processing
- Speech recognition using Whisper
- Command and dictation processing
- External text-to-speech API integration
- UI and system integration

For detailed architecture documentation, including sequence diagrams of key processes, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Directory Structure

The project follows a modular directory structure:

```
├── src/                    # Source code
│   ├── core/               # Core infrastructure components
│   ├── audio/              # Audio processing components
│   ├── utils/              # Utility modules
│   ├── ui/                 # User interface components
│   ├── config/             # Configuration management
│   └── tests/              # Test modules and test utilities
├── config/                 # Configuration files
├── docs/                   # Documentation
├── docs-src/               # Source files for generated documentation
├── logs/                   # Log files
│   └── test_logs/          # Test log output
├── scripts/                # Shell scripts
│   ├── docs/               # Documentation generation scripts
│   └── setup/              # Setup scripts
└── models/                 # Model files
```

Each source directory contains a README.md with detailed information about its components and usage.

### Core Architectural Components

- **Centralized Configuration System**: `config/config.py` provides unified configuration management from multiple sources
- **Error Handling Utilities**: `core/error_handler.py` implements consistent error handling patterns
- **Resource Management**: `audio/resource_manager.py` ensures proper cleanup of system resources
- **Centralized Logging**: `core/logging_config.py` establishes consistent logging practices
- **Core Dictation Module**: `core/core_dictation.py` provides shared typing functionality

### Key Design Patterns

- **Singleton Pattern**: Used for config, state manager, and other globally accessible resources
- **Dependency Injection**: Reduces coupling between components
- **Resource Context Managers**: Ensures proper cleanup of system resources
- **Centralized Error Handling**: Standardized approach to error handling
- **Configuration Hierarchy**: Environment variables → Config files → Default values

### Extending the System

The modular architecture makes it easy to extend the system:

1. **Custom Dictation Processing**: Extend `utils/dictation.py` or implement a new processor
2. **New Voice Synthesis Options**: Add to `audio/speech_synthesis.py` module
3. **Enhanced Audio Processing**: Extend `audio/audio_processor.py` with new capabilities
4. **Code Agent Integration**: Extend the API server for more advanced interactions

### Development Guidelines

When contributing to this project:

- Follow the established directory structure and import patterns
- Use the error handling utilities for consistent error reporting
- Let the configuration system manage settings
- Use resource managers to handle system resources
- Implement proper type annotations and docstrings
- Follow the logging conventions
- Write tests for new functionality in the tests directory using the helper utilities in test_utils.py
- Update documentation for new features

### Documentation System

The project includes a comprehensive documentation system:

- **Automated Documentation**: Generated from docstrings in the code
- **Self-Hosted Documentation**: Uses mdBook to create a searchable, static website
- **Documentation Tools**:
  - `scripts/docs/add_docstrings.py`: Adds template docstrings to Python files
  - `scripts/docs/extract_docs.py`: Extracts docstrings and generates markdown
  - `scripts/docs/create_documentation.sh`: End-to-end documentation generation
  - `scripts/docs/build_docs.sh`: Builds and serves documentation with Docker

Additional documentation:
- [ARCHITECTURE.md](docs/ARCHITECTURE.md): Detailed system architecture and diagrams
- [COMMANDS_CHEATSHEET.md](docs/COMMANDS_CHEATSHEET.md): Quick reference for voice commands
- [NEURAL_VOICE_SETUP.md](docs/NEURAL_VOICE_SETUP.md): Guide for setting up text-to-speech
- [CLOUD_CODE_API.md](docs/CLOUD_CODE_API.md): Code Agent API documentation
- [SPEECH_API.md](docs/SPEECH_API.md): Speech Recognition API documentation

To generate the documentation:

```bash
# Generate and build documentation
./scripts/docs/create_documentation.sh

# Serve existing documentation
./scripts/docs/build_docs.sh --serve-only

# Use Docker to build and serve
docker build -t whisper-voice-control-docs -f Dockerfile.docs .
docker run -p 8080:8080 whisper-voice-control-docs
```

The documentation website includes:
- API reference for all modules
- Searchable interface
- Interactive code examples
- Markdown rendering with syntax highlighting
- Responsive design for all devices

## Troubleshooting

- If you encounter permission issues with microphone access, make sure to grant Terminal (or your IDE) microphone permissions in System Preferences > Security & Privacy > Privacy > Microphone.
- If commands related to Yabai aren't working, make sure Yabai is properly installed and running.
- Check the logs for detailed error messages.
- For speech recognition issues, try:
  - Speaking more clearly and directly into the microphone
  - The system now uses the 'large-v3' Whisper model by default for maximum accuracy
  - If you need faster performance with less accuracy, you can switch to smaller models (medium, small, base, or tiny)
  - Checking for background noise that might be confusing the model
  - If possible, use a better microphone or move to a quieter environment
- The voice commands are designed to be natural language, so experiment with different phrasings if a command isn't recognized.
- Pay attention to the sound indicators:
  - High-pitched "Tink" sound: Recording has started - begin speaking
  - Low-pitched "Basso" sound: Recording has stopped - processing speech
  - "Pop" sound: Dictation has been processed and typed
- If dictation isn't typing text properly:
  - Make sure the application has accessibility permissions
  - Try clicking on the text field before dictating
  - For non-standard keyboard layouts, the clipboard-based paste approach should work

### Speech Synthesis Troubleshooting

- If speech synthesis is not working:
  - Check that the API URL and key are correctly set in your environment
  - Verify network connectivity to the API endpoint
  - Check the logs for API error responses
  - Try manually testing the API with a curl request

- API access issues:
  - Verify your API key has not expired
  - Check if there are rate limits on the API
  - Ensure your network allows outbound connections to the API endpoint
  - For detailed setup instructions, see `docs/NEURAL_VOICE_SETUP.md`

- Audio playback issues:
  - Make sure your system's audio output is properly configured
  - Check that audio is not muted
  - Verify appropriate audio playback permissions
  - Test audio playback with a simple system command like `afplay sample.wav`

### LLM Troubleshooting

- If the LLM is not loading properly, check that:
  - You've downloaded a compatible GGUF model
  - The path in `.env` file correctly points to your model
  - You have sufficient RAM for the model size you're using
- If LLM inference is slow, try:
  - Using a smaller, more quantized model (e.g., Q4_K_M instead of Q8_0)
  - Recommended lightweight models: Qwen2-0.5B or DeepSeek-Coder-1.3B
  - Increasing the number of threads in `.env` if you have more CPU cores
  - Enabling GPU acceleration if available
  - Setting `USE_LLM=false` to disable LLM features if performance is critical
- If commands aren't being interpreted correctly:
  - Try different phrasings
  - Check logs to see the LLM's interpretation
  - Try a different model architecture (Qwen, DeepSeek, LLaMA)
  - Adjust model parameters in the `.env` file
  - Check models/README.md for recommended models and configurations

### Speech Recognition API Troubleshooting

- If the Speech Recognition API server fails to start:
  - Check if the port is already in use (`lsof -i :8080`)
  - Verify you have sufficient memory for the model
  - Ensure all dependencies are installed (`pip install -r requirements.txt`)
  - Check logs for specific errors (`./scripts/run_speech_api.sh`)
- If the client can't connect to the API:
  - Verify the API server is running (`curl http://localhost:8080/`)
  - Check network connectivity if running on a separate machine
  - Ensure the `SPEECH_API_URL` environment variable has the correct URL
  - Look for firewall or network issues if running distributed
- If transcription quality is poor:
  - Try using a larger model (`--model large-v3`)
  - Check audio quality and recording settings
  - Verify microphone is working properly
  - Increase the `MIN_CONFIDENCE` threshold
- For better performance:
  - Run the API on a machine with a GPU
  - Use Docker with GPU support (see docker-compose.yml)
  - Adjust model size based on your hardware capabilities
  - For distributed setup, ensure network latency is low

## Testing

The project includes a comprehensive, modular testing framework organized by component:

```bash
# Run all tests
python -m pytest

# Run tests for a specific module
python -m pytest src/tests/audio/

# Run a specific test file
python -m pytest src/tests/audio/test_audio_processor.py

# Run tests in mock mode (without hardware dependencies)
python src/tests/discover_tests.py --mock

# Run tests with CI configuration
python -m pytest -c pytest.ci.ini
```

Tests are organized into subdirectories by component:

- `src/tests/api/`: Tests for API components
- `src/tests/audio/`: Tests for audio processing
- `src/tests/config/`: Tests for configuration
- `src/tests/core/`: Tests for core functionality
- `src/tests/ui/`: Tests for UI components
- `src/tests/utils/`: Tests for utilities
- `src/tests/integration/`: Tests for end-to-end flows

Common test utilities are centralized in the `src/tests/common/` directory to implement DRY principles.

For more information about testing practices, see the [Test Organization Guidelines](docs/CLAUDE.md#test-organization-guidelines) section in CLAUDE.md, which covers:

- Testing the trigger detection for "jarvis" and dictation modes
- Strategies for mocking async API calls
- Running and extending the test suite
- Using shared test utilities and base classes

## License

MIT
