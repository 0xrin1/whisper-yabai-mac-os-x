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
    
    # Check and upload activation script
    check_activation_script
    
    # Upload package check script
    echo -e "${GREEN}Uploading package check script...${NC}"
    scp "${SCRIPT_DIR}/utils/package_check.py" "${GPU_USER}@${GPU_HOST}:~/package_check.py"
    ssh "${GPU_USER}@${GPU_HOST}" "chmod +x ~/package_check.py"
    
    # Upload and run the server startup script
    echo -e "${GREEN}Starting neural voice server...${NC}"
    local timestamp=$(date +%s)
    local log_file="/tmp/neural_server_${PORT}_${timestamp}.log"
    
    # Upload the server startup script
    echo -e "${YELLOW}Uploading server startup script...${NC}"
    scp "${SCRIPT_DIR}/utils/start_neural_server.sh" "${GPU_USER}@${GPU_HOST}:~/start_neural_server.sh"
    ssh "${GPU_USER}@${GPU_HOST}" "chmod +x ~/start_neural_server.sh"
    
    # Run the server startup script
    echo -e "${YELLOW}Running server startup script...${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "~/start_neural_server.sh \"${log_file}\" \"${PORT}\" \"${MODEL_DIR}\" \"${SERVER_SCRIPT}\""

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
    
    # Upload neural_cuda_activate script
    echo -e "${GREEN}Uploading activation script...${NC}"
    scp "${SCRIPT_DIR}/utils/neural_cuda_activate.sh" "${GPU_USER}@${GPU_HOST}:~/neural_cuda_activate.sh"
    ssh "${GPU_USER}@${GPU_HOST}" "chmod +x ~/neural_cuda_activate.sh"
    
    # Upload conda environment setup script
    echo -e "${GREEN}Uploading conda environment setup script...${NC}"
    scp "${SCRIPT_DIR}/utils/setup_conda_env.sh" "${GPU_USER}@${GPU_HOST}:~/setup_conda_env.sh"
    ssh "${GPU_USER}@${GPU_HOST}" "chmod +x ~/setup_conda_env.sh"
    
    # Run the setup script
    echo -e "${GREEN}Running environment setup script...${NC}"
    ssh "${GPU_USER}@${GPU_HOST}" "~/setup_conda_env.sh"

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