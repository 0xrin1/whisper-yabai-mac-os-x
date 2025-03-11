# Speech Synthesis API Guide

This document explains how to use the external speech synthesis API.

## System Overview

The speech synthesis system now uses an external API for text-to-speech generation:

```
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Application    ├───HTTP/JSON────►  External TTS   │
│                 │                │  API Server     │
└─────────────────┘                └─────────────────┘
```

For detailed system architecture and sequence diagrams showing how the TTS integration works, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Configuration

The speech synthesis module is configured using environment variables:

### Required Environment Variables

1. `SPEECH_API_URL` - The URL of the speech synthesis API
2. `SPEECH_API_KEY` - API key for authentication

### Setting Environment Variables

```bash
# Set the API URL
export SPEECH_API_URL="https://api.example.com/synthesize"

# Set the API key
export SPEECH_API_KEY="your_api_key_here"
```

You can add these to your shell profile (`.bashrc`, `.zshrc`, etc.) or set them before launching the application.

## API Integration

The speech synthesis module sends requests to the external API with the following structure:

```json
{
  "text": "Text to be spoken",
  "format": "wav",
  "voice": "default"
}
```

The API is expected to return audio data in the specified format (WAV).

## Troubleshooting

### Common Issues

1. **API Connection Errors**:
   - Verify the API URL is correct
   - Check your internet connection
   - Confirm the API service is operational

2. **Authentication Errors**:
   - Verify your API key is correct and active
   - Check that the key has the necessary permissions

3. **Audio Playback Issues**:
   - Ensure your system has audio capabilities properly configured
   - Verify that the application has permission to play audio

## Development Notes

To use the speech synthesis module in your code:

```python
from src.audio.speech_synthesis import speak, speak_random

# Simple speech
speak("Hello world")

# Use a random response from a category
speak_random("greeting")

# Block until speech is complete
speak("This is important information", block=True)
```

The module handles queuing of speech requests and ensures they play in sequence without overlapping.
