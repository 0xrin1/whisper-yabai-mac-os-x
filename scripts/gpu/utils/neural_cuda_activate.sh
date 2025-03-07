#!/bin/bash
# Script to activate the neural_cuda environment with proper CUDA settings

# Activate conda environment using various methods
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda activate neural_cuda
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    . "$HOME/anaconda3/etc/profile.d/conda.sh"
    conda activate neural_cuda
elif [ -f "$HOME/miniconda3/bin/activate" ]; then
    source "$HOME/miniconda3/bin/activate" neural_cuda
else
    echo "WARNING: Could not find conda activation script"
    # Try direct path to python in environment
    if [ -f "$HOME/miniconda3/envs/neural_cuda/bin/python" ]; then
        export PATH="$HOME/miniconda3/envs/neural_cuda/bin:$PATH"
        echo "Using direct path to neural_cuda environment"
    fi
fi

# Set CUDA environment variables for proper detection
export CUDA_HOME=/usr/local/cuda
[ -d /usr/local/cuda-11.8 ] && export CUDA_HOME=/usr/local/cuda-11.8
[ -d /usr/lib/x86_64-linux-gnu ] && export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
[ -d $CUDA_HOME/lib64 ] && export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
[ -d $CUDA_HOME/extras/CUPTI/lib64 ] && export LD_LIBRARY_PATH=$CUDA_HOME/extras/CUPTI/lib64:$LD_LIBRARY_PATH

# Make sure all GPUs are visible
export CUDA_VISIBLE_DEVICES=0,1,2,3
export CUDA_DEVICE_ORDER=PCI_BUS_ID

# For PyTorch optimization
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Print environment info
echo "Activated neural_cuda environment with CUDA support"
if command -v python &> /dev/null; then
    echo "Python: $(which python)"
    echo "Python version: $(python --version)"
    
    # Test PyTorch CUDA detection
    python -c "
import torch
print('PyTorch CUDA available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('  CUDA version:', torch.version.cuda)
    print('  Device count:', torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print(f'  Device {i}:', torch.cuda.get_device_name(i))
else:
    import os
    print('CUDA HOME:', os.environ.get('CUDA_HOME', 'Not set'))
    print('LD_LIBRARY_PATH:', os.environ.get('LD_LIBRARY_PATH', 'Not set'))
"
else
    echo "WARNING: Python not found in PATH after activation"
fi