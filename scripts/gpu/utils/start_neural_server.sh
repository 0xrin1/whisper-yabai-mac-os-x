#!/bin/bash
# Neural voice server startup script
# This script is uploaded to the remote server and executed to start the neural voice server

# Generate a unique log file name and record it
LOG_FILE="${1:-/tmp/neural_server_$(date +%s).log}"
PORT="${2:-6000}"
MODEL_DIR="${3:-voice_models/neural_voice}"
SERVER_SCRIPT="${4:-whisper-yabai-mac-os-x/gpu_scripts/neural_voice_server.py}"

echo "${LOG_FILE}" > /tmp/neural_server_current_log

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
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
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
echo "===== CUDA ENVIRONMENT SETUP =====" > ${LOG_FILE}
echo "CUDA_HOME: $CUDA_HOME" >> ${LOG_FILE}
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH" >> ${LOG_FILE}
echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES" >> ${LOG_FILE}

# Display Python and environment info
echo "===== PYTHON ENVIRONMENT =====" >> ${LOG_FILE}
echo "Python path: $(which python)" >> ${LOG_FILE}
echo "Python version: $(python --version 2>&1)" >> ${LOG_FILE}
echo "pip path: $(which pip 2>/dev/null || echo 'pip not found')" >> ${LOG_FILE}

# Create necessary directories
mkdir -p ~/whisper-yabai-mac-os-x/gpu_scripts/audio_cache ~/audio_cache

# Run package verification
if [ -f ~/package_check.py ]; then
    echo "===== PACKAGE VERIFICATION =====" >> ${LOG_FILE}
    ~/package_check.py >> ${LOG_FILE} 2>&1
else
    echo "===== PACKAGE VERIFICATION =====" >> ${LOG_FILE}
    
    # Check NumPy
    if python -c "import numpy; print(f'NumPy version: {numpy.__version__}')" >> ${LOG_FILE} 2>&1; then
        echo "✓ NumPy is available" >> ${LOG_FILE}
    else
        echo "✗ NumPy not available, installing..." >> ${LOG_FILE}
        pip install numpy==1.22.0 >> ${LOG_FILE} 2>&1
    fi
    
    # Check PyTorch with specific CUDA version
    if python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')" >> ${LOG_FILE} 2>&1; then
        echo "✓ PyTorch is available" >> ${LOG_FILE}
        
        # If PyTorch is available but CUDA is not detected, try reinstall with specific version
        if ! python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available'" >> ${LOG_FILE} 2>&1; then
            echo "✗ PyTorch installed but CUDA not detected, reinstalling with specific CUDA version..." >> ${LOG_FILE}
            pip uninstall -y torch torchvision torchaudio >> ${LOG_FILE} 2>&1
            pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118 >> ${LOG_FILE} 2>&1
        fi
    else
        echo "✗ PyTorch not available, installing..." >> ${LOG_FILE}
        pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118 >> ${LOG_FILE} 2>&1
    fi
    
    # Check TTS 
    if python -c "import TTS; print(f'TTS version: {TTS.__version__}')" >> ${LOG_FILE} 2>&1; then
        echo "✓ TTS is available" >> ${LOG_FILE}
    else
        echo "✗ TTS not available, installing..." >> ${LOG_FILE}
        pip install TTS==0.13.0 >> ${LOG_FILE} 2>&1
    fi
    
    # Check Flask
    if python -c "import flask; print(f'Flask version: {flask.__version__}')" >> ${LOG_FILE} 2>&1; then
        echo "✓ Flask is available" >> ${LOG_FILE}
    else
        echo "✗ Flask not available, installing..." >> ${LOG_FILE}
        pip install flask >> ${LOG_FILE} 2>&1
    fi
fi

# Make sure model directory exists
mkdir -p ${MODEL_DIR}

# Start the server
echo "===== STARTING NEURAL VOICE SERVER =====" >> ${LOG_FILE}
# IMPORTANT: Using --host 0.0.0.0 to ensure server binds to all interfaces, not just localhost
echo "Using host 0.0.0.0 to bind to all interfaces for external access" >> ${LOG_FILE}

# Run server with explicit python path to ensure we use the right environment
PYTHON_PATH=$(which python)
echo "Using Python: ${PYTHON_PATH}" >> ${LOG_FILE}
nohup ${PYTHON_PATH} -u ${SERVER_SCRIPT} --port ${PORT} --host 0.0.0.0 --model ${MODEL_DIR} >> ${LOG_FILE} 2>&1 &

# Wait a moment to let server start
sleep 5

# Check if server started successfully
if pgrep -f "python.*neural_voice_server.py.*--port ${PORT}" > /dev/null; then
    echo "Server started successfully with PID $(pgrep -f "python.*neural_voice_server.py.*--port ${PORT}")"
    echo "Log file: ${LOG_FILE}"
else
    echo "Failed to start server"
    cat ${LOG_FILE}
    exit 1
fi

# Test server connection
echo "Testing server connection..."
curl -s --connect-timeout 2 http://localhost:${PORT} || echo "Server not responding yet - check logs"