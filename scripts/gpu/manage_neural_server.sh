#!/bin/bash
# Neural Voice Server Management Script
# This script manages the neural voice server on the remote GPU machine with CUDA-enabled environment

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

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
        echo -e "${YELLOW}Activation script not found, creating one now...${NC}"
        
        # Upload the activation script from the utils directory
        scp "${SCRIPT_DIR}/utils/neural_cuda_activate.sh" "${GPU_USER}@${GPU_HOST}:~/neural_cuda_activate.sh"
        
        # Make it executable
        ssh "${GPU_USER}@${GPU_HOST}" "chmod +x ~/neural_cuda_activate.sh"
        
        if [ $? -eq 0 ]; then
            USE_SPECIAL_ACTIVATION=true
            echo -e "${GREEN}Created neural_cuda_activate.sh script${NC}"
        else
            USE_SPECIAL_ACTIVATION=false
            echo -e "${RED}Failed to create activation script, will use standard conda activation${NC}"
        fi
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
            
            # Get process details
            local pid=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'pgrep -f \"python.*neural_voice_server.py.*--port ${PORT}\" | head -n1'")
            echo -e "${BLUE}Process information (PID: ${pid}):${NC}"
            
            # Check if process is running with correct parameters
            local cmd_line=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'ps -p ${pid} -o args='")
            echo -e "${BLUE}Command line: ${cmd_line}${NC}"
            
            # Check if process is binding to any interface or just localhost
            local netstat_cmd="ss -tlnp 2>/dev/null | grep ${pid} || netstat -tlnp 2>/dev/null | grep ${pid}"
            local binding_info=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c '$netstat_cmd'")
            if [[ -z "$binding_info" ]]; then
                echo -e "${RED}No network binding information found for PID ${pid}${NC}"
                echo -e "${YELLOW}Process might be failing to bind to port ${PORT}${NC}"
            else
                echo -e "${BLUE}Network binding: ${binding_info}${NC}"
                
                # Check if binding to localhost only
                if [[ "$binding_info" == *"127.0.0.1:${PORT}"* || "$binding_info" == *"localhost:${PORT}"* ]]; then
                    echo -e "${YELLOW}WARNING: Server is only bound to localhost, not external interfaces${NC}"
                    echo -e "${YELLOW}This is why remote clients cannot connect. Use --host 0.0.0.0 to bind to all interfaces${NC}"
                fi
            fi
            
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
    
    # Get the PID of the process on the specific port
    local pid=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'lsof -t -i:${PORT} || echo \"\"'")
    
    if [ -z "$pid" ]; then
        # Try the pattern match approach as a fallback
        pid=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'pgrep -f \"python.*neural_voice_server.py.*--port ${PORT}\" || echo \"\"'")
    fi
    
    if [ -z "$pid" ]; then
        echo -e "${YELLOW}Neural voice server is not running on port ${PORT}${NC}"
        return 0
    fi
    
    # First try gentle kill
    echo -e "${GREEN}Killing neural voice server process (PID: ${pid})${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'kill ${pid} 2>/dev/null || true'"
    sleep 2
    
    # Check if the process is still running
    pid=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'lsof -t -i:${PORT} 2>/dev/null || echo \"\"'")
    if [ -z "$pid" ]; then
        echo -e "${GREEN}Neural voice server stopped successfully${NC}"
        return 0
    fi
    
    # Try force kill
    echo -e "${RED}Failed to stop neural voice server. Using force kill...${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'kill -9 ${pid} 2>/dev/null || true'"
    sleep 2
    
    # Check one more time
    pid=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'lsof -t -i:${PORT} 2>/dev/null || echo \"\"'")
    if [ -z "$pid" ]; then
        echo -e "${GREEN}Neural voice server force-stopped successfully${NC}"
        return 0
    fi
    
    # Last resort - use the port directly
    echo -e "${RED}Failed to stop by PID. Trying extreme measures...${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'fuser -k ${PORT}/tcp 2>/dev/null || true'"
    sleep 2
    
    # Final check
    pid=$(ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'lsof -t -i:${PORT} 2>/dev/null || echo \"\"'")
    if [ -z "$pid" ]; then
        echo -e "${GREEN}Neural voice server stopped by port kill${NC}"
        return 0
    else
        echo -e "${RED}Failed to force-stop neural voice server. Manual intervention needed.${NC}"
        echo -e "${YELLOW}Run manually on server: sudo lsof -i:${PORT} and then kill -9 PID${NC}"
        return 1
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
    
    # Check if the neural_cuda environment exists
    if ! check_conda_env; then
        echo -e "${YELLOW}Neural CUDA environment not found. Setting it up now...${NC}"
        setup_cuda_env
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
    if [ -f ~/neural_cuda_activate.sh ]; then
        echo "Using neural_cuda_activate.sh script..."
        source ~/neural_cuda_activate.sh
    else
        echo "Warning: neural_cuda_activate.sh not found!"
        
        # Try to source conda directly
        if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
            . "$HOME/miniconda3/etc/profile.d/conda.sh"
            conda activate neural_cuda
        else
            echo "Trying direct environment path..."
            export PATH="$HOME/miniconda3/envs/neural_cuda/bin:$PATH"
        fi
        
        # Set CUDA environment variables
        export CUDA_HOME=/usr
        export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:\$LD_LIBRARY_PATH
        export CUDA_VISIBLE_DEVICES=0,1,2,3
        export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
    fi
    
    # Verify Python is working
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python not found after activation. Check environment setup."
        exit 1
    fi
    
    # Set proper CUDA environment variables
    export CUDA_HOME=/usr/local/cuda
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64:$LD_LIBRARY_PATH
    export CUDA_VISIBLE_DEVICES=0,1,2,3
    export CUDA_DEVICE_ORDER=PCI_BUS_ID
    echo "===== CUDA ENVIRONMENT SETUP =====" > \${LOG_FILE}
    echo "CUDA_HOME: $CUDA_HOME" >> \${LOG_FILE}
    echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH" >> \${LOG_FILE}
    echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES" >> \${LOG_FILE}
    
    # Display Python and environment info
    echo "===== PYTHON ENVIRONMENT =====" >> \${LOG_FILE}
    echo "Python path: \$(which python)" >> \${LOG_FILE}
    echo "Python version: \$(python --version 2>&1)" >> \${LOG_FILE}
    echo "pip path: \$(which pip 2>/dev/null || echo 'pip not found')" >> \${LOG_FILE}
    
    # Create necessary directories
    mkdir -p ~/whisper-yabai-mac-os-x/gpu_scripts/audio_cache ~/audio_cache
    
    # Upload and run the CUDA detection test script
    echo "===== CUDA DETECTION TEST =====" >> \${LOG_FILE}
    scp "${SCRIPT_DIR}/utils/cuda_detection_test.py" "${GPU_USER}@${GPU_HOST}:~/cuda_detection_test.py"
    ssh "${GPU_USER}@${GPU_HOST}" "chmod +x ~/cuda_detection_test.py"
    ssh "${GPU_USER}@${GPU_HOST}" "~/cuda_detection_test.py" >> \${LOG_FILE} 2>&1

    # Check if required packages are available
    echo "===== PACKAGE VERIFICATION =====" >> \${LOG_FILE}
    
    # Check NumPy
    if python -c "import numpy; print(f'NumPy version: {numpy.__version__}')" >> \${LOG_FILE} 2>&1; then
        echo "✓ NumPy is available" >> \${LOG_FILE}
    else
        echo "✗ NumPy not available, installing..." >> \${LOG_FILE}
        pip install numpy==1.22.0 >> \${LOG_FILE} 2>&1
    fi
    
    # Check PyTorch with specific CUDA version
    if python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')" >> \${LOG_FILE} 2>&1; then
        echo "✓ PyTorch is available" >> \${LOG_FILE}
        
        # If PyTorch is available but CUDA is not detected, try reinstall with specific version
        if ! python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" >> \${LOG_FILE} 2>&1; then
            echo "✗ PyTorch installed but CUDA not detected, reinstalling with specific CUDA version..." >> \${LOG_FILE}
            pip uninstall -y torch torchvision torchaudio >> \${LOG_FILE} 2>&1
            pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118 >> \${LOG_FILE} 2>&1
        fi
    else
        echo "✗ PyTorch not available, installing..." >> \${LOG_FILE}
        pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118 >> \${LOG_FILE} 2>&1
    fi
    
    # Upload and run the PyTorch CUDA check script
    scp "${SCRIPT_DIR}/utils/pytorch_cuda_check.py" "${GPU_USER}@${GPU_HOST}:~/pytorch_cuda_check.py"
    ssh "${GPU_USER}@${GPU_HOST}" "chmod +x ~/pytorch_cuda_check.py"
    ssh "${GPU_USER}@${GPU_HOST}" "~/pytorch_cuda_check.py" >> \${LOG_FILE} 2>&1
    
    # Check TTS 
    if python -c "import TTS; print(f'TTS version: {TTS.__version__}')" >> \${LOG_FILE} 2>&1; then
        echo "✓ TTS is available" >> \${LOG_FILE}
    else
        echo "✗ TTS not available, installing..." >> \${LOG_FILE}
        pip install TTS==0.13.0 >> \${LOG_FILE} 2>&1
    fi
    
    # Check Flask
    if python -c "import flask; print(f'Flask version: {flask.__version__}')" >> \${LOG_FILE} 2>&1; then
        echo "✓ Flask is available" >> \${LOG_FILE}
    else
        echo "✗ Flask not available, installing..." >> \${LOG_FILE}
        pip install flask >> \${LOG_FILE} 2>&1
    fi
    
    # Make sure model directory exists
    mkdir -p ${MODEL_DIR}
    
    # Start the server
    echo "===== STARTING NEURAL VOICE SERVER =====" >> \${LOG_FILE}
    # IMPORTANT: Using --host 0.0.0.0 to ensure server binds to all interfaces, not just localhost
    echo "Using host 0.0.0.0 to bind to all interfaces for external access" >> \${LOG_FILE}
    
    # Run server with explicit python path to ensure we use the right environment
    PYTHON_PATH=\$(which python)
    echo "Using Python: \${PYTHON_PATH}" >> \${LOG_FILE}
    nohup \${PYTHON_PATH} -u ${SERVER_SCRIPT} --port ${PORT} --host 0.0.0.0 --model ${MODEL_DIR} >> \${LOG_FILE} 2>&1 &
    
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

# Check detailed GPU information
check_gpu() {
    echo -e "${GREEN}Checking GPU status on server...${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'nvidia-smi || echo \"No NVIDIA GPU found or nvidia-smi not available\"'"
}

# Check full GPU server status
check_full_gpu_status() {
    echo -e "${GREEN}=== Checking GPU Server Status ===${NC}"
    echo -e "${GREEN}Host: ${GPU_HOST}${NC}"
    echo -e "${GREEN}User: ${GPU_USER}${NC}"
    echo

    # Check GPU status with nvidia-smi
    echo -e "${GREEN}=== GPU Information ===${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'sudo nvidia-smi || nvidia-smi || echo \"Failed to run nvidia-smi. GPU info not available.\"'"

    # Check system load
    echo
    echo -e "${GREEN}=== System Load ===${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'uptime && echo && echo \"CPU Usage:\" && top -bn1 | head -20'"

    # Check disk space
    echo
    echo -e "${GREEN}=== Disk Space ===${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'df -h | grep -E \"/$|/home\"'"

    # Check RAM usage
    echo
    echo -e "${GREEN}=== Memory Usage ===${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'free -h'"

    # Find Python and pip
    echo
    echo -e "${GREEN}=== Python Environment ===${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'which python3 && python3 --version && which pip3 || which pip || echo \"pip not found in PATH\"'"

    # List installed ML packages
    echo
    echo -e "${GREEN}=== Installed ML Packages ===${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "bash -l -c 'python3 -m pip list 2>/dev/null | grep -E \"torch|transformers|tts|tensorflow|voice|clone\" || echo \"No ML packages found or pip not available\"'"
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
    
    # Check if miniconda is installed correctly
    echo "Checking for Miniconda..." >> $LOG_FILE
    if [ -d "$HOME/miniconda3" ]; then
        echo "Miniconda found at $HOME/miniconda3" >> $LOG_FILE
    else
        echo "Miniconda not found in expected location. Will use system conda if available." >> $LOG_FILE
    fi
    
    # Try different methods to activate conda
    if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        echo "Sourcing conda.sh from miniconda3..." >> $LOG_FILE
        . "$HOME/miniconda3/etc/profile.d/conda.sh"
        CONDA_CMD="conda"
    elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        echo "Sourcing conda.sh from anaconda3..." >> $LOG_FILE
        . "$HOME/anaconda3/etc/profile.d/conda.sh"
        CONDA_CMD="conda"
    elif command -v conda &> /dev/null; then
        echo "Using system conda command..." >> $LOG_FILE
        CONDA_CMD="conda"
    elif [ -f "$HOME/miniconda3/bin/conda" ]; then
        echo "Using miniconda3/bin/conda directly..." >> $LOG_FILE
        CONDA_CMD="$HOME/miniconda3/bin/conda"
    else
        echo "ERROR: Conda not found in any standard location. Cannot proceed." >> $LOG_FILE
        echo "ERROR: Conda not found in any standard location. Cannot proceed."
        exit 1
    fi
    
    echo "Using conda command: $CONDA_CMD" >> $LOG_FILE
    
    # Check CUDA availability on the system
    echo "===== CUDA System Check =====" >> $LOG_FILE
    ls -la /usr/local/cuda* >> $LOG_FILE 2>&1 || echo "No CUDA found in /usr/local" >> $LOG_FILE
    ls -la /usr/lib/x86_64-linux-gnu/libcuda* >> $LOG_FILE 2>&1 || echo "No CUDA libs found in standard location" >> $LOG_FILE
    nvidia-smi >> $LOG_FILE 2>&1 || echo "nvidia-smi failed, may need permissions" >> $LOG_FILE
    
    # Check if environment already exists
    echo "Checking for existing neural_cuda environment..." >> $LOG_FILE
    if $CONDA_CMD env list | grep -q "neural_cuda"; then
        echo "Neural CUDA environment already exists" >> $LOG_FILE
        
        # Check if the environment already has the required packages
        echo "Checking for required packages in existing environment..." >> $LOG_FILE
        if $CONDA_CMD run -n neural_cuda python -c "import sys, numpy, torch, flask; print('Key packages available')" >> $LOG_FILE 2>&1; then
            echo "✓ Basic packages found in environment" >> $LOG_FILE
            NEEDS_CORE_PACKAGES=false
        else
            echo "✗ Some basic packages missing, will install them" >> $LOG_FILE
            NEEDS_CORE_PACKAGES=true
        fi
        
        # Check for TTS specifically since it's often missing
        if $CONDA_CMD run -n neural_cuda python -c "import TTS; print(f'TTS version: {TTS.__version__}')" >> $LOG_FILE 2>&1; then
            echo "✓ TTS package already installed" >> $LOG_FILE
            NEEDS_TTS=false
        else
            echo "✗ TTS package missing, will install it" >> $LOG_FILE
            NEEDS_TTS=true
        fi
    else
        echo "Creating neural_cuda environment from scratch..." >> $LOG_FILE
        $CONDA_CMD create -n neural_cuda python=3.9 -y >> $LOG_FILE 2>&1
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to create conda environment" >> $LOG_FILE
            echo "ERROR: Failed to create conda environment"
            exit 1
        fi
        NEEDS_CORE_PACKAGES=true
        NEEDS_TTS=true
    fi
    
    # Function to install packages
    install_packages() {
        echo "Installing required packages..." >> $LOG_FILE
        
        # Make sure conda environment is activated properly
        if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
            . "$HOME/miniconda3/etc/profile.d/conda.sh"
        fi
        
        # Activate the environment
        $CONDA_CMD activate neural_cuda
        
        if [ $NEEDS_CORE_PACKAGES = true ]; then
            echo "Installing core packages..." >> $LOG_FILE
            pip install numpy scipy flask >> $LOG_FILE 2>&1
            pip install librosa soundfile matplotlib phonemizer >> $LOG_FILE 2>&1
            
            # Install PyTorch with CUDA
            echo "Installing PyTorch with CUDA support..." >> $LOG_FILE
            # Use CUDA 11.8 for best compatibility
            pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118 >> $LOG_FILE 2>&1
        else
            echo "Core packages already installed, skipping" >> $LOG_FILE
        fi
        
        if [ $NEEDS_TTS = true ]; then
            echo "Installing TTS package..." >> $LOG_FILE
            pip install TTS==0.13.0 >> $LOG_FILE 2>&1
        else
            echo "TTS already installed, skipping" >> $LOG_FILE
        fi
    }
    
    # Install required packages
    install_packages
    
    # Create or update the activation script
    echo "Creating activation script..." >> $LOG_FILE
    cp "$SCRIPT_DIR/utils/neural_cuda_activate.sh" ~/neural_cuda_activate.sh
    chmod +x ~/neural_cuda_activate.sh
    
    # Create audio cache directories
    echo "Creating cache directories..." >> $LOG_FILE
    mkdir -p ~/whisper-yabai-mac-os-x/gpu_scripts/audio_cache >> $LOG_FILE 2>&1
    mkdir -p ~/audio_cache >> $LOG_FILE 2>&1
    
    # Test the environment
    echo "Testing environment setup..." >> $LOG_FILE
    source ~/neural_cuda_activate.sh >> $LOG_FILE 2>&1
    
    # Verify Python and key packages
    echo "Verifying Python and packages..." >> $LOG_FILE
    which python >> $LOG_FILE 2>&1
    python --version >> $LOG_FILE 2>&1
    
    # Verify NumPy
    echo "Verifying NumPy..." >> $LOG_FILE
    python -c "import numpy; print(f'NumPy version: {numpy.__version__}')" >> $LOG_FILE 2>&1 || echo "NumPy verification failed" >> $LOG_FILE
    
    # Verify PyTorch and CUDA
    echo "Verifying PyTorch and CUDA..." >> $LOG_FILE
    python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"Not available\"}')" >> $LOG_FILE 2>&1 || echo "PyTorch verification failed" >> $LOG_FILE
    
    # Verify TTS
    echo "Verifying TTS..." >> $LOG_FILE
    python -c "import TTS; print(f'TTS version: {TTS.__version__}')" >> $LOG_FILE 2>&1 || echo "TTS verification failed" >> $LOG_FILE
    
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
    ssh "${GPU_USER}@${GPU_HOST}" "cat ~/neural_env_setup.log 2>/dev/null || echo 'Log file not found, but setup may have succeeded'"
    
    echo -e "${GREEN}Neural CUDA environment setup completed!${NC}"
    return 0
}

# Main execution
main() {
    # Check connection to GPU server
    if ! check_connection; then
        exit 1
    fi
    
    # Comprehensive check including both server status and client connection
check_comprehensive_status() {
    echo -e "${GREEN}=== Comprehensive Neural Voice Server Status Check ===${NC}"
    
    # First check server status
    check_server_status
    
    # Check GPU status
    check_full_gpu_status
    
    # First check network connectivity using telnet or nc
    echo -e "${GREEN}=== Testing Network Connectivity ===${NC}"
    echo -e "${BLUE}Checking network connectivity to port ${PORT}...${NC}"
    
    # Check which tool is available
    if command -v nc &> /dev/null; then
        if timeout 2 nc -zv ${GPU_HOST} ${PORT} &> /dev/null; then
            echo -e "${GREEN}✅ Port ${PORT} is reachable${NC}"
            port_reachable=true
        else
            echo -e "${RED}❌ Port ${PORT} is NOT reachable${NC}"
            echo -e "${YELLOW}This suggests the server is running but not binding to the port correctly${NC}"
            echo -e "${YELLOW}or there may be a firewall blocking the connection.${NC}"
            port_reachable=false
            
            # Offer to fix by restarting the server
            echo -e "${BLUE}Would you like to restart the server to fix the issue? (y/n)${NC}"
            read -t 10 -n 1 answer || answer="n"
            echo
            
            if [[ "$answer" == "y" ]]; then
                echo -e "${GREEN}Restarting the neural voice server...${NC}"
                restart_server
            else
                echo -e "${YELLOW}You can restart manually with: ./scripts/gpu/manage_neural_server.sh restart${NC}"
            fi
        fi
    else
        # Fallback to timeout and curl
        if timeout 2 curl --connect-timeout 1 -s ${GPU_HOST}:${PORT} &> /dev/null; then
            echo -e "${GREEN}✅ Port ${PORT} is reachable${NC}"
            port_reachable=true
        else
            echo -e "${RED}❌ Port ${PORT} is NOT reachable${NC}" 
            echo -e "${YELLOW}This suggests the server is running but not binding to the port correctly${NC}"
            echo -e "${YELLOW}or there may be a firewall blocking the connection.${NC}"
            port_reachable=false
            
            # Offer to fix by restarting the server
            echo -e "${BLUE}Would you like to restart the server to fix the issue? (y/n)${NC}"
            read -t 10 -n 1 answer || answer="n"
            echo
            
            if [[ "$answer" == "y" ]]; then
                echo -e "${GREEN}Restarting the neural voice server...${NC}"
                restart_server
            else
                echo -e "${YELLOW}You can restart manually with: ./scripts/gpu/manage_neural_server.sh restart${NC}"
            fi
        fi
    fi
    
    # Check if firewall is enabled on the GPU server
    echo -e "${BLUE}Checking firewall status on GPU server...${NC}"
    firewall_status=$(ssh "${GPU_USER}@${GPU_HOST}" "sudo -n systemctl status ufw 2>/dev/null || true")
    
    if [[ $firewall_status == *"Active: active"* ]]; then
        echo -e "${YELLOW}⚠️ Firewall is active on GPU server${NC}"
        echo -e "${YELLOW}Check if port ${PORT} is allowed:${NC}"
        ssh "${GPU_USER}@${GPU_HOST}" "sudo -n ufw status 2>/dev/null || echo 'Cannot check firewall rules (requires sudo)'" 
    else
        echo -e "${GREEN}✅ No active firewall detected${NC}"
    fi
    
    # Test client connection - only if the server is running
    if check_server_status > /dev/null; then
        echo -e "${GREEN}=== Testing Client Connection ===${NC}"
        # Check if we have venv activated and test script exists
        if [ -f ./scripts/neural_voice/test_neural_voice.py ]; then
            # Activate the venv if available
            if [ -d "venv" ]; then
                source venv/bin/activate 2>/dev/null || true
            fi
            
            echo -e "${GREEN}Running client connection test...${NC}"
            python ./scripts/neural_voice/test_neural_voice.py --server-only --server "http://${GPU_HOST}:${PORT}"
        else
            echo -e "${YELLOW}Test script not found, skipping client connection test${NC}"
            echo -e "${YELLOW}Please run the consolidated neural voice test script${NC}"
        fi
    else
        echo -e "${YELLOW}Server not running, skipping client connection test${NC}"
    fi
}

# Function to run neural voice tests
run_neural_voice_test() {
    echo -e "${GREEN}===== Running Neural Voice System Tests =====${NC}"
    
    # Check if the consolidated test script exists
    if [ ! -f "./scripts/neural_voice/test_neural_voice.py" ]; then
        echo -e "${RED}Error: Consolidated test script not found at ./scripts/neural_voice/test_neural_voice.py${NC}"
        echo -e "${YELLOW}Please make sure the neural voice test script is properly installed${NC}"
        return 1
    fi
    
    # Make sure the script is executable
    chmod +x "./scripts/neural_voice/test_neural_voice.py"
    
    # Determine test arguments
    TEST_ARGS=""
    case "$2" in
        server)
            TEST_ARGS="--server-only"
            ;;
        api)
            TEST_ARGS="--api-only"
            ;;
        client)
            TEST_ARGS="--client-only"
            ;;
        model)
            TEST_ARGS="--model-info"
            ;;
        *)
            # Run all tests by default
            TEST_ARGS=""
            ;;
    esac
    
    # Execute the test script with proper Python environment
    if [ -d "venv" ]; then
        source venv/bin/activate 2>/dev/null || true
    fi
    
    echo -e "${GREEN}Running consolidated neural voice test script...${NC}"
    python "./scripts/neural_voice/test_neural_voice.py" --server "http://${GPU_HOST}:${PORT}" $TEST_ARGS
}

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
            check_full_gpu_status
            ;;
        full-status|check|test)
            check_comprehensive_status
            ;;
        test-voice|voice-test)
            run_neural_voice_test "$2"
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
            echo -e "  ${BLUE}check${NC}      - Run comprehensive status check (server + client)"
            echo -e "  ${BLUE}full-status${NC} - Same as check: comprehensive status check"
            echo -e "  ${BLUE}test${NC}       - Same as check: comprehensive status check"
            echo -e "  ${BLUE}test-voice${NC} - Run neural voice tests (accepts: server|api|synthesis|model)"
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