#!/usr/bin/env python3
"""
Test script for neural voice server connectivity.
Tests the basic HTTP connection to the server and verifies CUDA availability.
"""
import os
import sys
import requests
import json

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, project_root)

SERVER_URL = 'http://192.168.191.55:6000'

def print_colored(text, color):
    """Print colored text to terminal."""
    colors = {
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def test_server_connection():
    """Test basic connection to the neural voice server."""
    print_colored("Testing neural voice server connection...", "blue")
    print(f"Server URL: {SERVER_URL}")
    
    try:
        # Test basic endpoint
        response = requests.get(f'{SERVER_URL}', timeout=5)
        print_colored(f"Status: {response.status_code}", "green" if response.status_code == 200 else "red")
        
        # Pretty print the JSON response
        try:
            data = response.json()
            print_colored("Server response:", "blue")
            print(json.dumps(data, indent=2))
            
            # Check CUDA status
            if data.get('cuda') is True:
                print_colored("✅ CUDA is available on the server", "green")
            else:
                print_colored("❌ CUDA is NOT available on the server", "red")
                
        except json.JSONDecodeError:
            print(response.text)
        
        # If basic connection works, try info endpoint
        if response.status_code == 200:
            try:
                info_response = requests.get(f'{SERVER_URL}/info', timeout=5)
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    print_colored("\nServer information:", "blue")
                    print(json.dumps(info_data, indent=2))
                    
                    # Extract GPU info
                    if 'stats' in info_data and 'gpu_info' in info_data['stats']:
                        gpu_info = info_data['stats']['gpu_info']
                        if gpu_info['device_count'] > 0:
                            print_colored(f"\n✅ Found {gpu_info['device_count']} GPU(s):", "green")
                            for i, device in enumerate(gpu_info['devices']):
                                print_colored(f"   Device {i}: {device}", "green")
                        else:
                            print_colored("❌ No GPU devices found", "red")
            except Exception as e:
                print_colored(f"Error getting server info: {e}", "red")
        
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        print_colored("❌ Connection error: Could not connect to the server", "red")
        print_colored("Make sure the neural server is running on the GPU machine", "yellow")
        return False
    except Exception as e:
        print_colored(f"❌ Error: {e}", "red")
        return False

if __name__ == "__main__":
    success = test_server_connection()
    sys.exit(0 if success else 1)
