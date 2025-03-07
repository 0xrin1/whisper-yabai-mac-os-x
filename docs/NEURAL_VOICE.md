# Speech Synthesis API Documentation

## Overview

The speech synthesis system has been migrated to an external API-based approach that provides high-quality text-to-speech capabilities without requiring local GPU resources. This system is designed to be simple to configure and maintain, with fallback options in case of API unavailability.

## System Architecture

The speech synthesis system consists of the following components:

1. **Speech Synthesis Module**: A lightweight client that calls the external API
   - Sends text to the API for synthesis
   - Handles response caching to improve performance
   - Manages speech queuing for sequential playback

2. **External API**: Third-party service that handles text-to-speech conversion
   - Processes synthesis requests via HTTP
   - Returns audio data in WAV format
   - Provides high-quality voice synthesis

## Integration

The speech synthesis module is designed to integrate smoothly with the voice control system:

1. **Configuration**:
   - Set API URL via `SPEECH_API_URL` environment variable
   - Set API key via `SPEECH_API_KEY` environment variable

2. **Usage in Code**:
   ```python
   # Basic usage
   from src.audio.speech_synthesis import speak
   speak("Hello, this is a test message")
   
   # Blocking until speech completes
   speak("This is important information", block=True)
   
   # Using predefined responses
   from src.audio.speech_synthesis import speak_random
   speak_random("greeting")  # Selects a random greeting
   ```

## API Request Format

The API expects requests in the following format:

```json
{
  "text": "Text to synthesize",
  "format": "wav",
  "voice": "default"
}
```

Headers:
- `Authorization: Bearer YOUR_API_KEY`
- `Content-Type: application/json`

## Performance Considerations

- **Network Requirements**:
  - Reliable internet connection
  - Low-latency API service
  - Adequate bandwidth for audio streaming

- **Caching**:
  - Frequently used phrases are cached locally
  - Improves response time for common interactions
  - Reduces API calls and potential costs

## Troubleshooting

- **API Connection Issues**:
  - Verify internet connectivity
  - Check API credentials
  - Confirm API service is operational
  - Test with curl to isolate issues:
    ```
    curl -X POST "https://api.example.com/synthesize" \
      -H "Authorization: Bearer YOUR_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"text":"Hello world","format":"wav","voice":"default"}'
    ```

- **Audio Playback Issues**:
  - Ensure system audio is properly configured
  - Verify permissions for audio playback
  - Check for missing dependencies (e.g., audio libraries)
  - Test with system commands like `afplay` or `aplay`

## Future Enhancements

- Support for multiple voice options
- Emotion-based voice styling
- Streaming audio for lower latency
- Pre-caching of common phrases
- Language detection and multilingual support