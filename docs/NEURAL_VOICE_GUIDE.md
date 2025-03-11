# Speech Synthesis API Integration Guide

This guide explains how to integrate and use the external speech synthesis API with your application.

## Prerequisites

1. API access credentials (API key)
2. Network connectivity to the API endpoint
3. Basic understanding of HTTP requests

## Setup and Configuration

### Step 1: Set Environment Variables

Configure the speech synthesis module by setting environment variables:

```bash
# Set the speech API URL
export SPEECH_API_URL="https://api.example.com/synthesize"

# Set your API authentication key
export SPEECH_API_KEY="your_api_key_here"
```

For permanent configuration, add these to your shell profile (`.bashrc`, `.zshrc`, etc.).

### Step 2: Test the API Connection

Verify that you can connect to the speech API:

```bash
# Simple curl test
curl -X POST "https://api.example.com/synthesize" \
  -H "Authorization: Bearer your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world","format":"wav","voice":"default"}' \
  --output test.wav

# Play the resulting audio (on macOS)
afplay test.wav
```

### Step 3: Python Integration

The speech synthesis module provides a simple interface for using the API:

```python
# Import the speech module
from src.audio.speech_synthesis import speak, speak_random

# Basic speech synthesis
speak("Hello, this is a test of the speech synthesis API")

# Wait for speech to complete before continuing
speak("This is important information that needs to be heard fully", block=True)

# Use one of the predefined casual responses
speak_random("greeting")  # Picks a random greeting
```

## Using the Speech API

### Basic API Request Format

The API expects POST requests with this JSON format:

```json
{
  "text": "Text to synthesize into speech",
  "format": "wav",
  "voice": "default"
}
```

### API Headers

Always include these headers with your requests:

```
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

### Response Handling

The API returns audio data in the requested format (WAV by default). Your application should:

1. Save the binary response to a temporary file
2. Play the audio using the appropriate system command
3. Clean up the temporary file after playback

The speech synthesis module handles all of this for you automatically.

## Advanced Usage

### Queuing Multiple Speech Requests

The speech synthesis module includes a queue system that ensures speech requests are played in sequence:

```python
# These will play one after another without overlapping
speak("First sentence.")
speak("Second sentence.")
speak("Third sentence.")
```

### Blocking vs. Non-blocking Speech

By default, speech is non-blocking (the function returns immediately while speech plays in the background):

```python
# Non-blocking - continues code execution immediately
speak("This is non-blocking speech")
print("This prints immediately")

# Blocking - waits for speech to complete before continuing
speak("This is blocking speech", block=True)
print("This prints after speech completes")
```

### Casual Responses

For common interaction patterns, use the casual response categories:

```python
# Available categories:
speak_random("greeting")        # Hello there, Hi, etc.
speak_random("acknowledgment")  # Got it, I'm on it, etc.
speak_random("confirmation")    # That's done, All finished, etc.
speak_random("thinking")        # Let me think about that, etc.
speak_random("uncertainty")     # I'm not sure about that, etc.
speak_random("farewell")        # Goodbye for now, etc.
```

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Check network connectivity to the API endpoint
   - Verify your API key is valid and properly formatted
   - Confirm the API URL is correct

2. **Authorization Failures**
   - Ensure your API key has not expired
   - Check that your API key has the correct permissions
   - Verify the Authorization header format (should be `Bearer YOUR_API_KEY`)

3. **Audio Playback Issues**
   - Make sure your system audio is properly configured
   - Verify the appropriate playback command is available (`afplay` on macOS, `aplay` on Linux)
   - Check that the audio format returned by the API is supported by your playback system

### Debug Mode

For more detailed logging, set the log level to DEBUG:

```bash
export LOG_LEVEL=DEBUG
```

This will provide detailed information about API requests, responses, and audio processing.
