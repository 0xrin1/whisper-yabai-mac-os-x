# Neural Voice Model Training Guide

This guide explains how to create a high-quality neural voice model that sounds like you.

## Overview

The system now supports two types of voice models:

1. **Enhanced custom voice** (macOS-based): Uses macOS built-in voices with your custom parameters
2. **Neural voice model** (GPU-accelerated): Uses Coqui TTS for true neural voice synthesis

## Recording Voice Samples

For best results, follow these steps to record high-quality voice samples:

1. Run the voice training utility:
   ```
   python src/voice_training.py
   ```

2. Follow the prompts to record various types of samples:
   - Trigger words ("hey" with different intonations)
   - Dictation commands ("type", "dictate", etc.)
   - Regular commands ("open browser", "maximize window", etc.)
   - Questions (with natural rising intonation)
   - Exclamations (with more energy/emphasis)
   - Natural speech (longer conversational samples)

3. Record in a quiet environment with minimal background noise
4. Maintain consistent distance from the microphone
5. Speak naturally with your normal voice
6. For best results, record at least 40 samples across all categories

## Training Options

### Option 1: Enhanced Custom Voice (Local)

This method uses macOS built-in voices with customized parameters based on your voice:

1. Record samples with the voice training utility
2. Let the system analyze your voice and create a profile
3. The system selects the best base voice and adjusts parameters
4. The result is available immediately without GPU training
5. Test with:
   ```
   python -c "import src.speech_synthesis as speech; speech.speak('This is my enhanced custom voice speaking')"
   ```

### Option 2: Neural Voice Model (GPU-Accelerated)

For true neural voice synthesis (sounds much more like you):

1. Record high-quality samples (at least 40 recommended)
2. Check your connection to a GPU server:
   ```
   ./gpu_scripts/check_gpu_server.sh
   ```
3. Transfer your samples to the GPU server and start training:
   ```
   ./gpu_scripts/transfer_to_gpu_server.sh
   ```
4. Wait for training to complete (several hours)
5. Retrieve the trained model:
   ```
   ./gpu_scripts/retrieve_from_gpu_server.sh
   ```
6. Test your neural voice:
   ```
   python -c "import src.speech_synthesis as speech; speech.speak('This is my neural voice model speaking')"
   ```

## Training Requirements

For neural voice training:
- NVIDIA GPU, RTX 3090 recommended (or similar high-end GPU)
- CUDA installed and properly configured
- At least 12GB VRAM
- 50GB+ free disk space
- SSH access to the GPU server

## Troubleshooting

- If the neural voice doesn't sound like you:
  - Record more samples (40+ recommended)
  - Include more varied speech patterns
  - Make sure samples are clear and high-quality
  - Adjust training epochs (default: 1000)

- If you encounter GPU errors:
  - Verify CUDA is properly installed
  - Check GPU memory is sufficient
  - Reduce batch size in training parameters

- If the enhanced custom voice doesn't sound good:
  - Try different base voices in speech_synthesis.py
  - Adjust pitch_modifier values (0.92-0.98 range)
  - Record more samples with more variation

## Performance Comparison

| Feature | Enhanced Custom Voice | Neural Voice Model |
|---------|----------------------|-------------------|
| Training time | Seconds | Hours |
| Quality | Good | Excellent |
| Hardware | Local Mac | GPU Server |
| Similarity | Medium | High |
| Resource usage | Low | High |
| Setup difficulty | Easy | Complex |

Choose the option that best suits your needs and available resources.