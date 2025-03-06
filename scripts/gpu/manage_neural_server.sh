#!/bin/bash
# Neural Voice Server Management Script
# This script manages the neural voice server on the remote GPU machine with CUDA-enabled environment

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GPU_HOST="192.168.191.55"
GPU_USER="claudecode"
PORT=6000  # Using port 6000 for consistency
SERVER_SCRIPT="gpu_scripts/neural_voice_server.py"
MODEL_DIR="voice_models/neural_voice"
CONDA_ENV="neural_cuda"  # Using our new CUDA-enabled environment
LOG_FILE="/tmp/neural_server_${PORT}_$(date +%s).log"  # Create unique log file with timestamp
SETUP_LOG_FILE="/tmp/neural_env_setup_$(date +%s).log"  # Log file for environment setup

# Command line arguments
ACTION="${1:-start}"  # Default to start if no action provided

# Display banner
echo -e "${BLUE}"
echo "============================================"
echo "   Neural Voice Server Management Tool"
echo "   GPU Accelerated with CUDA Environment"
echo "============================================"
echo -e "${NC}"

# Utility functions from both scripts

# Check connection to GPU server
check_connection() {
    echo -e "${GREEN}Testing connection to GPU server...${NC}"
    if ! ssh -q "${GPU_USER}@${GPU_HOST}" exit; then
        echo -e "${RED}Failed to connect to GPU server${NC}"
        return 1
    fi
    echo -e "${GREEN}Connection to GPU server successful${NC}"
    return 0
}

# Check if conda environment exists
check_conda_env() {
    if ! ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'test -d ~/miniconda3/envs/${CONDA_ENV}'"; then
        echo -e "${RED}Neural CUDA environment not found on GPU server${NC}"
        echo -e "${YELLOW}Please run setup_neural_cuda_env.sh first${NC}"
        return 1
    fi
    return 0
}

# Find neural voice server script
find_server_script() {
    # First check the expected location
    if ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'test -f ~/${SERVER_SCRIPT}'"; then
        return 0
    fi

    # Check for GPU scripts directory
    if ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'test -f ~/whisper-yabai-mac-os-x/gpu_scripts/neural_voice_server.py'"; then
        SERVER_SCRIPT="whisper-yabai-mac-os-x/gpu_scripts/neural_voice_server.py"
        return 0
    fi
    
    # Search for it
    local found_script=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'find ~ -name neural_voice_server.py -type f | head -n 1'")
    
    if [ -z "$found_script" ]; then
        echo -e "${RED}Neural voice server script not found on GPU server${NC}"
        return 1
    fi
    
    # Strip home directory prefix to make path relative to home
    SERVER_SCRIPT=$(echo "$found_script" | sed "s|^/home/${GPU_USER}/||")
    echo -e "${GREEN}Found server script at: ${SERVER_SCRIPT}${NC}"
    return 0
}

# Check activation script
check_activation_script() {
    if ! ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'test -f ~/neural_cuda_activate.sh'"; then
        echo -e "${YELLOW}Activation script not found, will use standard conda activation${NC}"
        USE_SPECIAL_ACTIVATION=false
    else
        USE_SPECIAL_ACTIVATION=true
        echo -e "${GREEN}Found neural_cuda_activate.sh script${NC}"
    fi
}

# Check if server is running
check_server_status() {
    # Use curl with a very short timeout to check if the server is responding
    local curl_cmd="curl -s --connect-timeout 1 http://localhost:${PORT} || echo 'connection failed'"
    local curl_response=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c '$curl_cmd'")
    
    if [[ "$curl_response" == *"connection failed"* ]]; then
        # Double-check with process list since curl might fail for other reasons
        local pid_check=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'pgrep -f \"python.*neural_voice_server.py.*--port ${PORT}\"'")
        if [[ -z "$pid_check" ]]; then
            echo -e "${YELLOW}Neural voice server is not running on port ${PORT}${NC}"
            return 1
        else
            echo -e "${YELLOW}Neural voice server process exists but is not responding on port ${PORT}${NC}"
            return 0
        fi
    else
        # Server is running and responding
        local pid=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'pgrep -f \"python.*neural_voice_server.py.*--port ${PORT}\" | head -n1'")
        echo -e "${GREEN}Neural voice server is running on port ${PORT} (PID: ${pid})${NC}"
        return 0
    fi
}

