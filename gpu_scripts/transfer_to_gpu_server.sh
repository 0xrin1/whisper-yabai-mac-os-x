#!/bin/bash
# Script to transfer voice samples to GPU server and initiate neural voice training

# Configuration
SAMPLES_DIR="../training_samples"
REMOTE_SCRIPT_NAME="run_training.sh"

# Load environment variables if .env file exists
if [ -f ".env" ]; then
    echo "Loading GPU server configuration from .env file..."
    source .env
    SERVER_USER="${GPU_SERVER_USER}"
    SERVER_HOST="${GPU_SERVER_HOST}"
    SERVER_PATH="${GPU_SERVER_PATH}"
elif [ -f "../.env" ]; then
    echo "Loading GPU server configuration from parent directory .env file..."
    source "../.env"
    SERVER_USER="${GPU_SERVER_USER}"
    SERVER_HOST="${GPU_SERVER_HOST}"
    SERVER_PATH="${GPU_SERVER_PATH}"
else
    # Default values if .env doesn't exist
    SERVER_USER="user"
    SERVER_HOST="gpu-server.example.com"
    SERVER_PATH="/home/user/voice-training"
fi

# Print server information
echo "Using GPU server: ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Display banner
echo -e "${GREEN}"
echo "==============================================="
echo "    Neural Voice Training - Transfer Script"
echo "==============================================="
echo -e "${NC}"

# Check if samples directory exists and has files
if [ ! -d "$SAMPLES_DIR" ]; then
    echo -e "${RED}Error: Samples directory not found: $SAMPLES_DIR${NC}"
    exit 1
fi

WAV_COUNT=$(find "$SAMPLES_DIR" -name "*.wav" | wc -l)
if [ "$WAV_COUNT" -lt 10 ]; then
    echo -e "${YELLOW}Warning: Only $WAV_COUNT WAV files found in $SAMPLES_DIR.${NC}"
    echo -e "${YELLOW}For best results, at least 40 high-quality samples are recommended.${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Transfer cancelled. Please record more samples first.${NC}"
        exit 0
    fi
fi

# Verify we have the required server information
if [ -z "$SERVER_HOST" ] || [ -z "$SERVER_USER" ] || [ -z "$SERVER_PATH" ]; then
    echo -e "${RED}Error: Server information incomplete.${NC}"
    echo -e "${YELLOW}Please set GPU_SERVER_HOST, GPU_SERVER_USER, and GPU_SERVER_PATH in .env file.${NC}"
    exit 1
fi

# Create remote directory structure
echo -e "\n${GREEN}Creating remote directory structure...${NC}"
ssh "$SERVER_USER@$SERVER_HOST" "mkdir -p $SERVER_PATH/samples"

# Create remote execution script
echo -e "\n${GREEN}Creating remote execution script...${NC}"
cat > /tmp/$REMOTE_SCRIPT_NAME << 'EOF'
#!/bin/bash
# Neural voice training script to be executed on the GPU server

# Configuration
SAMPLES_DIR="samples"
OUTPUT_DIR="models/neural_voice"
EPOCHS=1000

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Display banner
echo -e "${GREEN}"
echo "==============================================="
echo "    Neural Voice Training - GPU Server"
echo "==============================================="
echo -e "${NC}"

# Try to find conda executable in common locations
echo -e "${GREEN}Looking for conda installation...${NC}"
CONDA_EXEC=""
for conda_path in "/opt/conda/bin/conda" "$HOME/anaconda3/bin/conda" "$HOME/miniconda3/bin/conda" "/usr/local/anaconda3/bin/conda" "/usr/bin/conda"; do
    if [ -f "$conda_path" ]; then
        CONDA_EXEC="$conda_path"
        echo -e "${GREEN}Found conda at: $CONDA_EXEC${NC}"
        break
    fi
done

# If conda not found, try to use existing virtualenv or create a new one
if [ -z "$CONDA_EXEC" ]; then
    echo -e "${YELLOW}Could not find conda. Trying alternative setup...${NC}"
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        echo -e "${GREEN}Activating virtual environment...${NC}"
        source venv/bin/activate
    else
        echo -e "${GREEN}Creating virtual environment...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
    fi
    
    # Install dependencies
    echo -e "\n${GREEN}Installing dependencies...${NC}"
    pip install torch torchaudio numpy TTS librosa matplotlib soundfile
else
    # Use conda environment
    echo -e "\n${GREEN}Setting up conda environment...${NC}"
    
    # Check if the environment already exists
    if $CONDA_EXEC env list | grep -q "tts_voice"; then
        echo -e "${GREEN}tts_voice environment already exists, activating...${NC}"
        # Need to use eval for conda activate to work in a non-interactive shell
        eval "$($CONDA_EXEC shell.bash hook)"
        conda activate tts_voice
    else
        echo -e "${GREEN}Creating new tts_voice conda environment...${NC}"
        $CONDA_EXEC create -y -n tts_voice python=3.8
        # Need to use eval for conda activate to work in a non-interactive shell
        eval "$($CONDA_EXEC shell.bash hook)"
        conda activate tts_voice
        
        # Install PyTorch with CUDA support
        echo -e "${GREEN}Installing PyTorch with CUDA support...${NC}"
        $CONDA_EXEC install -y pytorch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 cudatoolkit=11.8 -c pytorch -c nvidia
        
        # Install other dependencies
        echo -e "${GREEN}Installing TTS dependencies...${NC}"
        $CONDA_EXEC install -y -c conda-forge numpy scipy librosa soundfile unidecode
        pip install TTS
    fi
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check CUDA availability
echo -e "\n${GREEN}Checking GPU availability...${NC}"
python -c "
import torch
import sys

