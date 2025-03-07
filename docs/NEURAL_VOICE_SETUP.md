# Neural Voice Setup Guide

This document explains how to use the neural voice synthesis system.

> **Current Status**: The neural voice client is designed to connect to a neural voice server running on port 6000.

## System Overview

The neural voice system consists of two main components:

1. **Neural Voice Server** - A server running TTS neural synthesis
2. **Neural Voice Client** - Runs on the client machine and communicates with the server

```
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Client Machine ├───HTTP/JSON────►  Neural Voice   │
│                 │                │  Server         │
└─────────────────┘                └─────────────────┘
      │                                   │
      │                                   │
      ▼                                   ▼
┌─────────────────┐                ┌─────────────────┐
│ neural_voice    │                │ neural_voice    │
│ _client.py      │                │ _server.py      │
└─────────────────┘                └─────────────────┘
```

## Client Configuration

The client needs to know the address of the neural voice server.

### Setting the Server URL

The client will try to connect to the server in this order:
1. Use the `NEURAL_SERVER` environment variable if set
2. Fall back to the default value in the code: `http://192.168.191.55:6000`

### Configuration Methods

Set the server URL using one of these methods:

1. **Environment Variable**:
   ```bash
   export NEURAL_SERVER="http://your-server-address:6000"
   ```

2. **In Code**:
   ```python
   from src.audio import neural_voice_client
   neural_voice_client.configure(server="http://your-server-address:6000")
   ```

## Troubleshooting

### Testing Connection

To test if the server is reachable and working properly:

```bash
python scripts/neural_voice/test_neural_voice.py --server "http://your-server-address:6000"
```

This will check:
- Basic HTTP connectivity
- Server response with JSON parsing
- TTS availability

### Testing Speech Synthesis

To test if speech synthesis works:

```bash
# Test with custom text
python scripts/neural_voice/test_neural_voice.py --say "This is a test message" --server "http://your-server-address:6000"

# Only test server connection
python scripts/neural_voice/test_neural_voice.py --server-only --server "http://your-server-address:6000"

# Only test direct API synthesis
python scripts/neural_voice/test_neural_voice.py --api-only --server "http://your-server-address:6000"

# Only test client library
python scripts/neural_voice/test_neural_voice.py --client-only --server "http://your-server-address:6000"
```

### Common Issues

1. **Connection Errors**:
   - Ensure the neural voice server is running
   - Check if the neural voice server process is active
   - If port 6000 is occupied by another process:
     ```bash
     # Find the process using port 6000
     lsof -i :6000
     
     # Kill the process
     kill -9 <PID>
     ```
   - NEVER change the server port. Always keep port 6000 for consistent connectivity

2. **Synthesis Fails**:
   - Check that the TTS model is properly loaded on the server
   - Verify the `audio_cache` directory exists on the server

3. **Audio Quality Issues**:
   - Check the model parameters in `voice_models/neural_voice/model_info.json`

4. **Missing Directories**:
   - The server might fail if expected directories are missing
   - Make sure the audio cache directories exist:
     ```bash
     mkdir -p ~/audio_cache
     ```

## Development Notes

The server runs on port 6000 and provides the following API endpoints:

- `GET /` - Basic server information
- `GET /info` - Detailed model and server information
- `POST /synthesize` - Text-to-speech synthesis endpoint

**Important Port Configuration**:
- The neural voice server MUST run on port 6000
- NEVER modify the port in the server code
- If port 6000 is already in use, find and terminate the process using it
- Changing the port would require updating all clients and documentation

Example API call:
```python
import requests

response = requests.post(
    "http://192.168.191.55:6000/synthesize",
    json={"text": "Hello world"},
    timeout=10
)

# Save audio to file
with open("output.wav", "wb") as f:
    f.write(response.content)
```