# Stop the neural voice server
stop_server() {
    echo -e "${GREEN}Stopping neural voice server on GPU host...${NC}"
    
    # Check if the server is running
    if ! check_server_status; then
        echo -e "${YELLOW}Neural voice server is not running on port ${PORT}${NC}"
        return 0
    fi
    
    # Use a direct approach to kill all neural voice server processes on that port
    echo -e "${GREEN}Killing neural voice server processes${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'pkill -f \"python.*neural_voice_server.py.*--port ${PORT}\"'"
    sleep 1
        
    # Wait a moment and check if it's still running
    sleep 2
    if ! check_server_status; then
        echo -e "${GREEN}Neural voice server stopped successfully${NC}"
        return 0
    else
        echo -e "${RED}Failed to stop neural voice server. Using force kill...${NC}"
        # Use force kill (-9) with pkill
        ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'pkill -9 -f \"python.*neural_voice_server.py.*--port ${PORT}\"'"
        sleep 1
        
        if ! check_server_status; then
            echo -e "${GREEN}Neural voice server force-stopped successfully${NC}"
            return 0
        else
            echo -e "${RED}Failed to force-stop neural voice server${NC}"
            return 1
        fi
    fi
}

# Start the neural voice server
start_server() {
    echo -e "${GREEN}Starting neural voice server on GPU host...${NC}"
    
    # Check if any server is running and kill it
    echo -e "${YELLOW}Killing any existing neural voice server processes...${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'pkill -f \"python.*neural_voice_server.py\" || true'"
    sleep 2
    
    # Find the server script
    if ! find_server_script; then
        return 1
    fi
    
    # Check activation script
    check_activation_script
    
    # Simple start command
    echo -e "${GREEN}Starting fresh neural voice server...${NC}"
    local timestamp=$(date +%s)
    local log_file="/tmp/neural_server_${PORT}_${timestamp}.log"
    
    # Print the command we're about to run
    echo -e "${YELLOW}Running command on remote server...${NC}"
    
    # Use a here document to create a script that will be executed on the remote server
    ssh "${GPU_USER}@${GPU_HOST}" << EOF
    # Generate a unique log file name and record it
    LOG_FILE="${LOG_FILE}"
    echo "\${LOG_FILE}" > /tmp/neural_server_current_log
    
    cd ~
    
    # Activate environment with CUDA support
    if ${USE_SPECIAL_ACTIVATION}; then
        echo "Using custom neural_cuda_activate.sh script..."
        source ~/neural_cuda_activate.sh
    else
        echo "Using standard conda activation..."
    # Use our custom activation script that sets up CUDA properly
    source ~/neural_cuda_activate.sh        
        # Set CUDA environment variables
        export CUDA_HOME=/usr
        export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:\$LD_LIBRARY_PATH
        export CUDA_VISIBLE_DEVICES=0,1,2,3
        export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
    fi
    
    # Create necessary directories
    mkdir -p ~/whisper-yabai-mac-os-x/gpu_scripts/audio_cache ~/audio_cache
    
    # Check CUDA status before starting server
    echo "===== CUDA SETUP VERIFICATION =====" > \${LOG_FILE}
    python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('Device count:', torch.cuda.device_count() if torch.cuda.is_available() else 0)" >> \${LOG_FILE} 2>&1
    
    # Make sure model directory exists
    mkdir -p ${MODEL_DIR}
    
    # Start the server
    echo "Starting neural voice server..." >> \${LOG_FILE}
    nohup python -u ${SERVER_SCRIPT} --port ${PORT} --host 0.0.0.0 --model ${MODEL_DIR} >> \${LOG_FILE} 2>&1 &
    
    # Wait a moment to let server start
    sleep 5
    
    # Check if server started successfully
    if pgrep -f "python.*neural_voice_server.py.*--port ${PORT}" > /dev/null; then
        echo "Server started successfully with PID \$(pgrep -f "python.*neural_voice_server.py.*--port ${PORT}")"
        echo "Log file: \${LOG_FILE}"
    else
        echo "Failed to start server"
        cat \${LOG_FILE}
        exit 1
    fi
    
    # Test server connection
    echo "Testing server connection..."
    curl -s --connect-timeout 2 http://localhost:${PORT} || echo "Server not responding yet - check logs"
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Neural voice server started successfully${NC}"
        echo -e "${BLUE}Server is running at: http://${GPU_HOST}:${PORT}${NC}"
        setup_local_env
        return 0
    else
        echo -e "${RED}Failed to start neural voice server${NC}"
        return 1
    fi
}

