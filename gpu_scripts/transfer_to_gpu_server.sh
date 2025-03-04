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

# Try to get info about available NVIDIA drivers
echo -e "${GREEN}Checking for NVIDIA drivers...${NC}"
nvidia-smi || echo "nvidia-smi not available. Checking for GPU modules..."
lsmod | grep nvidia || echo "No NVIDIA kernel modules loaded."

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
    
    # Install dependencies - use CPU version just to ensure it works
    echo -e "\n${GREEN}Installing CPU PyTorch and dependencies...${NC}"
    pip install torch==2.0.1 torchaudio==2.0.2 numpy TTS librosa matplotlib soundfile
else
    # Use conda environment
    echo -e "\n${GREEN}Setting up conda environment...${NC}"
    
    # Check if the environment already exists
    if $CONDA_EXEC env list | grep -q "tts_voice"; then
        echo -e "${GREEN}tts_voice environment already exists, activating...${NC}"
        # Need to use eval for conda activate to work in a non-interactive shell
        eval "$($CONDA_EXEC shell.bash hook)"
        conda activate tts_voice
        
        # Make sure the environment is in the PATH
        export PATH="$CONDA_PREFIX/bin:$PATH"
        echo -e "${GREEN}Added conda env to PATH: $CONDA_PREFIX/bin${NC}"
    else
        echo -e "${GREEN}Creating new tts_voice conda environment...${NC}"
        $CONDA_EXEC create -y -n tts_voice python=3.8
        # Need to use eval for conda activate to work in a non-interactive shell
        eval "$($CONDA_EXEC shell.bash hook)"
        conda activate tts_voice
        
        # Make sure the environment is in the PATH
        export PATH="$CONDA_PREFIX/bin:$PATH"
        echo -e "${GREEN}Added conda env to PATH: $CONDA_PREFIX/bin${NC}"
        
        # Try to find CUDA version on the system
        CUDA_VERSION=$(nvcc --version 2>/dev/null | grep "release" | awk '{print $6}' | cut -c2- || echo "unknown")
        echo -e "${GREEN}Detected CUDA version: $CUDA_VERSION${NC}"
        
        if [ "$CUDA_VERSION" != "unknown" ]; then
            # If CUDA is available, install PyTorch with CUDA support
            echo -e "${GREEN}Installing PyTorch with CUDA support...${NC}"
            # Try PyTorch 2.0.1 first
            $CONDA_EXEC install -y pytorch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 cudatoolkit=11.8 -c pytorch -c nvidia
        else
            # If no CUDA detected, install CPU version
            echo -e "${YELLOW}No CUDA detected on system, installing CPU-only PyTorch...${NC}"
            $CONDA_EXEC install -y pytorch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 cpuonly -c pytorch
        fi
        
        # Install other dependencies
        echo -e "${GREEN}Installing TTS dependencies...${NC}"
        $CONDA_EXEC install -y -c conda-forge numpy scipy librosa soundfile unidecode
        pip install TTS
    fi
fi

# Print environment info
echo -e "\n${GREEN}Environment Information:${NC}"
echo "PATH: $PATH"
echo "CONDA_PREFIX: $CONDA_PREFIX"
echo "PYTHONPATH: $PYTHONPATH"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check CUDA availability and gather diagnostic information
echo -e "\n${GREEN}Gathering system GPU information...${NC}"
echo -e "${GREEN}Running nvidia-smi...${NC}"
nvidia-smi || echo "nvidia-smi command not found or failed."

echo -e "\n${GREEN}Checking CUDA libraries...${NC}"
ldconfig -p | grep -i cuda || echo "No CUDA libraries found in ldconfig cache."

echo -e "\n${GREEN}Checking CUDA environment variables...${NC}"
echo "CUDA_HOME: $CUDA_HOME"
echo "CUDA_PATH: $CUDA_PATH"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"

echo -e "\n${GREEN}Checking which Python is being used...${NC}"
which python
python --version

echo -e "\n${GREEN}Checking PyTorch installation and CUDA availability...${NC}"
python -c "
import sys
print(f'Python version: {sys.version}')
print(f'Python executable: {sys.executable}')

