# Neural Voice Setup Guide

This document explains how to set up and use the GPU-accelerated neural voice synthesis system.

> **Current Status**: The neural voice server is configured to run on port 6000 on the GPU server (192.168.191.55). A dedicated CUDA-enabled conda environment (`neural_cuda`) has been created to ensure GPU acceleration works properly.

## System Overview

The neural voice system consists of two main components:

1. **Neural Voice Server** - Runs on a GPU server to handle the neural TTS synthesis
2. **Neural Voice Client** - Runs on the client machine and communicates with the server

```
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Client Machine ├───HTTP/JSON────►  GPU Server     │
│                 │                │                 │
└─────────────────┘                └─────────────────┘
      │                                   │
      │                                   │
      ▼                                   ▼
┌─────────────────┐                ┌─────────────────┐
│ neural_voice    │                │ neural_voice    │
│ _client.py      │                │ _server.py      │
└─────────────────┘                └─────────────────┘
```

## Server Setup

The server requires a CUDA-capable GPU and a conda environment with the necessary dependencies.

### Prerequisites
- NVIDIA GPU with CUDA support
- Miniconda or Anaconda installed
- SSH access to the GPU server

### Environment Setup

There are two ways to set up the server environment:

#### 1. New Dedicated CUDA Environment (Recommended)

We've created a script that sets up a dedicated conda environment with all dependencies properly configured:

```bash
# Create the dedicated CUDA-enabled environment
./scripts/gpu/setup_neural_cuda_env.sh
```

This script:
- Creates a fresh `neural_cuda` conda environment with Python 3.9
- Installs PyTorch with CUDA support using the correct CUDA version
- Installs TTS (Coqui TTS) and all required dependencies
- Configures proper CUDA environment variables
- Creates necessary directories for audio caching
- Creates an activation script that ensures consistent environment setup
- Tests CUDA detection and availability
- Updates the server management script to use the new environment

#### 2. Use the Existing Environment (Legacy)

The server can also use the existing conda environment named `tts_voice` or `voice_model`, but these environments may not have CUDA properly configured:

- PyTorch with CUDA
- TTS (Coqui TTS)
- Flask

### Starting the Server

You can start the server using either:

```bash
# Start using the new dedicated environment script (recommended)
./scripts/gpu/start_neural_server_remote.sh

# Or use the management script (which has been updated to use the new environment)
./scripts/gpu/manage_neural_server.sh start
```

### Server Management

Use the `manage_neural_server.sh` script to manage the server:

```bash
# Check server status
./scripts/gpu/manage_neural_server.sh status

# Start the server
./scripts/gpu/manage_neural_server.sh start

# Stop the server
./scripts/gpu/manage_neural_server.sh stop

# View server logs
./scripts/gpu/manage_neural_server.sh logs

# Test server connection
./scripts/gpu/manage_neural_server.sh test

# Check GPU status
./scripts/gpu/manage_neural_server.sh gpu

# Set up local environment variables
./scripts/gpu/manage_neural_server.sh setup
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
   export NEURAL_SERVER="http://192.168.191.55:6000"
   ```

2. **Using the `setup` command**:
   ```bash
   scripts/gpu/manage_neural_server.sh setup
   ```

3. **In Code**:
   ```python
   from src.audio import neural_voice_client
   neural_voice_client.configure(server="http://192.168.191.55:6000")
   ```

## Troubleshooting

### Testing Connection and CUDA

We've improved the test scripts to provide detailed information. To test if the server is reachable and CUDA is properly detected:

```bash
python test_server.py
```

This will check:
- Basic HTTP connectivity
- Server response with JSON parsing
- CUDA availability status
- GPU device information

### Testing Speech Synthesis

To test if speech synthesis works, use the enhanced test script:

```bash
# Basic test
python test_synthesize.py

# Test with audio playback (macOS only)
python test_synthesize.py --play

# Test with custom text
python test_synthesize.py --text "This is a custom test message"

# Only test the direct API (not the client library)
python test_synthesize.py --direct-only

# Only test the client library
python test_synthesize.py --client-only
```

### Testing Client Library

To test if the neural voice client library is properly connecting:

```bash
python test_client.py
```

### Common Issues

1. **CUDA Not Detected**:
   - Use the new setup script to create a dedicated environment: `./scripts/gpu/setup_neural_cuda_env.sh`
   - Check if CUDA libraries are properly installed on the server
   - Ensure PyTorch is installed with CUDA support
   - Check the environment variables are properly set (CUDA_HOME, LD_LIBRARY_PATH)

2. **Connection Errors**:
   - Ensure the GPU server is running
   - Check if the neural voice server process is active
   - Verify firewall settings allow connections to port 6000
   - Make sure the server is started with `./scripts/gpu/start_neural_server_remote.sh`

3. **Synthesis Fails**:
   - Check server logs with `./scripts/gpu/manage_neural_server.sh logs`
   - Ensure the TTS model is properly loaded on the server
   - Verify the `audio_cache` directory exists on the server

4. **Audio Quality Issues**:
   - Adjust the model parameters in `voice_models/neural_voice/model_info.json`
   - Make sure CUDA is being used (synthesis should be faster)

5. **Missing Directories**:
   - The server might fail if expected directories are missing
   - Create the following directories on the GPU server:
     ```bash
     mkdir -p ~/whisper-yabai-mac-os-x/gpu_scripts/audio_cache
     mkdir -p ~/audio_cache
     ```

6. **Environment Activation Issues**:
   - Use the dedicated activation script: `source ~/neural_cuda_activate.sh` on the GPU server
   - This script properly sets all required environment variables

## Server Maintenance

### Checking GPU Status

To check the GPU status on the server:

```bash
scripts/gpu/manage_neural_server.sh gpu
```

### Updating the Model

To update the neural voice model:

1. Upload new model files to `voice_models/neural_voice` on the server
2. Restart the server:
   ```bash
   scripts/gpu/manage_neural_server.sh restart
   ```

## Development Notes

The server runs on port 6000 and provides the following API endpoints:

- `GET /` - Basic server information
- `GET /info` - Detailed model and server information
- `POST /synthesize` - Text-to-speech synthesis endpoint

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