# Neural Voice Synthesis

This document explains the neural voice synthesis feature that creates a high-quality voice model based on your voice recordings.

## Overview

The neural voice feature uses deep learning to create a custom voice model that sounds like you. Unlike the basic voice customization, this approach:

1. Utilizes a 3090 GPU for neural network processing
2. Creates a high-quality voice embedding from your recordings
3. Generates speech that captures your voice characteristics
4. Provides more natural and human-like responses

## Setup

### Prerequisites

- NVIDIA GPU (3090 or similar) on a remote server
- SSH access to the server
- Python 3.8+ on both local and remote machines
- Voice recordings (provided in training_samples directory)

### Configuration

1. Set up the GPU server connection in the `.env` file:
   ```
   GPU_SERVER_HOST=192.168.191.55
   GPU_SERVER_USER=claudecode
   GPU_SERVER_PASSWORD=claudecode
   GPU_SERVER_PORT=22
   USE_GPU_ACCELERATION=true
   VOICE_MODEL_TYPE=neural
   ```

2. Install required tools:
   ```bash
   # Local machine
   pip install python-dotenv sshpass
   ```

3. Run the setup script to set up the neural voice model on the GPU server:
   ```bash
   ./setup_neural_voice.sh
   ```

## Usage

### Testing the Neural Voice

Run the test script to verify that neural voice synthesis is working:
```bash
python test_neural_voice.py
```

This will speak several test phrases using the neural voice model.

### Using in the Voice Control System

The voice control system automatically uses the neural voice when:
1. GPU server is accessible
2. `USE_GPU_ACCELERATION=true` is set in `.env`
3. Neural models have been successfully set up

You don't need to do anything special - the system will automatically use neural voice synthesis for all spoken responses.

## Troubleshooting

### GPU Server Connection Issues

If you can't connect to the GPU server:
1. Check your network connection
2. Verify that the server is running
3. Ensure the credentials in `.env` are correct
4. Try connecting manually with SSH to test access

### Voice Quality Issues

If the voice doesn't sound like you:
1. Make sure you've provided enough high-quality recordings
2. Check that the training completed successfully
3. Verify that the RTX 3090 is being properly utilized

### Fallback Mechanism

If neural voice synthesis fails for any reason, the system will automatically fall back to the basic custom voice. You'll see a message in the logs when this happens.

## Technical Details

The neural voice system uses:
1. **Coqui TTS** - Text-to-speech engine based on deep learning
2. **GlowTTS** - Neural vocoder for high-quality voice synthesis
3. **Speaker Embeddings** - Voice characteristic extraction from recordings
4. **CUDA Acceleration** - GPU-accelerated inference for real-time synthesis

The voice conversion happens on the remote GPU server, and the generated audio is transferred back to your local machine for playback.