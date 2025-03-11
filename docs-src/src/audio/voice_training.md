# voice_training

Voice training utility for whisper-yabai-mac-os-x.
This script records samples of your voice saying trigger words and commands,
then uses them to help optimize recognition settings and create custom voice models.

Source: `audio/voice_training.py`

## Function: `ensure_directories()`

Make sure the necessary directories exist.

## Function: `record_sample(seconds: float = 3.0, prompt: str = None, interactive: bool = True)`

Record an audio sample of specified length.

    Args:
        seconds: Length of recording in seconds
        prompt: Optional text to display before recording
        interactive: Whether to wait for user input before recording

    Returns:
        Path to the recorded WAV file

## Function: `create_voice_model(name: str = DEFAULT_VOICE_MODEL, samples: List[str] = None)`

Create a custom voice model using existing voice samples.

    Args:
        name: Name for the voice model
        samples: List of WAV file paths with voice samples (if None, uses all training samples)

    Returns:
        Path to the created voice model directory

## Function: `install_voice_model(name: str = DEFAULT_VOICE_MODEL)`

Install a custom voice model to be used by the system.

    Args:
        name: Name of the voice model to install

    Returns:
        Boolean indicating success

## Function: `create_backup_zip(samples_dir: str = TRAINING_DIR)`

Create a backup zip file of all recorded samples.

    Args:
        samples_dir: Directory containing samples to backup

    Returns:
        Path to the created zip file

## Function: `main()`

Main function for voice training.
