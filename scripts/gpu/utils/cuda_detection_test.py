#!/usr/bin/env python3
"""
CUDA Detection Test Script
Checks for CUDA libraries and environment variables
Used by manage_neural_server.sh
"""

import os
import sys

def main():
    """Run CUDA detection tests and print results"""
    print('Environment variables:')
    print('- CUDA_HOME:', os.environ.get('CUDA_HOME', 'Not set'))
    print('- LD_LIBRARY_PATH:', os.environ.get('LD_LIBRARY_PATH', 'Not set'))
    print('- CUDA_VISIBLE_DEVICES:', os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set'))
    print('- PYTHONPATH:', os.environ.get('PYTHONPATH', 'Not set'))
    
    print('\nSystem paths:')
    for p in sys.path:
        print(f'- {p}')
    
    # Look for CUDA libraries
    print('\nCUDA library search:')
    cuda_paths = [
        '/usr/local/cuda/lib64/libcudart.so',
        '/usr/lib/x86_64-linux-gnu/libcudart.so',
        '/usr/lib/x86_64-linux-gnu/libcuda.so',
        '/usr/local/cuda-11/lib64/libcudart.so',
    ]
    for path in cuda_paths:
        print(f'- {path}: {os.path.exists(path)}')

if __name__ == "__main__":
    main()