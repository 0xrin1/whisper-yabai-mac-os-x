#!/bin/bash
cd ~/neural_voice_model

# Try to find conda executable in common locations
echo "Looking for conda installation..."
CONDA_EXEC=""
for conda_path in "/opt/conda/bin/conda" "$HOME/anaconda3/bin/conda" "$HOME/miniconda3/bin/conda" "/usr/local/anaconda3/bin/conda" "/usr/bin/conda"; do
    if [ -f "$conda_path" ]; then
        CONDA_EXEC="$conda_path"
        echo "Found conda at: $CONDA_EXEC"
        break
    fi
done

if [ -z "$CONDA_EXEC" ]; then
    echo "Could not find conda. Installing miniconda..."
    # Download and install miniconda
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p $HOME/miniconda3
    CONDA_EXEC="$HOME/miniconda3/bin/conda"
    export PATH="$HOME/miniconda3/bin:$PATH"
fi

# Create and activate conda environment
echo "Setting up conda environment..."
# Check if the environment already exists
if $CONDA_EXEC env list | grep -q "tts_voice"; then
    echo "tts_voice environment already exists, updating..."
    # Need to use eval for conda activate to work in a non-interactive shell
    eval "$($CONDA_EXEC shell.bash hook)"
    conda activate tts_voice
else
    echo "Creating new tts_voice conda environment..."
    $CONDA_EXEC create -y -n tts_voice python=3.8
    # Need to use eval for conda activate to work in a non-interactive shell
    eval "$($CONDA_EXEC shell.bash hook)"
    conda activate tts_voice
fi

# Install PyTorch with CUDA support
echo "Installing PyTorch with CUDA support..."
conda install -y pytorch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 cudatoolkit=11.8 -c pytorch -c nvidia

# Install other dependencies
echo "Installing TTS dependencies..."
conda install -y -c conda-forge numpy scipy librosa soundfile unidecode

# Clone Coqui TTS repository for voice cloning
echo "Setting up TTS environment..."
if [ ! -d "code/TTS" ]; then
    git clone https://github.com/coqui-ai/TTS.git code/TTS
    cd code/TTS
    pip install -e .
    cd ../..
else
    cd code/TTS
    git pull
    pip install -e .
    cd ../..
fi

# Download pre-trained voice conversion model
echo "Downloading pre-trained models..."
if [ ! -f "models/tts_models--en--ljspeech--glow-tts.zip" ]; then
    python -c "from TTS.utils.manage import ModelManager; ModelManager().download_model('tts_models/en/ljspeech/glow-tts')"
    python -c "from TTS.utils.manage import ModelManager; ModelManager().download_model('tts_models/en/ljspeech/hifigan_v2')"
fi

# Create a simple voice conversion script
cat > code/voice_conversion.py << 'PYEOF'
import os
import sys
import glob
import torch
import json
import argparse
import datetime
import numpy as np
from TTS.utils.audio import AudioProcessor
from TTS.tts.utils.synthesis import synthesis
from TTS.tts.utils.io import load_checkpoint
from TTS.tts.models import setup_model
from TTS.utils.io import load_config

class VoiceConverter:
    def __init__(self, model_path="tts_models/en/ljspeech/glow-tts"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        
        # Set up paths from the pre-trained model
        self.config_path = os.path.join(model_path, "config/config.json")
        self.model_path = os.path.join(model_path, "checkpoint_130000.pth.tar")
        self.vocoder_path = "tts_models/en/ljspeech/hifigan_v2"
        
        # Load configs
        self.config = load_config(self.config_path)
        self.vocoder_config = load_config(os.path.join(self.vocoder_path, "config/config.json"))
        
        # Load models
        self.model = setup_model(self.config)
        if self.device.type == "cuda":
            self.model.cuda()
        
        # Load checkpoints
        cp = load_checkpoint(self.model_path, self.device)
        self.model.load_state_dict(cp["model"])
        self.model.eval()

        # Set up audio processor
        self.ap = AudioProcessor(**self.config.audio)
        
        # Create speaker embedding
        self.sample_voice_files = []
        self.speaker_embedding = None
        
    def add_voice_sample(self, wav_file):
        """Add a voice sample to use for speaker embedding."""
        self.sample_voice_files.append(wav_file)
        
    def create_speaker_embedding(self):
        """Create a speaker embedding from all added voice samples."""
        if not self.sample_voice_files:
            raise Exception("No voice samples added. Please add samples first.")
            
        # Extract speaker embeddings from all samples and average them
        embeddings = []
        for wav_file in self.sample_voice_files:
            waveform = self.ap.load_wav(wav_file)
            mel = self.ap.melspectrogram(waveform)
            mel = torch.FloatTensor(mel).unsqueeze(0).to(self.device)
            speaker_embedding = self.model.extract_speaker_embedding(mel)
            embeddings.append(speaker_embedding.detach().cpu().numpy())
        
        # Average the embeddings
        self.speaker_embedding = np.mean(np.array(embeddings), axis=0)
        self.speaker_embedding = torch.FloatTensor(self.speaker_embedding).unsqueeze(0).to(self.device)
        
        return self.speaker_embedding
    
    def convert_text_to_speech(self, text, output_path):
        """Convert text to speech using the model and speaker embedding."""
        if self.speaker_embedding is None:
            self.create_speaker_embedding()
        
        # Generate speech
        with torch.no_grad():
            mel, alignment, mel_postnet, postnet_output, stop_tokens, _ = synthesis(
                self.model,
                text,
                self.config,
                use_cuda=self.device.type == "cuda",
                ap=self.ap,
                speaker_id=None,
                speaker_embedding=self.speaker_embedding,
                style_embedding=None,
                truncated=False,
                enable_eos_bos_chars=self.config.enable_eos_bos_chars,
                use_griffin_lim=True,
                do_trim_silence=True
            )
        
        # Save the output
        self.ap.save_wav(postnet_output, output_path)
        return output_path

def create_voice_model(samples_dir, output_dir):
    """Create a voice model from samples and save metadata."""
    # Initialize voice converter
    converter = VoiceConverter()
    
    # Add all samples
    sample_files = glob.glob(os.path.join(samples_dir, "*.wav"))
    for sample_file in sample_files:
        print(f"Adding sample: {sample_file}")
        converter.add_voice_sample(sample_file)
    
    # Create speaker embedding
    print("Creating speaker embedding...")
    speaker_embedding = converter.create_speaker_embedding()
    
    # Save metadata
    metadata = {
        "name": "neural_voice_model",
        "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sample_count": len(sample_files),
        "samples": [os.path.basename(f) for f in sample_files],
        "embedding_shape": speaker_embedding.shape
    }
    
    # Save embedding
    torch.save(speaker_embedding, os.path.join(output_dir, "speaker_embedding.pt"))
    
    # Save metadata
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Test the model
    test_text = "Hello, this is a test of your custom voice model."
    output_path = os.path.join(output_dir, "test_output.wav")
    converter.convert_text_to_speech(test_text, output_path)
    
    return output_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice conversion tools")
    parser.add_argument("--samples", required=True, help="Directory containing voice samples")
    parser.add_argument("--output", required=True, help="Output directory for model")
    args = parser.parse_args()
    
    create_voice_model(args.samples, args.output)
PYEOF

echo "Setup complete!"
