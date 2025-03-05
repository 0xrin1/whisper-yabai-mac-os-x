#!/bin/bash
# Script to check GPU server status

# Load configuration from config/.env file
if [[ -f config/.env ]]; then
    # Parse config/.env file and export variables
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # Skip comments and empty lines
        if [[ $key == \#* ]] || [[ -z $key ]]; then
            continue
        fi
        # Remove quotes and export the variable
        value=$(echo $value | sed 's/^["'"'"']//;s/["'"'"']$//')
        export "$key=$value"
    done < config/.env
else
    echo "Error: config/.env file not found"
    exit 1
fi

echo "=== Checking GPU Server Status ==="
echo "Host: $GPU_SERVER_HOST"
echo "User: $GPU_SERVER_USER"
echo

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "sshpass is not installed. Installing..."
    brew install hudochenkov/sshpass/sshpass
fi

# Create SSH commands
SSHPASS_CMD="sshpass -p $GPU_SERVER_PASSWORD"
SSH_BASE="$SSHPASS_CMD ssh -o StrictHostKeyChecking=no -p $GPU_SERVER_PORT $GPU_SERVER_USER@$GPU_SERVER_HOST"

# Check server connectivity
echo "Testing connection to GPU server..."
if $SSH_BASE "echo 'Connection successful'" > /dev/null 2>&1; then
    echo "✅ Connected to GPU server"
else
    echo "❌ Failed to connect to GPU server"
    exit 1
fi

# Check GPU status with nvidia-smi
echo
echo "=== GPU Information ==="
$SSH_BASE "sudo nvidia-smi || nvidia-smi || echo 'Failed to run nvidia-smi. GPU info not available.'"

# Check system load
echo
echo "=== System Load ==="
$SSH_BASE "uptime && echo && echo 'CPU Usage:' && top -bn1 | head -20"

# Check disk space
echo
echo "=== Disk Space ==="
$SSH_BASE "df -h | grep -E '/$|/home'"

# Check RAM usage
echo
echo "=== Memory Usage ==="
$SSH_BASE "free -h"

# Find Python and pip
echo
echo "=== Python Environment ==="
$SSH_BASE "which python3 && python3 --version && which pip3 || which pip || echo 'pip not found in PATH'"

# List installed ML packages
echo
echo "=== Installed ML Packages ==="
$SSH_BASE "python3 -m pip list 2>/dev/null | grep -E 'torch|transformers|tts|tensorflow|voice|clone' || echo 'No ML packages found or pip not available'"

echo
echo "GPU server check complete"