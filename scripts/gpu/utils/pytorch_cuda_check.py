#!/usr/bin/env python3
"""
PyTorch CUDA Check Script
Verifies PyTorch installation and CUDA detection
Used by manage_neural_server.sh
"""

import torch

def main():
    """Check PyTorch CUDA availability and print results"""
    print('PyTorch CUDA check after installation:')
    print('- CUDA Available:', torch.cuda.is_available())
    
    if torch.cuda.is_available():
        print('- CUDA Version:', torch.version.cuda)
        print('- Device Count:', torch.cuda.device_count())
        for i in range(torch.cuda.device_count()):
            print(f'- Device {i}:', torch.cuda.get_device_name(i))

if __name__ == "__main__":
    main()