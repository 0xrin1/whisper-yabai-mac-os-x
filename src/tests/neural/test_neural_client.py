#!/usr/bin/env python3
"""
Test script for neural voice client connectivity.
Tests the connection to the neural voice server and client library functionality.
"""
import os
import sys
import requests
import json
import argparse
from pathlib import Path

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, project_root)

# Server configuration - make global for proper scope
SERVER_URL = 'http://192.168.191.55:6000'

# Define a constant to avoid scope issues
DEFAULT_SERVER_URL = SERVER_URL

# Terminal colors
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_colored(text, color):
    """Print colored text to terminal."""
    colors = {
        'green': Colors.GREEN,
        'yellow': Colors.YELLOW,
        'red': Colors.RED,
        'blue': Colors.BLUE,
        'end': Colors.END
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def test_basic_connectivity():
    """Test basic HTTP connectivity to the server."""
    print_colored("\n=== Testing Basic HTTP Connectivity ===", "blue")
    print_colored(f"Server URL: {SERVER_URL}", "yellow")
    
    try:
        response = requests.get(SERVER_URL, timeout=5)
        print_colored(f"Status code: {response.status_code}", 
                     "green" if response.status_code == 200 else "red")
        
        try:
            data = response.json()
            print_colored("Server response:", "blue")
            print(json.dumps(data, indent=2))
            
            # Check CUDA status
            if data.get('cuda') is True:
                print_colored("✅ CUDA is available on the server", "green")
            else:
                print_colored("❌ CUDA is NOT available on the server", "red")
            
            return True
        except:
            print(response.text)
            return response.status_code == 200
            
    except requests.exceptions.ConnectionError:
        print_colored("❌ Connection error: Could not connect to the server", "red")
        print_colored("Make sure the neural server is running on the GPU machine", "yellow")
        return False
    except Exception as e:
        print_colored(f"❌ Error: {e}", "red")
        return False
        
def test_client_connection():
    """Test the neural_voice_client connection."""
    print_colored("\n=== Testing Neural Voice Client Connection ===", "blue")
    
    try:
        # Add project path
        base_path = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(base_path)
        
        # Import the neural_voice_client module
        from src.audio import neural_voice_client
        
        # Configure client
        neural_voice_client.server_url = SERVER_URL
        os.environ['NEURAL_SERVER'] = SERVER_URL
        
        print_colored(f"Neural client URL: {neural_voice_client.server_url}", "yellow")
        
        # Check connection
        connection_status = neural_voice_client.check_server_connection()
        
        if connection_status:
            print_colored("✅ Successfully connected to neural voice server", "green")
            
            # Display server info
            if hasattr(neural_voice_client, 'server_info') and neural_voice_client.server_info:
                server_info = neural_voice_client.server_info
                print_colored("Server information:", "blue")
                print(json.dumps(server_info, indent=2))
                
                # Check CUDA status
                if 'cuda' in server_info:
                    cuda_status = "✅ CUDA Enabled" if server_info['cuda'] else "❌ CUDA Disabled"
                    print_colored(f"CUDA Status: {cuda_status}", 
                                 "green" if server_info['cuda'] else "red")
                
                # Get more detailed info
                try:
                    print_colored("\nFetching detailed server info...", "blue")
                    response = requests.get(f"{SERVER_URL}/info", timeout=5)
                    if response.status_code == 200:
                        info_data = response.json()
                        print_colored("Detailed server information:", "blue")
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
                    print_colored(f"Error getting detailed info: {e}", "red")
            
            return True
        else:
            print_colored("❌ Failed to connect to neural voice server", "red")
            return False
            
    except ImportError as e:
        print_colored(f"❌ Import error: {e}", "red")
        print_colored("Make sure you're running from the project root directory", "yellow")
        return False
    except Exception as e:
        print_colored(f"❌ Error in client connection test: {e}", "red")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Test neural voice client connectivity')
    parser.add_argument('--server', default=DEFAULT_SERVER_URL, help='Neural server URL')
    args = parser.parse_args()
    
    # Update server URL if provided
    global SERVER_URL  # Now we need global as we're updating module-level var
    SERVER_URL = args.server
    
    print_colored("=== Neural Voice Client Connection Test ===", "blue")
    print_colored(f"Server: {SERVER_URL}", "yellow")
    
    # Run tests
    basic_success = test_basic_connectivity()
    client_success = test_client_connection()
    
    # Final summary
    print_colored("\n=== Test Summary ===", "blue")
    print_colored(f"Basic HTTP Connectivity: {'✅ PASSED' if basic_success else '❌ FAILED'}", 
                 "green" if basic_success else "red")
    print_colored(f"Neural Voice Client Connection: {'✅ PASSED' if client_success else '❌ FAILED'}", 
                 "green" if client_success else "red")
    
    if basic_success and client_success:
        print_colored("\n✅ All tests completed successfully!", "green")
        print_colored("The neural voice server is properly configured and accessible.", "green")
    else:
        print_colored("\n❌ Some tests failed", "red")
        print_colored("Please check the server configuration and connection.", "yellow")
    
    return 0 if (basic_success and client_success) else 1

if __name__ == "__main__":
    sys.exit(main())

