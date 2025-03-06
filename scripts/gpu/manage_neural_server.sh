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
        if [ -f ~/neural_cuda_activate.sh ]; then
            source ~/neural_cuda_activate.sh
        else
            echo "Warning: neural_cuda_activate.sh not found!"
            # Use default environment setup
            export CUDA_HOME=/usr
            export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:\$LD_LIBRARY_PATH
            export CUDA_VISIBLE_DEVICES=0,1,2,3
            export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
        fi
    else
        echo "Using standard conda activation..."
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
    python3 -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('Device count:', torch.cuda.device_count() if torch.cuda.is_available() else 0)" >> \${LOG_FILE} 2>&1
    
    # Make sure model directory exists
    mkdir -p ${MODEL_DIR}
    
    # Start the server
    echo "Starting neural voice server..." >> \${LOG_FILE}
    # IMPORTANT: Using --host 0.0.0.0 to ensure server binds to all interfaces, not just localhost
    echo "Using host 0.0.0.0 to bind to all interfaces for external access" >> \${LOG_FILE}
    nohup python3 -u ${SERVER_SCRIPT} --port ${PORT} --host 0.0.0.0 --model ${MODEL_DIR} >> \${LOG_FILE} 2>&1 &
    
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
        # Check if we have venv activated
        if [ -d "venv" ]; then
            # Activate the venv and run client test
            source venv/bin/activate 2>/dev/null || true
            echo -e "${GREEN}Running client connection test...${NC}"
            python ./scripts/neural_voice/test_neural_voice.py --server-only --server "http://${GPU_HOST}:${PORT}"
        else
            echo -e "${YELLOW}Virtual environment not found, skipping client connection test${NC}"
            echo -e "${YELLOW}Run 'python ./scripts/neural_voice/test_neural_voice.py --server-only' to test client connection${NC}"
        fi
    else
        echo -e "${YELLOW}Server not running, skipping client connection test${NC}"
    fi
}