# Set environment variables on local machine
setup_local_env() {
    echo -e "${GREEN}Setting up local environment for neural voice client${NC}"
    export NEURAL_SERVER="http://${GPU_HOST}:${PORT}"
    echo "export NEURAL_SERVER=\"http://${GPU_HOST}:${PORT}\"" > ~/.neural_server_config
    echo -e "${YELLOW}To use the neural voice server in other terminals, run:${NC}"
    echo -e "${BLUE}source ~/.neural_server_config${NC}"
}

# Get server logs
get_logs() {
    echo -e "${GREEN}Fetching neural voice server logs...${NC}"
    # Get the log file from the stored path
    local log_file=$(ssh "${GPU_USER}@${GPU_HOST}" "cat /tmp/neural_server_current_log 2>/dev/null || echo '${LOG_FILE}'")
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'cat ${log_file} 2>/dev/null || echo \"Log file not found: ${log_file}\"'"
}

# Check GPU information
check_gpu() {
    echo -e "${GREEN}Checking GPU status on server...${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'nvidia-smi || echo \"No NVIDIA GPU found or nvidia-smi not available\"'"
}

# Restart the neural voice server
restart_server() {
    echo -e "${GREEN}Restarting neural voice server...${NC}"
    stop_server
    sleep 2
    start_server
}

# Setup the neural CUDA environment on the remote server
setup_cuda_env() {
    echo -e "${GREEN}Setting up dedicated neural CUDA conda environment...${NC}"
    
    # Create the environment setup script that will run on the remote server
    ssh "${GPU_USER}@${GPU_HOST}" << 'EOF'
    # Log file for the setup process
    LOG_FILE="/tmp/neural_env_setup_$(date +%s).log"
    CONDA_ENV="neural_cuda"
    
    # Start logging
    echo "===== Neural CUDA Environment Setup Log =====" > $LOG_FILE
    date >> $LOG_FILE
    
    # Check CUDA availability on the system
    echo "===== CUDA System Check =====" >> $LOG_FILE
    ls -la /usr/local/cuda* >> $LOG_FILE 2>&1
    ls -la /usr/lib/x86_64-linux-gnu/libcuda* >> $LOG_FILE 2>&1
    nvidia-smi >> $LOG_FILE 2>&1
    
    # Check if conda is available
    if ! command -v conda &> /dev/null; then
        echo "Conda not found. Cannot proceed." >> $LOG_FILE
        echo "Conda not found. Please install Miniconda or Anaconda first."
        exit 1
    fi
    
    # Check if environment already exists and remove it if it does
    echo "Checking for existing neural_cuda environment..." >> $LOG_FILE
    if conda env list | grep -q "^$CONDA_ENV "; then
        echo "Removing existing neural_cuda environment..." >> $LOG_FILE
        conda env remove -n $CONDA_ENV -y >> $LOG_FILE 2>&1
    fi
    
    # Create fresh conda environment with Python 3.9
    echo "Creating fresh neural_cuda conda environment..." >> $LOG_FILE
    conda create -n $CONDA_ENV python=3.9 -y >> $LOG_FILE 2>&1
    
    # Activate the environment and install dependencies
    echo "Installing dependencies in the new environment..." >> $LOG_FILE
    
    # Create a temporary requirements file with exact versions
    cat > /tmp/neural_requirements.txt << 'REQUIREMENTS'
numpy>=1.20.0
scipy>=1.7.0
librosa>=0.9.1
soundfile>=0.10.3
matplotlib>=3.5.0
phonemizer>=3.0.0
flask>=2.0.1
TTS>=0.12.0
REQUIREMENTS
    
    # Install base dependencies
    conda activate $CONDA_ENV && pip install -r /tmp/neural_requirements.txt >> $LOG_FILE 2>&1
    
    # Install PyTorch with CUDA - using pip to ensure we get the CUDA version
    echo "Installing PyTorch with CUDA support..." >> $LOG_FILE
    conda activate $CONDA_ENV && pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118 >> $LOG_FILE 2>&1
    
    # Create a test script to verify CUDA is working
    cat > /tmp/cuda_test.py << 'PYEOF'
import torch
import sys

print("Python version:", sys.version)
print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA version:", torch.version.cuda if torch.cuda.is_available() else "Not available")
print("GPU count:", torch.cuda.device_count() if torch.cuda.is_available() else 0)

if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f"Device {i}: {torch.cuda.get_device_name(i)}")
        
    # Run a small test tensor operation on GPU
    try:
        x = torch.rand(100, 100).cuda()
        y = torch.rand(100, 100).cuda()
        z = torch.matmul(x, y)
        print("Tensor operation successful on GPU")
    except Exception as e:
        print(f"Error running GPU tensor operation: {e}")
