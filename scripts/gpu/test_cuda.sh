#!/bin/bash
# Simple CUDA test script

# Check NVIDIA driver
echo "===== CUDA System Check ====="
echo "Checking NVIDIA driver..."
echo claudecode | sudo -S nvidia-smi || echo "Error: nvidia-smi failed. Check GPU drivers."

# Check CUDA libraries
echo -e "\n===== CUDA Libraries Check ====="
echo "Checking CUDA libraries..."
ls -la /usr/lib/x86_64-linux-gnu/libcuda* || echo "Error: CUDA libraries not found in expected location."

# Set environment variables
echo -e "\n===== Environment Variables ====="
echo "Setting CUDA environment variables..."
export CUDA_HOME=/usr
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES=0,1,2,3

echo "CUDA_HOME: ${CUDA_HOME}"
echo "LD_LIBRARY_PATH: ${LD_LIBRARY_PATH}"
echo "CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES}"

# Create simple test script
echo -e "\n===== Running Simple Test ====="
python3 -c "import os; print('CUDA Environment:'); print('CUDA_HOME:', os.environ.get('CUDA_HOME', 'Not set')); print('LD_LIBRARY_PATH:', os.environ.get('LD_LIBRARY_PATH', 'Not set')); print('CUDA_VISIBLE_DEVICES:', os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set'))" || echo "Python3 not available"

# Test if server is ready
echo -e "\n===== Neural Server Status ====="
if [ -f ~/whisper-yabai-mac-os-x/gpu_scripts/neural_voice_server.py ]; then
    echo "Neural voice server script is available."
    
    if [ -f ~/whisper-yabai-mac-os-x/voice_models/neural_voice/model_info.json ]; then
        echo "Model info file is available."
    else
        echo "Model info file is missing."
    fi
    
    # Check if server is running
    if pgrep -f "python.*neural_voice_server.py" > /dev/null; then
        echo "Neural voice server is running."
        ps aux | grep "neural_voice_server.py" | grep -v grep
    else
        echo "Neural voice server is not running."
    fi
else
    echo "Neural voice server script is not available."
fi

echo -e "\n===== Test Complete ====="