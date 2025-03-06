#!/bin/bash
# CUDA Fix Script for Neural Voice Server
# This script fixes CUDA detection issues on the GPU server

# IMPORTANT:
# 1. We know CUDA is installed on the system with RTX 3090 GPUs
# 2. We need to ensure the neural_cuda environment is used
# 3. PyTorch must be compiled with CUDA support
# 4. Environment variables must be properly set for CUDA detection

echo "=== Fixing CUDA setup for Neural Voice Server ==="

# Check if running on the GPU server directly or need to SSH
if [[ $(hostname) == *"gpu"* ]]; then
  # Running directly on GPU server
  REMOTE=false
  ACTIVATE_CMD="source ~/miniconda3/bin/activate neural_cuda"
else
  # We need to use the manage_neural_server.sh script
  echo "This script should be run on the GPU server directly."
  echo "Please use: scripts/gpu/manage_neural_server.sh restart"
  echo "If issues persist, ensure proper CUDA support in PyTorch"
  exit 1
fi

# Activate the neural_cuda environment (we MUST use this environment)
echo "Activating neural_cuda environment..."
$ACTIVATE_CMD

# Set CUDA environment variables
export CUDA_HOME=/usr
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES=0,1,2,3  # Use all available GPUs
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Check if we can link against libcuda
echo "CUDA libraries in system:"
ls -la /usr/lib/x86_64-linux-gnu/libcuda*

echo "Checking PyTorch CUDA setup:"
python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA Available:', torch.cuda.is_available()); print('CUDA Version:', torch.version.cuda if torch.cuda.is_available() else 'Not available'); print('GPU Count:', torch.cuda.device_count() if torch.cuda.is_available() else 0);"

# If CUDA is not available, reinstall PyTorch with explicit CUDA support
if ! python -c "import torch; exit(0 if torch.cuda.is_available() else 1)"; then
  echo "CUDA not detected by PyTorch. Reinstalling with explicit CUDA support..."
  # We MUST use this specific version to ensure CUDA compatibility
  pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
  
  # Verify installation
  python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA Available:', torch.cuda.is_available())"
fi

# Create a custom activation script to ensure CUDA is properly set up
echo "Creating CUDA environment activation script..."
cat > ~/neural_cuda_activate.sh << 'EOF'
#!/bin/bash
# Activate neural_cuda environment with proper CUDA settings

# Activate conda environment - MUST use neural_cuda
source ~/miniconda3/bin/activate neural_cuda

# Set CUDA environment variables - CRITICAL for detection
export CUDA_HOME=/usr
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
export CUDA_VISIBLE_DEVICES=0,1,2,3
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Print environment info
echo "Activated neural_cuda environment with CUDA support"
echo "Python: $(which python)"
echo "CUDA_HOME: $CUDA_HOME"
EOF

chmod +x ~/neural_cuda_activate.sh

echo "=== CUDA setup complete ==="
echo "Use 'scripts/gpu/manage_neural_server.sh restart' to restart the server"
echo "The server MUST use the neural_cuda environment for proper CUDA detection"
