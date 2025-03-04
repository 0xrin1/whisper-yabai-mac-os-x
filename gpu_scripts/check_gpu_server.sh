#!/bin/bash
# Script to check GPU server connection and status

# Configuration
SERVER_USER="user"
SERVER_HOST="gpu-server.example.com" # Edit this with your GPU server hostname/IP
SERVER_PATH="/home/user/voice-training"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Display banner
echo -e "${BLUE}"
echo "==============================================="
echo "       GPU Server Connection Check"
echo "==============================================="
echo -e "${NC}"

# Request server information if not provided
if [ "$SERVER_HOST" == "gpu-server.example.com" ]; then
    echo -e "${YELLOW}Please provide GPU server information:${NC}"
    read -p "Server hostname or IP: " SERVER_HOST
    read -p "Username: " SERVER_USER
    read -p "Remote directory path (optional): " SERVER_PATH_INPUT
    
    if [ ! -z "$SERVER_PATH_INPUT" ]; then
        SERVER_PATH="$SERVER_PATH_INPUT"
    fi
    
    if [ -z "$SERVER_HOST" ] || [ -z "$SERVER_USER" ]; then
        echo -e "${RED}Error: Server information incomplete.${NC}"
        exit 1
    fi
fi

# Test SSH connection
echo -e "\n${BLUE}Testing SSH connection...${NC}"
ssh -o BatchMode=yes -o ConnectTimeout=5 "$SERVER_USER@$SERVER_HOST" "echo 'Connection successful'" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to connect to $SERVER_USER@$SERVER_HOST${NC}"
    echo -e "${YELLOW}Please check:${NC}"
    echo -e "  1. Server hostname/IP is correct"
    echo -e "  2. SSH key is properly configured"
    echo -e "  3. Server is online and reachable"
    echo -e "  4. Firewall settings allow SSH connections"
    exit 1
else
    echo -e "${GREEN}✓ SSH connection successful!${NC}"
fi

# Check Python and CUDA availability
echo -e "\n${BLUE}Checking Python and CUDA...${NC}"
SSH_OUTPUT=$(ssh "$SERVER_USER@$SERVER_HOST" "
python3 --version 2>&1
command -v nvidia-smi > /dev/null 2>&1 && echo 'NVIDIA_SMI_FOUND' || echo 'NVIDIA_SMI_NOT_FOUND'
command -v nvidia-smi > /dev/null 2>&1 && nvidia-smi 2>&1 || echo 'No GPU information available'
python3 -c 'import torch; print(f\"PyTorch version: {torch.__version__}\"); print(f\"CUDA available: {torch.cuda.is_available()}\"); print(f\"CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}\"); print(f\"GPU count: {torch.cuda.device_count()}\"); [print(f\"GPU {i}: {torch.cuda.get_device_name(i)}\") for i in range(torch.cuda.device_count())]' 2>&1 || echo 'PyTorch not available'
")

echo -e "\n${BLUE}== Server Environment ==${NC}"
echo -e "$SSH_OUTPUT" | grep -i "python" | head -n 1
echo

if [[ "$SSH_OUTPUT" == *"NVIDIA_SMI_FOUND"* ]]; then
    echo -e "${GREEN}✓ NVIDIA GPU tools installed${NC}"
    
    # Extract and format GPU information
    GPU_INFO=$(echo "$SSH_OUTPUT" | awk '/\| NVIDIA-SMI/{flag=1} /\+----/{flag=1} /\|/{flag=1} /No GPU information/{flag=1} flag')
    echo -e "${BLUE}GPU Information:${NC}"
    echo "$GPU_INFO"
else
    echo -e "${RED}✗ NVIDIA GPU tools not found${NC}"
fi

# Check PyTorch and CUDA
if [[ "$SSH_OUTPUT" == *"PyTorch version"* ]]; then
    echo -e "\n${BLUE}PyTorch Information:${NC}"
    echo "$SSH_OUTPUT" | grep -E "PyTorch version|CUDA available|CUDA version|GPU count|GPU [0-9]+"
    
    if [[ "$SSH_OUTPUT" == *"CUDA available: True"* ]]; then
        echo -e "\n${GREEN}✓ Server is ready for neural voice training!${NC}"
        
        # Check for RTX cards
        if [[ "$SSH_OUTPUT" == *"RTX"* ]] || [[ "$SSH_OUTPUT" == *"RTX"* ]]; then
            echo -e "${GREEN}✓ High-performance RTX GPU detected${NC}"
        elif [[ "$SSH_OUTPUT" == *"A100"* ]] || [[ "$SSH_OUTPUT" == *"H100"* ]]; then
            echo -e "${GREEN}✓ Data center GPU detected (excellent performance)${NC}"
        else
            echo -e "${YELLOW}⚠ No RTX GPU detected. Training may be slower.${NC}"
        fi
    else
        echo -e "\n${RED}✗ CUDA is not available. Neural voice training will not work!${NC}"
    fi
else
    echo -e "\n${RED}✗ PyTorch not installed on server${NC}"
    echo -e "${YELLOW}Please install PyTorch with CUDA support on the server${NC}"
fi

# Check disk space for training
echo -e "\n${BLUE}Checking disk space...${NC}"
DISK_SPACE=$(ssh "$SERVER_USER@$SERVER_HOST" "df -h $SERVER_PATH 2>/dev/null || df -h ~ 2>/dev/null || df -h / 2>/dev/null")
echo -e "$DISK_SPACE" | head -1
echo -e "$DISK_SPACE" | grep -v "Filesystem"

# Check TTS library installation 
echo -e "\n${BLUE}Checking TTS library...${NC}"
TTS_CHECK=$(ssh "$SERVER_USER@$SERVER_HOST" "python3 -c 'import TTS; print(f\"Coqui TTS version: {TTS.__version__}\")' 2>&1 || echo 'TTS not installed'")

if [[ "$TTS_CHECK" == *"Coqui TTS version"* ]]; then
    echo -e "${GREEN}✓ $TTS_CHECK${NC}"
else
    echo -e "${YELLOW}⚠ Coqui TTS not installed. Will be installed during training.${NC}"
fi

echo -e "\n${BLUE}===========================================${NC}"
echo -e "${BLUE}Connection check summary:${NC}"

if [[ "$SSH_OUTPUT" == *"CUDA available: True"* ]] && [[ "$SSH_OUTPUT" == *"GPU count: "* ]] && [[ ! "$SSH_OUTPUT" == *"GPU count: 0"* ]]; then
    echo -e "${GREEN}✓ Server is ready for GPU-accelerated neural voice training${NC}"
    echo -e "${GREEN}✓ SSH connection working properly${NC}"
    
    # Recommend next steps
    echo -e "\n${BLUE}Next steps:${NC}"
    echo -e "1. Run 'python src/voice_training.py' to record voice samples"
    echo -e "2. Run './gpu_scripts/transfer_to_gpu_server.sh' to transfer samples and start training"
    echo -e "3. After training completes, run './gpu_scripts/retrieve_from_gpu_server.sh' to get your model"
else
    echo -e "${RED}✗ Server is not fully ready for neural voice training${NC}"
    echo -e "${YELLOW}Please resolve the issues mentioned above before proceeding${NC}"
fi

echo -e "${BLUE}===========================================${NC}"