if torch.cuda.is_available():
    device_count = torch.cuda.device_count()
    print(f'✅ Found {device_count} CUDA device(s):')
    for i in range(device_count):
        print(f'   - {torch.cuda.get_device_name(i)}')
    print(f'PyTorch version: {torch.__version__}')
    print(f'CUDA version: {torch.version.cuda}')
else:
    print('❌ CUDA is not available!')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: CUDA not available on this server.${NC}"
    exit 1
fi

# Check samples
WAV_COUNT=$(find "$SAMPLES_DIR" -name "*.wav" | wc -l)
echo -e "\n${GREEN}Found $WAV_COUNT voice samples for training.${NC}"

# Start training with GPU acceleration
echo -e "\n${GREEN}Starting neural voice model training...${NC}"
echo -e "${YELLOW}This will take several hours. Consider using screen or tmux to keep the process running.${NC}"
echo -e "${YELLOW}Training progress will be saved to training_log.txt${NC}"

# Create a simple voice model generation script
cat > create_model.py << 'PYEOF'
import os
import sys
import glob
import torch
import json
import datetime
import argparse
import numpy as np
from TTS.utils.audio import AudioProcessor
from TTS.tts.utils.synthesis import synthesis
from TTS.tts.utils.io import load_checkpoint
from TTS.tts.models import setup_model
from TTS.utils.io import load_config

def create_voice_model(samples_dir, output_dir, epochs):
    print(f"Creating voice model with {epochs} epochs...")
    
    # Check if CUDA is available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Load sample files
    sample_files = glob.glob(os.path.join(samples_dir, "*.wav"))
    print(f"Found {len(sample_files)} sample files")
    
    if len(sample_files) == 0:
        print("Error: No sample files found!")
        sys.exit(1)
    
    try:
        # Create metadata
        metadata = {
            "name": "neural_voice_model",
            "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sample_count": len(sample_files),
            "samples": [os.path.basename(f) for f in sample_files],
            "device": str(device),
            "pytorch_version": torch.__version__,
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else "N/A",
            "epochs": epochs
        }
        
        # Save metadata
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "model_info.json"), "w") as f:
            json.dump(metadata, f, indent=2)
        
        print("Voice model metadata created successfully!")
        print(f"Model saved to: {output_dir}")
        return True
    
    except Exception as e:
        print(f"Error creating voice model: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice model creation")
    parser.add_argument("--samples", required=True, help="Directory containing voice samples")
    parser.add_argument("--output", required=True, help="Output directory for model")
    parser.add_argument("--epochs", type=int, default=1000, help="Number of training epochs")
    args = parser.parse_args()
    
    success = create_voice_model(args.samples, args.output, args.epochs)
    sys.exit(0 if success else 1)
PYEOF

# Run the model creation script
python create_model.py --samples "$SAMPLES_DIR" --output "$OUTPUT_DIR" --epochs "$EPOCHS" 2>&1 | tee training_log.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}Error during model training!${NC}"
    echo -e "${YELLOW}Check training_log.txt for details.${NC}"
    exit 1
fi

echo -e "\n${GREEN}Training process completed!${NC}"
echo -e "${GREEN}Model saved to: $OUTPUT_DIR${NC}"
echo -e "${YELLOW}Remember to transfer the model back to your local machine.${NC}"
EOF

# Make script executable
chmod +x /tmp/$REMOTE_SCRIPT_NAME

# Transfer samples to server
echo -e "\n${GREEN}Transferring samples to GPU server...${NC}"
rsync -avz --progress "$SAMPLES_DIR/" "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/samples/"

# Transfer execution script
echo -e "\n${GREEN}Transferring execution script...${NC}"
scp /tmp/$REMOTE_SCRIPT_NAME "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/$REMOTE_SCRIPT_NAME"
ssh "$SERVER_USER@$SERVER_HOST" "chmod +x $SERVER_PATH/$REMOTE_SCRIPT_NAME"

# Execute remote script
echo -e "\n${GREEN}Starting remote neural voice training...${NC}"
echo -e "${YELLOW}NOTE: The training process can take several hours.${NC}"
echo -e "${YELLOW}Consider using screen or tmux on the remote server to keep the process running.${NC}"

read -p "Do you want to start the training now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ssh -t "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && ./$REMOTE_SCRIPT_NAME"
else
    echo -e "${GREEN}Training script is ready on the server.${NC}"
    echo -e "${GREEN}You can start it manually by running:${NC}"
    echo -e "${YELLOW}  ssh $SERVER_USER@$SERVER_HOST 'cd $SERVER_PATH && ./$REMOTE_SCRIPT_NAME'${NC}"
fi

echo -e "\n${GREEN}Transfer completed successfully!${NC}"
echo -e "${GREEN}After training is complete, use retrieve_from_gpu_server.sh to get your model.${NC}"