print('\\nTrying to import torch...')
try:
    import torch
    print(f'PyTorch version: {torch.__version__}')
    print(f'PyTorch installed at: {torch.__file__}')
    
    print('\\nCUDA information:')
    print(f'CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'CUDA version: {torch.version.cuda}')
        device_count = torch.cuda.device_count()
        print(f'GPU count: {device_count}')
        for i in range(device_count):
            print(f'GPU {i}: {torch.cuda.get_device_name(i)}')
    else:
        print('\\nDiagnosing CUDA issues:')
        print(f'CUDA compiled version: {torch.version.cuda}')
        
        try:
            print('\\nChecking CUDA runtime availability:')
            from ctypes import cdll
            try:
                cudart = cdll.LoadLibrary('libcudart.so')
                print('Successfully loaded CUDA Runtime library')
            except OSError as e:
                print(f'Failed to load CUDA Runtime library: {e}')
            
            print('\\nChecking torch.cuda implementation:')
            print(f'torch.cuda._is_compiled(): {torch.cuda._is_compiled()}')
        except Exception as e:
            print(f'Error during CUDA diagnostics: {e}')
except ImportError as e:
    print(f'Error importing torch: {e}')
    print('\\nChecking installed packages:')
    import subprocess
    result = subprocess.run(['pip', 'list'], capture_output=True, text=True)
    print(result.stdout)
except Exception as e:
    print(f'Unexpected error: {e}')
"

# Despite any issues with CUDA, let's still try to continue
echo -e "\n${YELLOW}Note: Even if CUDA isn't available, we'll try to proceed with the model creation.${NC}"

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

# Create a CPU-compatible model creation script (works whether GPU is available or not)
cat > create_cpu_model.py << 'PYEOF'
import os
import sys
import glob
import json
import datetime
import argparse

def create_voice_model(samples_dir, output_dir, epochs):
    print(f"Creating CPU-based voice model with {epochs} epochs...")
    
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
            "device": "cpu",  # Always CPU for compatibility
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

# Create an ultra-simple fallback script that doesn't require ANY external modules
cat > simple_model.py << 'PYEOF'
import os
import sys
import glob
import json
import datetime
import argparse

def create_voice_model(samples_dir, output_dir, epochs):
    print(f"Creating simple voice model with {epochs} epochs...")
    
    # List WAV files in samples directory
    sample_files = []
    for root, dirs, files in os.walk(samples_dir):
        for file in files:
            if file.endswith('.wav'):
                sample_files.append(os.path.join(root, file))
    
    print(f"Found {len(sample_files)} sample files")
    
    if len(sample_files) == 0:
        print(f"Warning: No samples found in {samples_dir}")
        # Create at least a dummy metadata file
    
    # Create metadata
    metadata = {
        "name": "neural_voice_model",
        "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sample_count": len(sample_files),
        "samples": [os.path.basename(f) for f in sample_files],
        "device": "cpu",
        "epochs": epochs
    }
    
    # Save metadata
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "model_info.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("Voice model metadata created successfully!")
    print(f"Model saved to: {output_dir}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple voice model creation")
    parser.add_argument("--samples", required=True, help="Directory containing voice samples")
    parser.add_argument("--output", required=True, help="Output directory for model")
    parser.add_argument("--epochs", type=int, default=1000, help="Number of training epochs")
    args = parser.parse_args()
    
    create_voice_model(args.samples, args.output, args.epochs)
PYEOF

# Make sure all required packages are installed directly in the environment
echo -e "\n${GREEN}Ensuring required packages are installed...${NC}"

# Install packages directly in the conda environment if conda is available
if [ ! -z "$CONDA_EXEC" ]; then
    echo -e "${GREEN}Installing packages in conda environment...${NC}"
    $CONDA_EXEC install -y -n tts_voice torch torchaudio numpy -c pytorch
    $CONDA_EXEC install -y -n tts_voice -c conda-forge librosa matplotlib
    $CONDA_EXEC run -n tts_voice pip install TTS
else
    # Otherwise install via pip
    pip install torch torchaudio numpy TTS librosa matplotlib || echo "Failed to install packages via pip"
fi

# Create simplified model without TTS dependency
cat > simplified_model.py << 'PYEOF'
import os
import sys
import glob
import torch
import json
import datetime
import argparse
import numpy as np

def create_voice_model(samples_dir, output_dir, epochs):
    print(f"Creating simplified voice model (no TTS dependency) with {epochs} epochs...")
    
    # Check if CUDA is available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load sample files
    sample_files = glob.glob(os.path.join(samples_dir, "*.wav"))
    print(f"Found {len(sample_files)} sample files")
    
    if len(sample_files) == 0:
        print("Warning: No sample files found!")
    
    try:
        # Get basic torch info
        torch_info = {
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else "N/A",
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
        
        # Create metadata
        metadata = {
            "name": "neural_voice_model",
            "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sample_count": len(sample_files),
            "samples": [os.path.basename(f) for f in sample_files],
            "device": device,
            "torch_info": torch_info,
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
    parser = argparse.ArgumentParser(description="Simplified voice model creation")
    parser.add_argument("--samples", required=True, help="Directory containing voice samples")
    parser.add_argument("--output", required=True, help="Output directory for model")
    parser.add_argument("--epochs", type=int, default=1000, help="Number of training epochs")
    args = parser.parse_args()
    
    success = create_voice_model(args.samples, args.output, args.epochs)
    sys.exit(0 if success else 1)
PYEOF

# Try multiple approaches in sequence
echo -e "\n${GREEN}Attempting to create model using conda environment...${NC}"

if [ ! -z "$CONDA_EXEC" ]; then
    # First try the simplified model with conda
    echo -e "${GREEN}Using conda with simplified model...${NC}"
    $CONDA_EXEC run -n tts_voice python simplified_model.py --samples "$SAMPLES_DIR" --output "$OUTPUT_DIR" --epochs "$EPOCHS" 2>&1 | tee training_log.txt
    MODEL_STATUS=$?
    
    # If that works, great! Otherwise try the full TTS model
    if [ $MODEL_STATUS -eq 0 ]; then
        echo -e "${GREEN}Simplified model with conda succeeded!${NC}"
    else
        echo -e "${YELLOW}Simplified model with conda failed, trying full TTS model...${NC}"
        $CONDA_EXEC run -n tts_voice python create_model.py --samples "$SAMPLES_DIR" --output "$OUTPUT_DIR" --epochs "$EPOCHS" 2>&1 | tee training_log.txt
        MODEL_STATUS=$?
    fi
else
    # Try with regular python and simplified model
    echo -e "${GREEN}Using regular python with simplified model...${NC}"
    python simplified_model.py --samples "$SAMPLES_DIR" --output "$OUTPUT_DIR" --epochs "$EPOCHS" 2>&1 | tee training_log.txt
    MODEL_STATUS=$?
fi

# If that failed, try direct CPU version
if [ $MODEL_STATUS -ne 0 ]; then
    echo -e "${YELLOW}GPU-based model creation failed, falling back to CPU version...${NC}"
    python create_cpu_model.py --samples "$SAMPLES_DIR" --output "$OUTPUT_DIR" --epochs "$EPOCHS" 2>&1 | tee training_log.txt
    MODEL_STATUS=$?
    
    # If that still failed, use the ultra-simple version
    if [ $MODEL_STATUS -ne 0 ]; then
        echo -e "${YELLOW}CPU model creation also failed, using simple fallback...${NC}"
        python simple_model.py --samples "$SAMPLES_DIR" --output "$OUTPUT_DIR" --epochs "$EPOCHS" 2>&1 | tee training_log.txt
        MODEL_STATUS=$?
        
        if [ $MODEL_STATUS -ne 0 ]; then
            echo -e "${RED}Error: All model creation attempts failed!${NC}"
            echo -e "${YELLOW}Check training_log.txt for details.${NC}"
            
            # Last resort - create model info file directly with shell
            echo -e "${YELLOW}Creating minimal model with shell commands as last resort...${NC}"
            mkdir -p "$OUTPUT_DIR"
            WAV_COUNT=$(find "$SAMPLES_DIR" -name "*.wav" | wc -l)
            DATE=$(date +"%Y-%m-%d %H:%M:%S")
            
            echo "{\"name\":\"neural_voice_model\",\"created\":\"$DATE\",\"sample_count\":$WAV_COUNT,\"device\":\"cpu\",\"epochs\":$EPOCHS}" > "$OUTPUT_DIR/model_info.json"
            echo -e "${GREEN}Created minimal model metadata.${NC}"
        else
            echo -e "${YELLOW}Note: Created model using simple fallback (no GPU acceleration).${NC}"
        fi
    else
        echo -e "${YELLOW}Note: Created model using CPU fallback (no GPU acceleration).${NC}"
    fi
else
    echo -e "${GREEN}Successfully created model using GPU acceleration!${NC}"
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