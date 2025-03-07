#!/usr/bin/env python3
"""
Package Check Utility
Verifies installed Python packages and their versions
Used by manage_neural_server.sh
"""

import sys
import importlib.util
from typing import Dict, Optional, List, Tuple

# Colors for terminal output
GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'
RESET = '\033[0m'

def check_package(package_name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a package is installed and get its version
    
    Args:
        package_name: Name of the package to check
        
    Returns:
        Tuple of (is_installed, version)
    """
    try:
        spec = importlib.util.find_spec(package_name)
        if spec is None:
            return False, None
        
        # Import the package to get its version
        package = importlib.import_module(package_name)
        version = getattr(package, "__version__", "unknown")
        return True, version
    except ImportError:
        return False, None
    except Exception as e:
        print(f"Error checking {package_name}: {e}")
        return False, None

def check_cuda() -> Tuple[bool, Optional[str]]:
    """
    Check if CUDA is available through PyTorch
    
    Returns:
        Tuple of (is_available, version)
    """
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        cuda_version = torch.version.cuda if cuda_available else None
        return cuda_available, cuda_version
    except ImportError:
        return False, None
    except Exception as e:
        print(f"Error checking CUDA: {e}")
        return False, None

def check_numpy() -> bool:
    """Check for NumPy and print its version"""
    installed, version = check_package("numpy")
    if installed:
        print(f"NumPy version: {version}")
        return True
    else:
        print("NumPy not installed")
        return False

def check_pytorch() -> bool:
    """Check for PyTorch and print its version and CUDA status"""
    installed, version = check_package("torch")
    if installed:
        cuda_available, cuda_version = check_cuda()
        print(f"PyTorch version: {version}")
        print(f"CUDA available: {cuda_available}")
        if cuda_available:
            print(f"CUDA version: {cuda_version}")
        else:
            print("CUDA not available")
        return True
    else:
        print("PyTorch not installed")
        return False

def check_tts() -> bool:
    """Check for TTS and print its version"""
    installed, version = check_package("TTS")
    if installed:
        print(f"TTS version: {version}")
        return True
    else:
        print("TTS not installed")
        return False

def check_flask() -> bool:
    """Check for Flask and print its version"""
    installed, version = check_package("flask")
    if installed:
        print(f"Flask version: {version}")
        return True
    else:
        print("Flask not installed")
        return False

def check_all_packages() -> Dict[str, bool]:
    """Check all required packages and return results"""
    results = {}
    
    print("Checking required packages:")
    
    # Check NumPy
    print("\n=== NumPy ===")
    results["numpy"] = check_numpy()
    
    # Check PyTorch
    print("\n=== PyTorch ===")
    results["pytorch"] = check_pytorch()
    
    # Check TTS
    print("\n=== TTS ===")
    results["tts"] = check_tts()
    
    # Check Flask
    print("\n=== Flask ===")
    results["flask"] = check_flask()
    
    return results

def main():
    """Main function to run package checks"""
    # Parse command line arguments
    if len(sys.argv) > 1:
        package = sys.argv[1].lower()
        if package == "numpy":
            check_numpy()
        elif package == "pytorch":
            check_pytorch()
        elif package == "tts":
            check_tts()
        elif package == "flask":
            check_flask()
        else:
            print(f"Unknown package: {package}")
            print("Available options: numpy, pytorch, tts, flask")
    else:
        # Check all packages
        results = check_all_packages()
        
        # Print summary
        print("\n=== Summary ===")
        all_installed = all(results.values())
        for package, installed in results.items():
            status = f"{GREEN}✓{RESET}" if installed else f"{RED}✗{RESET}"
            print(f"{status} {package}")
        
        if all_installed:
            print(f"\n{GREEN}All required packages are installed{RESET}")
        else:
            print(f"\n{YELLOW}Some packages are missing{RESET}")

if __name__ == "__main__":
    main()