# Custom Voice Models

This directory contains custom voice models created from your voice samples. 
These models allow the system to respond using a voice that sounds more like you,
rather than using the default robotic system voices.

## How It Works

1. Voice samples are recorded using the voice training utility (`src/voice_training.py`)
2. These samples are used to create a voice model that captures your voice characteristics
3. The speech synthesis system uses this model to make responses sound more natural

## Creating a Custom Voice Model

You can create a custom voice model in two ways:

1. **Automatic method**: Run `./create_voice_model.sh` which will create a model from 
   your existing voice samples and set it as the active voice.

2. **Interactive method**: Run `python src/voice_training.py` and follow the prompts
   to record voice samples and create a model.

## Model Structure

Each voice model is stored in a subdirectory with:

- `metadata.json`: Information about the model (creation date, sample count, etc.)
- `samples/`: Directory containing the original voice samples used
- `temp/`: Temporary directory for voice synthesis operations

## Active Voice Model

The active voice model is specified in `active_model.json` in this directory.
To disable custom voice and return to the system voices, you can simply delete
or rename this file.

## Voice Quality

The quality of your custom voice depends on:

1. The number of voice samples collected
2. The clarity and consistency of your recordings
3. The variety of speech patterns in your samples

For best results, collect at least 30 samples with a good microphone in a quiet room.