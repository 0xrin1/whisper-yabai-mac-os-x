#!/bin/bash
# Script to create a custom voice model from existing training samples

echo "==== Creating Enhanced Custom Voice Model ===="
echo "This script will create a voice model from your existing voice training samples"
echo "and set it as the active voice for the system."
echo "It will customize the voice parameters to better match your voice characteristics."
echo

# Check if we have training samples
if [ ! -d "training_samples" ] || [ $(find training_samples -name "*.wav" | wc -l) -eq 0 ]; then
    echo "No voice samples found in the training_samples directory."
    echo "Please run the voice training utility first with: python src/voice_training.py"
    exit 1
fi

# Count samples
SAMPLE_COUNT=$(find training_samples -name "*.wav" | wc -l)
echo "Found $SAMPLE_COUNT voice samples to use for model creation."
echo "More samples = better voice matching (recommended: 30+ samples)"

# Create the voice model
echo
echo "Creating voice model..."
# Find all user voice recordings (excluding test samples)
USER_SAMPLES=$(find training_samples -name "sample_*.wav" | tr '\n' ' ')
# Use Python to create the model directly with actual user samples
python -c "
import sys
sys.path.append('.')
from src.voice_training import create_voice_model, install_voice_model
sample_paths = '$USER_SAMPLES'.split()
if sample_paths:
    print(f'Using {len(sample_paths)} user voice recordings')
    model_dir = create_voice_model('user_voice', sample_paths)
    if model_dir:
        install_voice_model('user_voice')
        print('Voice model created and installed successfully')
else:
    print('No user voice samples found. Running standard training script instead.')
    import subprocess
    subprocess.run(['python', 'src/voice_training.py', '--create-voice-model', '--non-interactive'])
"

# Test the new voice
echo
echo "Testing your new voice model..."
python -c "import src.speech_synthesis as speech; speech.reload_voice_model(); speech.speak('Hello, this is your custom voice model speaking. How do I sound?', block=True)"

echo
echo "Your custom voice model has been created and activated."
echo "The system will now use your voice instead of the default robot voice."
echo "To return to the default voice, rename or delete the file: voice_models/active_model.json"