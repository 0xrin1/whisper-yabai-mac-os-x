# Whisper Voice Control for macOS with Yabai

![CI Status](https://github.com/0xrin1/whisper-yabai-mac-os-x/actions/workflows/ci.yml/badge.svg)
![Lint Status](https://github.com/0xrin1/whisper-yabai-mac-os-x/actions/workflows/lint.yml/badge.svg)

A voice command daemon that uses OpenAI's Whisper model locally to control your Mac, with Yabai window manager integration, LLM-powered natural language command interpretation, and text-to-speech feedback via external API.

## Features

- Voice control for your Mac using a local Whisper model
- Dictation mode by default - speak naturally to type text at cursor position
- Command mode via "jarvis" trigger word
- Text-to-speech API integration for voice feedback
- Audio feedback with sounds for recording start/stop and completion
- Yabai window manager integration for advanced window management
- Continuous listening mode that automatically processes commands
- LLM-powered natural language command interpretation with multiple model support
- Dynamic response generation for ambiguous commands
- Ability to open applications, type text, manipulate windows, and more
- Extensible command system
- Support for non-standard keyboard layouts during dictation
- Modular, refactored architecture for easier maintenance
- Support for multiple LLM architectures (Qwen, DeepSeek, LLaMA)
- Cloud Code API for integrating speech recognition with external applications
- WebSocket interface for real-time transcriptions
- Standalone Speech Recognition API for distributed processing
- Ability to run speech recognition on a separate machine for better resource allocation

## Prerequisites

- macOS
- [Yabai](https://github.com/koekeishiya/yabai) window manager installed and configured
- Python 3.8+ installed
- Required Python packages (see requirements.txt)
- Local LLM model in GGUF format (for natural language command processing)

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

4. Download a Whisper model (this will happen automatically on first run, but you can pre-download your preferred model size):
   ```
   # Example for downloading the base model
   python -c "import whisper; whisper.load_model('base')"
   ```

5. Download a GGUF model for the LLM interpreter:
   ```
   # Create models directory
   mkdir -p models

   # Download a GGUF model (e.g., Llama 2 7B Chat quantized)
   # You can download from https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/tree/main
   # Example using curl:
   curl -L https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf -o models/llama-2-7b-chat.Q4_K_M.gguf
   ```

6. Copy the example environment file and customize as needed:
   ```
   cp .env.example .env
   ```

   Ensure the LLM model path is correctly set in the .env file:
   ```
   LLM_MODEL_PATH=models/llama-2-7b-chat.Q4_K_M.gguf
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

### Running the Voice Control Daemon

There are two versions of the daemon:

#### Standard Version (Hotkey Activated)

1. Start the daemon:
   ```
   python src/daemon.py
   ```

2. Press the activation hotkey (default: Ctrl+Shift+Space) and speak a command.

3. To exit, press Ctrl+C in the terminal.

#### Simplified Version (Hotkey Activated)

1. Start the simplified daemon:
   ```
   python src/simplified_daemon.py
   ```

2. Use the following hotkeys:
   - **Command Mode**: Press Ctrl+Shift+Space to start recording, then speak a command to be executed
   - **Dictation Mode**: Press Ctrl+Shift+D to start recording, then speak text to be typed at the current cursor position

3. To exit, press Ctrl+C in the terminal or press ESC to exit gracefully.

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

### Cloud Code Mode
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

For more details about the Cloud Code integration and dictation features, see `docs/COMMANDS_CHEATSHEET.md` and `docs/CLOUD_CODE_API.md`.

## Customization

### Cloud Code Integration

The system now uses Cloud Code integration to process all "jarvis" commands. This provides a more natural way to interact with the assistant:

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

## Cloud Code API

The system includes a built-in API server that allows external applications to interact with the speech recognition system, providing a way to create cloud-based assistants that leverage the local speech processing capabilities.

### Starting the API Server

To start the daemon with the API server enabled:

```
python src/daemon.py --api --api-port 8000 --api-host 127.0.0.1
```

### API Endpoints

- `GET /status`: Get the current status of the voice control system
- `POST /speak`: Synthesize speech from text
- `POST /cloud-code`: Process a cloud code request
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

# Test cloud code integration
python src/api/client.py --prompt "What's the weather like today?"
```

### Integration Example

To integrate with your own application, connect to the WebSocket endpoint to receive transcriptions in real-time, and use the cloud-code endpoint to send responses back to the user via speech synthesis.

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

1. **Adding New Commands**: Add to `commands.json` or extend command processor
2. **Custom Dictation Processing**: Extend `utils/dictation.py` or implement a new processor
3. **New Voice Synthesis Options**: Add to `audio/speech_synthesis.py` module
4. **Enhanced Audio Processing**: Extend `audio/audio_processor.py` with new capabilities

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
- [CLOUD_CODE_API.md](docs/CLOUD_CODE_API.md): Cloud Code API documentation
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

The project includes a robust testing framework for ensuring functionality works correctly:

```bash
# Run all tests
python -m pytest src/tests/

# Run specific test file
python -m pytest src/tests/test_audio_processor.py

# Run with more detailed output
python -m pytest -v src/tests/
```

For more detailed information about the testing framework, see [TESTING.md](docs/TESTING.md), which covers:

- Comprehensive testing of the Speech Recognition API
- Testing audio processing with the API-only approach
- Testing the trigger detection for "jarvis" and dictation modes
- Strategies for mocking async API calls
- Running and extending the test suite

## License

MIT
