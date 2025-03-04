#!/bin/bash
# Script to start the neural voice server on the GPU machine

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Display banner
echo -e "${BLUE}"
echo "==============================================="
echo "    Neural Voice Server - GPU Accelerated"
echo "==============================================="
echo -e "${NC}"

# Configuration
MODEL_DIR="voice_models/neural_voice"
PORT=5001
HOST="0.0.0.0"  # Listen on all interfaces

# Load environment variables if .env file exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    source .env
    
    # Override defaults if set in .env
    [ ! -z "$NEURAL_MODEL_DIR" ] && MODEL_DIR="$NEURAL_MODEL_DIR"
    [ ! -z "$NEURAL_SERVER_PORT" ] && PORT="$NEURAL_SERVER_PORT"
    [ ! -z "$NEURAL_SERVER_HOST" ] && HOST="$NEURAL_SERVER_HOST"
fi

# Create audio cache directory
mkdir -p audio_cache

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

# Check if required Python packages are installed
echo -e "${GREEN}Checking for required Python packages...${NC}"
PACKAGES=("flask" "torch" "numpy" "TTS")
MISSING_PACKAGES=()

for pkg in "${PACKAGES[@]}"; do
    if ! python3 -c "import $pkg" &> /dev/null; then
        MISSING_PACKAGES+=("$pkg")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}Missing packages: ${MISSING_PACKAGES[*]}${NC}"
    echo -e "${YELLOW}Installing missing packages...${NC}"
    
    for pkg in "${MISSING_PACKAGES[@]}"; do
        echo -e "${GREEN}Installing $pkg...${NC}"
        
        case "$pkg" in
            "flask")
                pip install flask
                ;;
            "torch")
                # Install PyTorch with CUDA support if available
                if command -v nvcc &> /dev/null; then
                    echo -e "${GREEN}CUDA found, installing PyTorch with CUDA support${NC}"
                    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
                else
                    echo -e "${YELLOW}CUDA not found, installing CPU-only PyTorch${NC}"
                    pip install torch torchvision torchaudio
                fi
                ;;
            "TTS")
                pip install TTS
                ;;
            *)
                pip install "$pkg"
                ;;
        esac
    done
fi

# Check if the model directory exists
if [ ! -d "$MODEL_DIR" ]; then
    echo -e "${YELLOW}Model directory $MODEL_DIR does not exist, creating it...${NC}"
    mkdir -p "$MODEL_DIR"
    
    # Check if we have model_info.json file
    if [ ! -f "$MODEL_DIR/model_info.json" ]; then
        echo -e "${YELLOW}No model information found. Creating a default one...${NC}"
        cat > "$MODEL_DIR/model_info.json" << EOF
{
  "name": "neural_voice_model",
  "created": "$(date '+%Y-%m-%d %H:%M:%S')",
  "sample_count": 0,
  "engine": "neural",
  "voice_profile": {
    "base_voice": "Daniel",
    "pitch_modifier": 0.92,
    "speaking_rate": 1.05,
    "gender": "male",
    "personality": "professional",
    "neural_model": true
  }
}
EOF
    fi
fi

# Find neural_voice_server.py
SERVER_SCRIPT="neural_voice_server.py"
if [ ! -f "$SERVER_SCRIPT" ]; then
    # Look for the script in current directory and subdirectories
    SERVER_SCRIPT=$(find . -name "neural_voice_server.py" -type f | head -n 1)

    if [ -z "$SERVER_SCRIPT" ]; then
        echo -e "${RED}Error: neural_voice_server.py not found${NC}"
        exit 1
    fi
fi

# Check for GPU access
GPU_INFO=$(nvidia-smi 2>/dev/null || echo "No NVIDIA GPU found")
if [[ "$GPU_INFO" == *"No NVIDIA GPU found"* ]]; then
    echo -e "${YELLOW}Warning: No NVIDIA GPU detected. Server will run in CPU mode.${NC}"
else
    echo -e "${GREEN}NVIDIA GPU detected. Server will use GPU acceleration.${NC}"
    echo -e "${BLUE}GPU Information:${NC}"
    nvidia-smi
fi

# Get external IP address for client connection info
EXTERNAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

# Create a simple flask requirement file if needed
if ! command -v flask &> /dev/null; then
    echo "Flask not found, creating requirements file..."
    echo "flask>=2.0.0" > requirements.txt
    echo "torch>=1.10.0" >> requirements.txt
    echo "numpy>=1.20.0" >> requirements.txt
    echo "Please install requirements: pip install -r requirements.txt"
fi

# Start the server
echo -e "\n${GREEN}Starting neural voice server...${NC}"
echo -e "${GREEN}Server will be accessible at:${NC}"
echo -e "${BLUE}   http://$EXTERNAL_IP:$PORT${NC}"
echo -e "${GREEN}Use this URL in the client configuration.${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server.${NC}\n"

# Start the server
python3 "$SERVER_SCRIPT" --host "$HOST" --port "$PORT" --model "$MODEL_DIR"