else:
    import os
    print("Environment variables:")
    print("- CUDA_HOME:", os.environ.get('CUDA_HOME', 'Not set'))
    print("- LD_LIBRARY_PATH:", os.environ.get('LD_LIBRARY_PATH', 'Not set'))
PYEOF
    
    # Run the CUDA test with environment variables set
    echo "Testing CUDA with PyTorch..." >> $LOG_FILE
    conda activate $CONDA_ENV && \
    export CUDA_HOME=/usr && \
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH && \
    python /tmp/cuda_test.py >> $LOG_FILE 2>&1
    
    # Create a shell script that will properly set up the environment when running the neural server
    cat > ~/neural_cuda_activate.sh << 'ACTIVATE'
#!/bin/bash
# Script to activate the neural_cuda environment with proper CUDA settings

# Activate conda environment
source ~/miniconda3/bin/activate neural_cuda

# Set CUDA environment variables
export CUDA_HOME=/usr
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES=0,1,2,3

# For PyTorch optimization
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Print environment info
echo "Activated neural_cuda environment with CUDA support"
echo "Python: $(which python)"
echo "CUDA_HOME: $CUDA_HOME"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
ACTIVATE

    chmod +x ~/neural_cuda_activate.sh
    
    # Check if TTS is properly installed
    echo "Testing TTS installation..." >> $LOG_FILE
    conda activate $CONDA_ENV && python -c "import TTS; print(f'TTS version: {TTS.__version__}')" >> $LOG_FILE 2>&1
    
    # Create audio cache directory for neural server
    mkdir -p ~/whisper-yabai-mac-os-x/gpu_scripts/audio_cache
    mkdir -p ~/audio_cache
    
    # Show final status
    echo "===== Environment Setup Complete =====" >> $LOG_FILE
    conda activate $CONDA_ENV && pip list >> $LOG_FILE 2>&1
    
    # Copy the log to a more accessible location
    cp $LOG_FILE ~/neural_env_setup.log
    
    # Print success message
    echo "Neural CUDA environment setup complete!"
    echo "Log file: ~/neural_env_setup.log"
    echo ""
    echo "To activate this environment, run:"
    echo "source ~/neural_cuda_activate.sh"
EOF

    # Display the remote setup log
    echo -e "${YELLOW}Setup process completed. Fetching logs...${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "cat ~/neural_env_setup.log"
    
    echo -e "${GREEN}Neural CUDA environment setup completed!${NC}"
    return 0
}

# Main execution
main() {
    # Check connection to GPU server
    if ! check_connection; then
        exit 1
    fi
    
    # Execute the requested action based on first argument
    case "$ACTION" in
        start)
            # Check conda environment before starting
            if ! check_conda_env; then
                echo -e "${YELLOW}Neural CUDA environment not found. Setting it up now...${NC}"
                setup_cuda_env
                if ! check_conda_env; then
                    echo -e "${RED}Failed to set up the neural CUDA environment. Cannot start server.${NC}"
                    exit 1
                fi
            fi
            start_server
            ;;
        stop)
            stop_server
            ;;
        restart)
            # Check conda environment before restarting
            if ! check_conda_env; then
                echo -e "${YELLOW}Neural CUDA environment not found. Setting it up now...${NC}"
                setup_cuda_env
                if ! check_conda_env; then
                    echo -e "${RED}Failed to set up the neural CUDA environment. Cannot restart server.${NC}"
                    exit 1
                fi
            fi
            restart_server
            ;;
        status)
            check_server_status
            ;;
        logs)
            get_logs
            ;;
        gpu)
            check_gpu
            ;;
        setup-env)
            setup_cuda_env
            ;;
        setup)
            setup_local_env
            ;;
        *)
            echo -e "${RED}Unknown action: ${ACTION}${NC}"
            echo -e "${GREEN}Available actions:${NC}"
            echo -e "  ${BLUE}start${NC}      - Start the neural voice server"
            echo -e "  ${BLUE}stop${NC}       - Stop the neural voice server"
            echo -e "  ${BLUE}restart${NC}    - Restart the neural voice server"
            echo -e "  ${BLUE}status${NC}     - Check if the server is running"
            echo -e "  ${BLUE}logs${NC}       - View server logs"
            echo -e "  ${BLUE}gpu${NC}        - Check GPU status on server"
            echo -e "  ${BLUE}setup-env${NC}  - Set up CUDA environment on GPU server"
            echo -e "  ${BLUE}setup${NC}      - Configure local environment variables"
            exit 1
            ;;
    esac
}

# Run the main function
main