# Function to run neural voice tests
run_neural_voice_test() {
    echo -e "${GREEN}===== Running Neural Voice System Tests =====${NC}"
    
    # Create a temporary Python test script
    TMP_TEST_SCRIPT="/tmp/neural_voice_test_${PORT}_$(date +%s).py"
    
    cat > "$TMP_TEST_SCRIPT" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
Neural voice system test script integrated into manage_neural_server.sh
Tests server connection, voice model info, and speech synthesis
"""

import sys
import time
import os
import json
import argparse
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("neural-voice-test")

# ANSI color codes for terminal output
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
RED = '\033[31m'
RESET = '\033[0m'

# Default server URL - will be overridden by command line arg
SERVER_URL = 'http://localhost:6000'

def print_color(text: str, color: str = GREEN) -> None:
    """Print colored text to the terminal."""
    colors = {
        'green': GREEN,
        'yellow': YELLOW,
        'blue': BLUE,
        'magenta': MAGENTA,
        'cyan': CYAN,
        'red': RED,
        'reset': RESET
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 60)
    print_color(f" {title}", 'cyan')
    print("=" * 60)

def print_subsection(title: str) -> None:
    """Print a subsection header."""
    print("\n" + "-" * 50)
    print_color(f" {title}", 'magenta')
    print("-" * 50)

def test_server_connection() -> bool:
    """Test connection to the neural voice server."""
    print_subsection("Testing Neural Voice Server Connection")
    print(f"Server URL: {SERVER_URL}")
    
    try:
        # Import requests here to avoid hard dependency
        import requests
        
        # Test basic endpoint
        response = requests.get(f'{SERVER_URL}', timeout=5)
        status_color = 'green' if response.status_code == 200 else 'red'
        print_color(f"Status: {response.status_code}", status_color)
        
        # Pretty print the JSON response
        try:
            data = response.json()
            print_color("Server response:", 'blue')
            print(json.dumps(data, indent=2))
            
            # Check CUDA status
            if data.get('cuda') is True:
                print_color("✅ CUDA is available on the server", 'green')
            else:
                print_color("❌ CUDA is NOT available on the server", 'red')
                
        except json.JSONDecodeError:
            print(response.text)
        
        # If basic connection works, try info endpoint
        if response.status_code == 200:
            try:
                info_response = requests.get(f'{SERVER_URL}/info', timeout=5)
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    print_color("\nServer information:", 'blue')
                    print(json.dumps(info_data, indent=2))
                    
                    # Extract GPU info
                    if 'stats' in info_data and 'gpu_info' in info_data['stats']:
                        gpu_info = info_data['stats']['gpu_info']
                        if gpu_info['device_count'] > 0:
                            print_color(f"\n✅ Found {gpu_info['device_count']} GPU(s):", 'green')
                            for i, device in enumerate(gpu_info['devices']):
                                print_color(f"   Device {i}: {device}", 'green')
                        else:
                            print_color("❌ No GPU devices found", 'red')
            except Exception as e:
                print_color(f"Error getting server info: {e}", 'red')
        
        return response.status_code == 200
        
    except ImportError:
        print_color("❌ Requests module not installed. Cannot check server connection.", 'red')
        print_color("Install with: pip install requests", 'yellow')
        return False
    except Exception as e:
        print_color(f"❌ Error: {e}", 'red')
        return False

def test_basic_synthesis() -> bool:
    """Test basic speech synthesis with the custom voice model."""
    try:
        from src import speech_synthesis as speech
        
        print_subsection("Testing Basic Speech Synthesis")
        
        # Check if custom voice model is loaded
        if speech.ACTIVE_VOICE_MODEL:
            print_color(f"✅ Custom voice model loaded: {speech.ACTIVE_VOICE_MODEL.get('name', 'Unknown')}", 'green')
            print(f"   Created: {speech.ACTIVE_VOICE_MODEL.get('created', 'Unknown')}")
            print(f"   Samples: {speech.ACTIVE_VOICE_MODEL.get('sample_count', 0)}")
        else:
            print_color("⚠️ No custom voice model detected. Using standard system voices.", 'yellow')
        
        # Test custom voice with a simple phrase
        print_color("\nTesting neural voice synthesis:", 'blue')
        test_phrase = "Hello, this is a test of the neural voice synthesis system."
        
        print(f"Speaking: \"{test_phrase}\"")
        result = speech.speak(test_phrase, block=True)
        
        if result:
            print_color("✅ Speech synthesis successful", 'green')
            return True
        else:
            print_color("❌ Speech synthesis failed", 'red')
            return False
            
    except ImportError as e:
        print_color(f"\n❌ Error importing speech synthesis module: {e}", 'red')
        print_color("Make sure you are running from the project root directory", 'yellow')
        return False
    except Exception as e:
        print_color(f"\n❌ Error during synthesis test: {e}", 'red')
        return False

def test_synthesis_api_directly() -> bool:
    """Test the synthesis API directly without using the client library."""
    print_subsection("Testing Synthesis API Directly")
    
    try:
        import requests
        import tempfile
        import subprocess
        
        # Create a temp file for the audio
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        # Test text to synthesize
        test_text = "This is a direct test of the neural voice synthesis API."
        print(f"Synthesizing: \"{test_text}\"")
        
        # Send POST request to synthesize endpoint
        response = requests.post(
            f"{SERVER_URL}/synthesize",
            json={"text": test_text},
            timeout=10
        )
        
        if response.status_code == 200:
            # Save the audio
            with open(temp_path, 'wb') as f:
                f.write(response.content)
                
            print_color(f"✅ Synthesis successful, audio saved to {temp_path}", 'green')
            
            # Try to play the audio on macOS
            if sys.platform == "darwin":
                print("Playing audio...")
                try:
                    subprocess.run(["afplay", temp_path], check=True)
                    print_color("✅ Audio playback successful", 'green')
                except Exception as e:
                    print_color(f"⚠️ Audio playback failed: {e}", 'yellow')
            
            return True
        else:
            print_color(f"❌ Synthesis API call failed with status {response.status_code}", 'red')
            print(response.text)
            return False
    
    except ImportError:
        print_color("❌ Requests module not installed", 'red')
        return False
    except Exception as e:
        print_color(f"❌ Error in direct API test: {e}", 'red')
        return False
    finally:
        # Cleanup temp file
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

def display_voice_model_info() -> bool:
    """Display detailed information about the current voice model."""
    try:
        from src import speech_synthesis as speech
        
        print_subsection("Active Voice Model Details")
        
        if not speech.ACTIVE_VOICE_MODEL:
            print_color("No active voice model found.", 'yellow')
            return False
        
        model = speech.ACTIVE_VOICE_MODEL
        
        model_name = model.get("name", "Unknown")
        model_path = model.get("path", "Unknown")
        engine_type = model.get("engine", "parameter-based")
        sample_count = model.get("sample_count", 0)
        
        print(f"Model name: {model_name}")
        print(f"Model path: {model_path}")
        print(f"Engine type: {engine_type}")
        print(f"Sample count: {sample_count}")
        
        # Display voice profile if available
        if "voice_profile" in model:
            voice_profile = model["voice_profile"]
            print_subsection("Voice Profile Parameters")
            
            for key, value in voice_profile.items():
                if key in ["context_modifiers", "emotion_markers"] and isinstance(value, dict):
                    # Handle nested dictionaries
                    print(f"\n{key}:")
                    for subkey, subvalue in value.items():
                        print(f"  {subkey}: {subvalue}")
                else:
                    print(f"{key}: {value}")
        
        return True
        
    except ImportError as e:
        print_color(f"❌ Error importing speech synthesis module: {e}", 'red')
        return False
    except Exception as e:
        print_color(f"❌ Error displaying model info: {e}", 'red')
        return False

def main():
    """Main function for testing neural voice capabilities."""
    global SERVER_URL
    
    parser = argparse.ArgumentParser(description="Test neural voice synthesis capabilities")
    parser.add_argument("--server-only", action="store_true", help="Only test server connection")
    parser.add_argument("--api-only", action="store_true", help="Only test direct API synthesis")
    parser.add_argument("--synthesis-only", action="store_true", help="Only test basic speech synthesis")
    parser.add_argument("--model-info", action="store_true", help="Display voice model information")
    parser.add_argument("--server", default=SERVER_URL, help="Neural voice server URL")
    args = parser.parse_args()
    
    # Print header
    print_section("Neural Voice System Test")
    
    # Update server URL
    SERVER_URL = args.server
    
    # Check server connection - this is always done
    server_ok = test_server_connection()
    
    # If server connection test fails and we're only testing the server, exit
    if not server_ok:
        print_color("\n❌ Server connection failed.", 'red')
        if args.server_only:
            return False
        print_color("Continuing with local tests...", 'yellow')
    
    # Stop here if only testing server
    if args.server_only:
        return server_ok
    
    # Determine which tests to run
    run_all = not (args.api_only or args.synthesis_only or args.model_info)
    
    test_results = []
    
    try:
        # Show model info if requested or running all tests
        if run_all or args.model_info:
            model_info_ok = display_voice_model_info()
            test_results.append(("Model Info", model_info_ok))
        
        # Test direct API if requested or running all tests and server is ok
        if (run_all or args.api_only) and server_ok:
            api_ok = test_synthesis_api_directly()
            test_results.append(("Direct API", api_ok))
        
        # Test synthesis if requested or running all tests
        if run_all or args.synthesis_only:
            synthesis_ok = test_basic_synthesis()
            test_results.append(("Speech Synthesis", synthesis_ok))
        
        # Print summary
        print_section("Test Results Summary")
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            color = "green" if result else "red"
            print_color(f"{test_name}: {status}", color)
        
        # Overall result
        if all(result for _, result in test_results):
            print_color("\nAll tests passed successfully!", 'green')
        else:
            print_color("\nSome tests failed. See details above.", 'yellow')
        
        # Return overall result
        return all(result for _, result in test_results) if test_results else server_ok
        
    except Exception as e:
        print_color(f"\n❌ Unexpected error: {e}", 'red')
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_color("\nTest interrupted by user.", 'yellow')
        sys.exit(0)
    except Exception as e:
        print_color(f"\nUnexpected error: {e}", 'red')
        sys.exit(1)
PYTHON_EOF

    # Make script executable
    chmod +x "$TMP_TEST_SCRIPT"
    
    # Determine test arguments
    TEST_ARGS=""
    case "$2" in
        server)
            TEST_ARGS="--server-only"
            ;;
        api)
            TEST_ARGS="--api-only"
            ;;
        synthesis)
            TEST_ARGS="--synthesis-only"
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
    
    python "$TMP_TEST_SCRIPT" --server "http://${GPU_HOST}:${PORT}" $TEST_ARGS
    
    # Clean up
    rm -f "$TMP_TEST_SCRIPT"
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