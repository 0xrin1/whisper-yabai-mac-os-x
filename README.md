# Whisper Voice Control for macOS with Yabai

![CI Status](https://github.com/0xrin1/whisper-yabai-mac-os-x/actions/workflows/ci.yml/badge.svg)
![Lint Status](https://github.com/0xrin1/whisper-yabai-mac-os-x/actions/workflows/lint.yml/badge.svg)

A voice command daemon that uses OpenAI's Whisper model locally to control your Mac, with Yabai window manager integration, LLM-powered natural language command interpretation, and customized voice synthesis that sounds like you.

## Features

- Voice control for your Mac using a local Whisper model
- Dictation mode for converting speech directly to text at cursor position
- **Enhanced custom voice model** with advanced voice personalization:
  - Voice profile extraction from your recordings
  - Dynamic voice adjustments based on context
  - Intelligent base voice selection tailored to your voice characteristics
  - Customized pitch, rate, and tone based on your speech patterns
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

### Creating an Enhanced Custom Voice Model

The system supports two types of voice models:

#### 1. Parameter-Based Voice Model (Simple)

The system uses an advanced voice model based on your voice characteristics:

1. Record voice samples with the training utility:
   ```
   python src/voice_training.py
   ```
   This records samples and creates a baseline voice profile.

2. Create your personalized voice model:
   ```
   ./create_voice_model.sh
   ```
   This analyzes your voice recordings to extract unique characteristics:
   - Speech patterns and energy levels
   - Voice profile with optimal parameters
   - Context-aware speech adjustments

3. Test your custom voice:
   ```
   python -c "import src.speech_synthesis as speech; speech.test_voices()"
   ```
   This compares your custom voice with standard system voices.

#### 2. GPU-Accelerated Neural Voice Model (Advanced)

For truly lifelike voice that sounds like you:

1. Record voice samples as above (40+ samples recommended for best quality)

2. Configure your GPU server details in `.env` file:
   ```
   GPU_SERVER_HOST=your-gpu-server-ip
   GPU_SERVER_PORT=22
   GPU_SERVER_USER=your-username
   GPU_SERVER_PASSWORD=your-password
   ```

3. Set up neural voice environment on GPU server:
   ```
   ./setup_neural_voice.sh
   ```
   This transfers your samples and sets up the environment on your GPU server

4. Train a high-performance neural model directly on your GPU server:
   ```
   ssh your-username@your-gpu-server-ip
   cd neural_voice_model/code
   python train_neural_voice.py --samples-dir ../samples --output-dir ../models --epochs 5000
   ```
   This creates a maximum-quality Tacotron2 model utilizing the full power of your RTX 3090 GPU

5. Start the neural voice server on your GPU machine:
   ```
   cd neural_voice_model/code
   ./start_neural_server.sh
   ```
   The server will provide high-quality voice synthesis via HTTP API on port 5001

6. On your client machine, configure the neural server address:
   ```
   export NEURAL_SERVER="http://your-gpu-server-ip:5001"
   ```

7. Test your neural voice:
   ```
   python test_neural_voice.py
   ```

The system will automatically use the best available voice, prioritizing the GPU-based neural model when available and falling back to parameter-based voice when the GPU server is offline.

For detailed setup instructions, see `NEURAL_VOICE_GUIDE.md`

## Voice Commands

The daemon responds to the following voice commands:

### Basic Commands
- `open [application]` - Opens an application (e.g., "open Safari")
- `focus [application]` - Focuses on an application window using Yabai
- `type [text]` - Types the specified text
- `move [direction]` - Moves the focused window (left, right, top, bottom)
- `resize [direction]` - Resizes the focused window (left, right, top, bottom)
- `space [number]` - Moves the focused window to the specified space
- `maximize` - Maximizes the focused window
- `close` - Closes the focused window
- `click` - Clicks the mouse at the current position

### Application Commands
- `browser` - Opens Safari
- `chrome` - Opens Google Chrome
- `terminal` - Opens Terminal
- `iterm` - Opens iTerm
- `code` - Opens Visual Studio Code
- `intellij` - Opens IntelliJ IDEA
- `pycharm` - Opens PyCharm
- `android studio` - Opens Android Studio
- `xcode` - Opens Xcode
- `docker` - Opens Docker Desktop
- `postman` - Opens Postman
- `figma` - Opens Figma
- `github` - Opens GitHub in the browser
- `gitlab` - Opens GitLab in the browser
- `slack` - Opens Slack
- `teams` - Opens Microsoft Teams
- `zoom` - Opens Zoom
- And more...

### Keyboard Shortcuts
- `save` - Command+S (Save)
- `undo` - Command+Z (Undo)
- `redo` - Command+Shift+Z (Redo)
- `copy` - Command+C (Copy)
- `paste` - Command+V (Paste)
- `cut` - Command+X (Cut)
- `select all` - Command+A (Select All)
- `find` - Command+F (Find)
- `new file` - Command+N (New File)
- `new tab` - Command+T (New Tab)
- `close tab` - Command+W (Close Tab)
- `reload` - Command+R (Reload)

### Developer Commands
- `build` - Command+B (Build)
- `run` - Command+R (Run)
- `debug` - Command+D (Debug)
- `stop` - Command+. (Stop)
- `test` - Command+U (Run Tests)
- `refactor` - Control+T (Refactor)
- `next error` - F8 (Next Error)
- `previous error` - Shift+F8 (Previous Error)
- `comment` - Command+/ (Comment/Uncomment)

### Window Management
- `split vertical` - Split window vertically using Yabai
- `split horizontal` - Split window horizontally using Yabai
- `flip` - Mirror the current space along the y-axis
- `balance` - Balance window sizes in the current space
- `float` - Toggle floating mode for the current window
- `rotate` - Rotate the current space by 90 degrees

Additional custom commands can be defined in `commands.json`

## Customization

### Adding Custom Commands

You can add custom commands by editing the `commands.json` file. For example:

```json
{
  "custom_commands": {
    "browser": "open -a 'Safari'",
    "terminal": "open -a 'Terminal'",
    "code": "open -a 'Visual Studio Code'"
  }
}
```

### Changing Settings

The application now uses a centralized configuration system with multiple configuration sources:

1. **Environment Variables**: Set in the `.env` file or system environment
2. **Configuration File**: Edit `config.json` in the project root or `~/.config/whisper_voice_control/config.json`
3. **Default Values**: Built-in defaults for all settings

#### Using the Configuration File (Recommended)

Edit `config.json` to customize settings:

```json
{
  "MODEL_SIZE": "tiny",
  "COMMAND_TRIGGER": "hey",
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
COMMAND_TRIGGER=hey
DICTATION_TRIGGER=type
RECORDING_TIMEOUT=7.0
USE_LLM=true
LOG_LEVEL=INFO
```

#### Key Configuration Options

- `MODEL_SIZE` - The size of the Whisper model to use (tiny, base, small, medium, large)
- `COMMAND_TRIGGER` - The trigger word for command mode (default: "hey")
- `DICTATION_TRIGGER` - The trigger word for dictation mode (default: "type")
- `ASSISTANT_TRIGGER` - The trigger phrase for assistant mode (default: "hey jarvis")
- `RECORDING_TIMEOUT` - How long to record after trigger detection (in seconds)
- `DICTATION_TIMEOUT` - How long to record for dictation (in seconds)
- `USE_LLM` - Enable or disable LLM-based command interpretation (true/false)
- `LLM_MODEL_PATH` - Path to the local LLM model in GGUF format
- `LOG_LEVEL` - Set logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `VOICE_NAME` - System voice to use for speech synthesis
- `USE_NEURAL_VOICE` - Enable neural voice if available
- `NEURAL_SERVER` - URL of neural voice server

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

### Core Architectural Components

- **Centralized Configuration System**: `config.py` provides unified configuration management from multiple sources
- **Error Handling Utilities**: `error_handler.py` implements consistent error handling patterns
- **Resource Management**: `resource_manager.py` ensures proper cleanup of system resources
- **Centralized Logging**: `logging_config.py` establishes consistent logging practices
- **Core Dictation Module**: `core_dictation.py` provides shared typing functionality

### Key Design Patterns

- **Singleton Pattern**: Used for config, state manager, and other globally accessible resources
- **Dependency Injection**: Reduces coupling between components
- **Resource Context Managers**: Ensures proper cleanup of system resources
- **Centralized Error Handling**: Standardized approach to error handling
- **Configuration Hierarchy**: Environment variables → Config files → Default values

### Extending the System

The modular architecture makes it easy to extend the system:

1. **Adding New Commands**: Add to `commands.json` or extend command processor
2. **Custom Dictation Processing**: Extend `DictationProcessor` or implement a new processor
3. **New Voice Synthesis Options**: Add to speech synthesis module
4. **Enhanced Audio Processing**: Extend audio processor with new capabilities 

### Development Guidelines

When contributing to this project:

- Follow existing code organization and patterns
- Use the error handling utilities for consistent error reporting
- Let the configuration system manage settings
- Use resource managers to handle system resources
- Implement proper type annotations and docstrings
- Follow the logging conventions
- Write tests for new functionality
- Update documentation for new features

## Troubleshooting

- If you encounter permission issues with microphone access, make sure to grant Terminal (or your IDE) microphone permissions in System Preferences > Security & Privacy > Privacy > Microphone.
- If commands related to Yabai aren't working, make sure Yabai is properly installed and running.
- Check the logs for detailed error messages.
- If you're getting repetitive "little bit of a little bit of" transcriptions, try:
  - Speaking more clearly and directly into the microphone
  - Using the smaller 'tiny' Whisper model by setting `WHISPER_MODEL_SIZE=tiny` in your .env file
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

### Voice Model Troubleshooting

#### Parameter-Based Voice Model Issues

- If the custom voice isn't working properly:
  - Check that `voice_models/active_model.json` exists and points to a valid model
  - Verify the voice profile was created correctly in the metadata.json file
  - Run `python -c "import src.speech_synthesis as speech; speech.test_voices()"` to test voices
  - Try `python src/speech_synthesis.py` to test individual voices

- For better parameter-based voice quality:
  - Record at least 40+ voice samples with diverse speech patterns
  - Include a mix of commands, dictation, and natural speech
  - Record in a quiet environment with a good microphone
  - Use varied intonation for different types of phrases
  - Record some questions, statements, and exclamations

- Fine-tuning your parameter-based voice model:
  - Customize parameters in `speech_synthesis.py` for your specific voice
  - Adjust base voice selection (`Daniel`, `Samantha`, `Alex` work best)
  - Try different pitch modifiers (0.92-0.98 range)
  - Modify rate parameters for more natural speed
  - Create a new model with `./create_voice_model.sh` after making changes

#### Neural Voice Model Issues

- If the neural voice client can't connect to the server:
  - Check that the GPU server is running with `./start_neural_server.sh` on the GPU server
  - Verify the server URL is correct in the `NEURAL_SERVER` environment variable
  - Check that port 5001 is open on the GPU server's firewall
  - Ensure the client can reach the server (try `curl http://your-gpu-server-ip:5001/info`)
  - Verify the GPU server is on the same network or properly port-forwarded

- If the neural voice quality is not good enough:
  - Increase the training epochs to 10000 for extended training
  - Check GPU logs to ensure full GPU utilization during training
  - Provide more voice samples (40+ high-quality samples recommended)
  - Make sure samples include diverse speech patterns and intonations
  - Ensure your GPU has enough VRAM (RTX 3090 with 24GB recommended)
  - Try adjusting the model configuration parameters in `train_neural_voice.py`

- Server performance issues:
  - Use a dedicated GPU for inference (RTX 3090 or better recommended)
  - Check GPU memory usage with `nvidia-smi` while the server is running
  - Increase the server's cache size in `neural_voice_server.py`
  - Use a faster network connection between client and server
  - Consider running the server on the same network as the client to reduce latency
  - Try increasing the batch size for faster inference if your GPU has sufficient memory

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

## License

MIT