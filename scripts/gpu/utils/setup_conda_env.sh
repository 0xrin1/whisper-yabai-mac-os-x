#!/bin/bash
# Setup script for neural CUDA conda environment
# This script is uploaded to the remote server and executed to create the environment

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