# Audio Processing Components

This directory contains modules related to audio recording, processing, speech recognition, and speech synthesis.

## Core Components

### `audio_recorder.py`

The `AudioRecorder` class is responsible for recording audio from the microphone with smart silence detection.

**Key Features:**
- Records audio for configurable durations
- Detects silence to automatically end recordings
- Supports different recording modes (command, dictation, trigger detection)
- Handles microphone access and permissions gracefully
- Uses adaptive thresholds for different recording contexts
- Provides clear error messages and fallbacks for hardware issues
- Manages temporary file creation and cleanup

**Usage Example:**
```python
from src.audio.audio_recorder import AudioRecorder

recorder = AudioRecorder()
# Record audio for dictation (typing what the user says)
wav_file = recorder.start_recording(duration=10, dictation_mode=True)
# Record a short clip for trigger word detection
trigger_wav = recorder.start_recording(duration=2, trigger_mode=True)
```

### `audio_processor.py`

The `AudioProcessor` class processes recorded audio files and transcribes them using Whisper.

**Key Features:**
- Manages a queue of audio files for processing
- Transcribes speech to text using OpenAI's Whisper model
- Handles command parsing and execution
- Supports dictation mode to type transcribed text
- Integrates with LLM-based command interpretation
- Implements robust error handling and model recovery
- Processes audio files asynchronously in a worker thread

**Usage Example:**
```python
from src.audio.audio_processor import processor

# Start the processor in the background
processor.start()

# Manually process a specific file
processor.load_model()  # Ensure model is loaded
result = processor.whisper_model.transcribe("path/to/audio.wav")
transcription = result["text"]
```

### `continuous_recorder.py`

The `ContinuousRecorder` class implements always-on listening with a rolling buffer.

**Key Features:**
- Maintains a continuous audio buffer for trigger word detection
- Processes the buffer periodically to detect trigger words
- Uses efficient memory management and audio chunking
- Provides mute/unmute functionality for privacy
- Implements smart power management to reduce CPU usage
- Handles microphone disconnection and reconnection

**Usage Example:**
```python
from src.audio.continuous_recorder import ContinuousRecorder

recorder = ContinuousRecorder()
recorder.start()  # Start continuous listening
# ... system runs and listens for trigger words ...
recorder.stop()   # Stop listening
```

## Speech Synthesis

### `speech_synthesis.py`

Handles text-to-speech functionality using an external API.

**Key Features:**
- Integration with external TTS API for high-quality speech
- Speech queuing system to prevent overlapping speech
- Automatic caching of frequently spoken phrases
- Support for both blocking and non-blocking speech
- Predefined casual responses for common interactions
- Robust error handling and fallback options

**Usage Example:**
```python
from src.audio.speech_synthesis import speak, speak_random

# Basic speech synthesis
speak("Hello, how can I help you?")

# Use blocking speech for important messages
speak("This is an important message", block=True)

# Use random responses from categories
speak_random("greeting")    # Selects random greeting
speak_random("confirmation") # Selects random confirmation
```

## Utility Components

### `trigger_detection.py`

Implements detection of trigger words in audio streams.

**Key Features:**
- Detects multiple trigger phrases ("hey", "type", "hey jarvis")
- Uses lightweight detection for constant monitoring
- Configurable sensitivity and thresholds
- Manages different actions based on detected triggers
- Implements smart filtering to reduce false positives
- Handles different languages and accents

**Usage Example:**
```python
from src.audio.trigger_detection import TriggerDetector

detector = TriggerDetector()
detector.start()  # Start listening for trigger words
# System continues running, responding to trigger words
detector.stop()   # Stop detection
```

### `resource_manager.py`

Manages system resource allocation and cleanup for audio components.

**Key Features:**
- Centralizes resource management to prevent leaks
- Handles audio device initialization and cleanup
- Provides sound playback functionality
- Implements caching for system sounds and resources
- Ensures proper shutdown of audio subsystems
- Monitors resource usage for optimal performance

**Usage Example:**
```python
from src.audio.resource_manager import play_system_sound, cleanup_resources

# Play a system sound
play_system_sound("Glass")

# Ensure resources are properly released at shutdown
cleanup_resources()
```

### `voice_training.py`

Tools for training and customizing voice models.

**Key Features:**
- Records voice samples for model training
- Extracts voice characteristics for personalization
- Analyzes pitch, rhythm, and tonal qualities
- Creates parameter profiles for system voices
- Prepares data for neural voice model training
- Validates and tests voice models

**Usage Example:**
```python
from src.audio.voice_training import VoiceTrainer

trainer = VoiceTrainer()
# Record voice samples
trainer.record_samples(num_samples=10)
# Create a voice profile
trainer.create_voice_profile()
# Test the created voice
trainer.test_voice()
```

## Error Handling

All audio components implement comprehensive error handling to ensure robustness:

1. **Hardware Failures**: Graceful handling of microphone disconnection or malfunction
2. **Permission Issues**: Clear messaging for microphone access problems
3. **Resource Limitations**: Proper management of memory and file handles
4. **Recovery Strategies**: Multiple fallback approaches for each critical operation
5. **User Feedback**: Informative notifications for issues requiring user action

## Testing

The audio components include mockable interfaces for testing without actual audio hardware:

```python
# Example of testing with mocked audio
from unittest.mock import patch
with patch('src.audio.audio_recorder.AudioRecorder.start_recording') as mock_record:
    mock_record.return_value = '/path/to/test/audio.wav'
    # Test functionality that depends on recording
```

## Design Principles

- **Resource Management**: Proper handling of audio resources with context managers
- **Asynchronous Processing**: Non-blocking audio processing
- **Fallback Mechanisms**: Multiple fallback options for speech synthesis
- **Modular Architecture**: Clear separation of recording, processing, and synthesis
- **Error Resilience**: Comprehensive error handling and recovery
- **User Experience**: Clear feedback and notifications for audio events