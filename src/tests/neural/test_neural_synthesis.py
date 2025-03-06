#!/usr/bin/env python3
"""
Test script for neural voice synthesis functionality.
Tests both direct API calls and the client library for GPU-accelerated speech synthesis.
"""
import os
import sys
import time
import requests
import argparse
import json
from pathlib import Path

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.insert(0, project_root)

# Server configuration - make global for proper scope
SERVER_URL = 'http://192.168.191.55:6000'
TEST_TEXT = 'This is a test of the neural voice synthesis endpoint with CUDA acceleration.'

# Define constants to avoid scope issues
DEFAULT_SERVER_URL = SERVER_URL
DEFAULT_TEST_TEXT = TEST_TEXT

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

def setup_directories():
    """Set up required directories for audio files."""
    # Create necessary directories
    directories = ["neural_cache", "tmp_neural_audio"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print_colored(f"✅ Directory ready: {directory}", "green")
    return True

def test_direct_synthesis(text=TEST_TEXT, play_audio=False):
    """Test the synthesize endpoint directly."""
    print_colored("\n=== Testing Direct Synthesis API ===", "blue")
    
    try:
        # Generate a unique filename
        timestamp = int(time.time() * 1000)
        output_file = f"neural_cache/speech_{timestamp}.wav"
        
        print_colored(f"Sending synthesis request to: {SERVER_URL}/synthesize", "blue")
        print_colored(f"Text: \"{text}\"", "yellow")
        
        # Make the request with a longer timeout since synthesis can take time
        start_time = time.time()
        response = requests.post(
            f'{SERVER_URL}/synthesize',
            json={'text': text},
            timeout=30  # Longer timeout for synthesis
        )
        end_time = time.time()
        
        print_colored(f"Response time: {end_time - start_time:.2f} seconds", "yellow")
        print_colored(f"Response status: {response.status_code}", 
                     "green" if response.status_code == 200 else "red")
        
        if response.status_code == 200:
            # Save audio to file
            with open(output_file, 'wb') as f:
                f.write(response.content)
                
            file_size = Path(output_file).stat().st_size / 1024  # KB
            print_colored(f"✅ Audio saved to {output_file} ({file_size:.2f} KB)", "green")
            
            # Play the audio if requested
            if play_audio and sys.platform == 'darwin':  # macOS
                os.system(f"afplay {output_file}")
                print_colored("🔈 Playing audio...", "blue")
            
            return True
        else:
            # Try to extract error message from response
            try:
                error_data = response.json()
                print_colored(f"❌ Error: {json.dumps(error_data, indent=2)}", "red")
            except:
                print_colored(f"❌ Error: {response.text}", "red")
            
            return False
            
    except requests.exceptions.ConnectionError:
        print_colored("❌ Connection error: Could not connect to the server", "red")
        print_colored("Make sure the neural server is running on the GPU machine", "yellow")
        return False
    except Exception as e:
        print_colored(f"❌ Error: {e}", "red")
        return False

def test_client_library(text=TEST_TEXT, play_audio=False):
    """Test synthesis using the neural_voice_client library."""
    print_colored("\n=== Testing Neural Voice Client Library ===", "blue")
    
    try:
        # Import the neural_voice_client module directly using our path setup
        from src.audio import neural_voice_client
        
        # Configure client
        neural_voice_client.server_url = SERVER_URL
        os.environ['NEURAL_SERVER'] = SERVER_URL
        
        # Check connection first
        print_colored("Checking server connection...", "blue")
        connection_status = neural_voice_client.check_server_connection()
        
        if not connection_status:
            print_colored("❌ Could not connect to the neural voice server", "red")
            return False
            
        print_colored("✅ Connected to neural voice server", "green")
        
        # If we have server info, display CUDA status
        if hasattr(neural_voice_client, 'server_info') and neural_voice_client.server_info:
            server_info = neural_voice_client.server_info
            if 'cuda' in server_info:
                cuda_status = "✅ CUDA Enabled" if server_info['cuda'] else "❌ CUDA Disabled"
                print_colored(f"CUDA Status: {cuda_status}", "green" if server_info['cuda'] else "red")
            
            if 'model' in server_info:
                print_colored(f"Model: {server_info['model']}", "blue")
        
        # Synthesize speech
        print_colored(f"Synthesizing text: \"{text}\"", "yellow")
        
        start_time = time.time()
        output_file = neural_voice_client.synthesize_speech(text)
        end_time = time.time()
        
        print_colored(f"Synthesis time: {end_time - start_time:.2f} seconds", "yellow")
        
        if output_file and os.path.exists(output_file):
            file_size = Path(output_file).stat().st_size / 1024  # KB
            print_colored(f"✅ Audio saved to {output_file} ({file_size:.2f} KB)", "green")
            
            # Play the audio if requested
            if play_audio and sys.platform == 'darwin':  # macOS
                os.system(f"afplay {output_file}")
                print_colored("🔈 Playing audio...", "blue")
                
            return True
        else:
            print_colored("❌ Failed to synthesize speech", "red")
            return False
            
    except ImportError as e:
        print_colored(f"❌ Import error: {e}", "red")
        print_colored("Make sure you're running from the project root directory", "yellow")
        return False
    except Exception as e:
        print_colored(f"❌ Error in client library test: {e}", "red")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Test neural voice synthesis')
    parser.add_argument('--text', default=DEFAULT_TEST_TEXT, help='Text to synthesize')
    parser.add_argument('--play', action='store_true', help='Play audio after synthesis')
    parser.add_argument('--client-only', action='store_true', help='Only test the client library')
    parser.add_argument('--direct-only', action='store_true', help='Only test direct API calls')
    parser.add_argument('--server', default=DEFAULT_SERVER_URL, help='Neural server URL')
    args = parser.parse_args()
    
    # Update global variables with provided values
    global SERVER_URL, TEST_TEXT  # Now we need global as we're updating module-level vars
    SERVER_URL = args.server
    TEST_TEXT = args.text
    
    print_colored("=== Neural Voice Synthesis Test ===", "blue")
    print_colored(f"Server: {SERVER_URL}", "yellow")
    
    # Set up directories
    setup_directories()
    
    success = True
    
    # Run tests based on flags
    if not args.client_only:
        direct_success = test_direct_synthesis(args.text, args.play)
        success = success and direct_success
    
    if not args.direct_only:
        client_success = test_client_library(args.text, args.play)
        success = success and client_success
    
    if success:
        print_colored("\n✅ All tests completed successfully!", "green")
    else:
        print_colored("\n❌ Some tests failed", "red")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

