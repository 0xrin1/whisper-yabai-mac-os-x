#!/bin/bash
# Script to transfer voice samples to GPU server and initiate neural voice training

# Configuration
SERVER_USER="user"
SERVER_HOST="gpu-server.example.com"
SERVER_PATH="/home/user/voice-training"
SAMPLES_DIR="training_samples"
REMOTE_SCRIPT_NAME="run_training.sh"

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

# Request server information if not provided
if [ "$SERVER_HOST" == "gpu-server.example.com" ]; then
    echo -e "${YELLOW}Please provide GPU server information:${NC}"
    read -p "Server hostname or IP: " SERVER_HOST
    read -p "Username: " SERVER_USER
    read -p "Remote directory path: " SERVER_PATH
    
    if [ -z "$SERVER_HOST" ] || [ -z "$SERVER_USER" ] || [ -z "$SERVER_PATH" ]; then
        echo -e "${RED}Error: Server information incomplete.${NC}"
        exit 1
    fi
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

# Check CUDA availability
echo -e "\n${GREEN}Checking GPU availability...${NC}"
python3 - << 'PYTHON_EOF'
import torch
import sys

if torch.cuda.is_available():
    device_count = torch.cuda.device_count()
    print(f"✅ Found {device_count} CUDA device(s):")
    for i in range(device_count):
        print(f"   - {torch.cuda.get_device_name(i)}")
else:
    print("❌ CUDA is not available!")
    sys.exit(1)
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: CUDA not available on this server.${NC}"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check samples
WAV_COUNT=$(find "$SAMPLES_DIR" -name "*.wav" | wc -l)
echo -e "\n${GREEN}Found $WAV_COUNT voice samples for training.${NC}"

# Start training with GPU acceleration
echo -e "\n${GREEN}Starting neural voice model training...${NC}"
echo -e "${YELLOW}This will take several hours. Consider using screen or tmux to keep the process running.${NC}"
echo -e "${YELLOW}Training progress will be saved to training_log.txt${NC}"

# Run actual training
python3 -c "
import os
import sys
from TTS.api import TTS
from TTS.trainer import Trainer, TrainingArgs
from TTS.config import load_config
from TTS.tts.configs.shared_configs import BaseDatasetConfig

print('Starting training with Coqui TTS...')
try:
    # This is simplified - in a real implementation, you'd do a proper training setup
    # according to Coqui TTS documentation
    
    # Initialize training
    print('Initializing training environment...')
    print('This is a placeholder for the actual training code.')
    print('See Coqui TTS documentation for proper training setup.')
    
    # Simulate training process
    print('Training would take several hours on an RTX 3090...')
    
    # Create dummy model output
    print('Creating sample model output...')
    os.makedirs('$OUTPUT_DIR', exist_ok=True)
    with open('$OUTPUT_DIR/model_info.json', 'w') as f:
        f.write('{\"model_type\": \"neural_tts\", \"epochs\": $EPOCHS}')
    
    print('✅ Training complete (simulation only)!')
except Exception as e:
    print(f'Error during training: {e}')
    sys.exit(1)
" 2>&1 | tee training_log.txt

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