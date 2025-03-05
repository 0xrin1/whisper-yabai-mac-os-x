# Audio Processing Components

This directory contains modules related to audio recording, processing, speech recognition, and speech synthesis.

## Components

- **audio_recorder.py**: Core audio recording functionality
- **audio_processor.py**: Audio processing and transcription using Whisper
- **continuous_recorder.py**: Continuous audio recording with rolling buffer
- **resource_manager.py**: Audio resource management utilities
- **speech_synthesis.py**: Text-to-speech functionality
- **neural_voice_client.py**: Neural voice synthesis client
- **trigger_detection.py**: Trigger word detection
- **voice_training.py**: Voice training for neural voice models

## Usage

These modules handle all audio-related functionality in the application:

```python
from src.audio.audio_recorder import AudioRecorder
from src.audio.speech_synthesis import speak
from src.audio.continuous_recorder import ContinuousRecorder
```

## Design Principles

- **Resource Management**: Proper handling of audio resources with context managers
- **Asynchronous Processing**: Non-blocking audio processing
- **Fallback Mechanisms**: Multiple fallback options for speech synthesis
- **Modular Architecture**: Clear separation of recording, processing, and synthesis