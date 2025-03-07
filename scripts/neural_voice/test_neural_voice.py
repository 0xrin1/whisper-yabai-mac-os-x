#!/usr/bin/env python3
"""
Neural Voice Test - Comprehensive testing tool for neural voice synthesis
Tests server connection, synthesis, and client integration
"""

import os
import sys
import json
import time
import logging
import argparse
import platform
import subprocess
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("neural-voice-test")

# ANSI color codes for terminal output
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
RED = '\033[31m'
RESET = '\033[0m'

# Default server URL - will be overridden by command line arg
SERVER_URL = os.environ.get("NEURAL_SERVER", "http://192.168.191.55:6000")

def print_color(text: str, color: str = GREEN) -> None:
    """Print colored text to the terminal."""
    colors = {
        'green': GREEN,
        'yellow': YELLOW,
        'blue': BLUE,
        'magenta': MAGENTA,
        'cyan': CYAN,
        'red': RED,
        'reset': RESET
    }
    print(f"{colors.get(color, color)}{text}{colors['reset']}")

def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 60)
    print_color(f" {title}", 'cyan')
    print("=" * 60)

def print_subsection(title: str) -> None:
    """Print a subsection header."""
    print("\n" + "-" * 50)
    print_color(f" {title}", 'magenta')
    print("-" * 50)

def test_server_connection() -> bool:
    """Test connection to the neural voice server."""
    print_subsection("Testing Neural Voice Server Connection")
    print(f"Server URL: {SERVER_URL}")
    
    try:
        # Import requests here to avoid hard dependency
        import requests
        
        # Test basic endpoint
        response = requests.get(f'{SERVER_URL}', timeout=5)
        status_color = 'green' if response.status_code == 200 else 'red'
        print_color(f"Status: {response.status_code}", status_color)
        
        # Pretty print the JSON response
        try:
            data = response.json()
            print_color("Server response:", 'blue')
            print(json.dumps(data, indent=2))
            
            # Check CUDA status
            if data.get('cuda') is True:
                print_color("✅ CUDA is available on the server", 'green')
            else:
                print_color("❌ CUDA is NOT available on the server", 'red')
                
        except json.JSONDecodeError:
            print(response.text)
        
        # If basic connection works, try info endpoint
        if response.status_code == 200:
            try:
                info_response = requests.get(f'{SERVER_URL}/info', timeout=5)
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    print_color("\nServer information:", 'blue')
                    print(json.dumps(info_data, indent=2))
                    
                    # Extract GPU info
                    if 'stats' in info_data and 'gpu_info' in info_data['stats']:
                        gpu_info = info_data['stats']['gpu_info']
                        if gpu_info['device_count'] > 0:
                            print_color(f"\n✅ Found {gpu_info['device_count']} GPU(s):", 'green')
                            for i, device in enumerate(gpu_info['devices']):
                                print_color(f"   Device {i}: {device}", 'green')
                        else:
                            print_color("❌ No GPU devices found", 'red')
            except Exception as e:
                print_color(f"Error getting server info: {e}", 'red')
        
        return response.status_code == 200
        
    except ImportError:
        print_color("❌ Requests module not installed. Cannot check server connection.", 'red')
        print_color("Install with: pip install requests", 'yellow')
        return False
    except Exception as e:
        print_color(f"❌ Error: {e}", 'red')
        return False

def test_synthesis_api_directly() -> bool:
    """Test the synthesis API directly without using the client library."""
    print_subsection("Testing Synthesis API Directly")
    
    try:
        import requests
        
        # Create a temp directory for test output
        os.makedirs('neural_test', exist_ok=True)
        
        # Generate unique filename for this test
        timestamp = int(time.time() * 1000)
        output_file = f"neural_test/speech_{timestamp}.wav"
        
        # Test text to synthesize
        test_text = "This is a direct test of the neural voice synthesis API."
        print(f"Synthesizing: \"{test_text}\"")
        
        # Send POST request to synthesize endpoint
        response = requests.post(
            f"{SERVER_URL}/synthesize",
            json={"text": test_text},
            timeout=10
        )
        
        if response.status_code == 200:
            # Save the audio
            with open(output_file, 'wb') as f:
                f.write(response.content)
                
            print_color(f"✅ Synthesis successful, audio saved to {output_file}", 'green')
            
            # Try to play the audio
            if platform.system() == "Darwin":
                print("Playing audio...")
                try:
                    subprocess.run(["afplay", output_file], check=True)
                    print_color("✅ Audio playback successful", 'green')
                except Exception as e:
                    print_color(f"⚠️ Audio playback failed: {e}", 'yellow')
            
            return True
        else:
            print_color(f"❌ Synthesis API call failed with status {response.status_code}", 'red')
            print(response.text)
            return False
    
    except ImportError:
        print_color("❌ Requests module not installed", 'red')
        return False
    except Exception as e:
        print_color(f"❌ Error in direct API test: {e}", 'red')
        return False

def test_client_library() -> bool:
    """Test the neural voice client library."""
    print_subsection("Testing Neural Voice Client Library")
    
    try:
        # Try to import the client module
        try:
            import sys
            # Add the src directory to path if needed
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
            from src.audio import neural_voice_client as client
            print_color("✅ Successfully imported neural_voice_client module", 'green')
        except ImportError as e:
            print_color(f"❌ Could not import neural_voice_client module: {e}", 'red')
            print_color("Make sure you're running from the project root directory", 'yellow')
            return False
        
        # Configure the client with the server URL
        print(f"Configuring client with server URL: {SERVER_URL}")
        if client.configure(SERVER_URL):
            print_color("✅ Client connected to server successfully", 'green')
        else:
            print_color("❌ Client failed to connect to server", 'red')
            return False
        
        # Get server info
        server_info = client.get_server_info()
        if server_info:
            print_color("Server information from client:", 'blue')
            print(json.dumps(server_info, indent=2))
        
        # Test speech synthesis
        test_text = "This is a test of the neural voice client library integration."
        print(f"Synthesizing: \"{test_text}\"")
        
        output_file = client.speak(test_text, play=True)
        
        if output_file:
            print_color(f"✅ Client synthesis successful, audio saved to {output_file}", 'green')
            return True
        else:
            print_color("❌ Client synthesis failed", 'red')
            return False
            
    except Exception as e:
        import traceback
        print_color(f"❌ Error testing client library: {e}", 'red')
        traceback.print_exc()
        return False

def display_voice_model_info() -> bool:
    """Display detailed information about the current voice model."""
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
        from src.audio import speech_synthesis as speech
        
        print_subsection("Active Voice Model Details")
        
        if not hasattr(speech, 'ACTIVE_VOICE_MODEL') or not speech.ACTIVE_VOICE_MODEL:
            print_color("No active voice model found.", 'yellow')
            return False
        
        model = speech.ACTIVE_VOICE_MODEL
        
        model_name = model.get("name", "Unknown")
        model_path = model.get("path", "Unknown")
        engine_type = model.get("engine", "parameter-based")
        sample_count = model.get("sample_count", 0)
        
        print(f"Model name: {model_name}")
        print(f"Model path: {model_path}")
        print(f"Engine type: {engine_type}")
        print(f"Sample count: {sample_count}")
        
        # Display voice profile if available
        if "voice_profile" in model:
            voice_profile = model["voice_profile"]
            print_subsection("Voice Profile Parameters")
            
            for key, value in voice_profile.items():
                if key in ["context_modifiers", "emotion_markers"] and isinstance(value, dict):
                    # Handle nested dictionaries
                    print(f"\n{key}:")
                    for subkey, subvalue in value.items():
                        print(f"  {subkey}: {subvalue}")
                else:
                    print(f"{key}: {value}")
        
        return True
        
    except ImportError as e:
        print_color(f"❌ Error importing speech synthesis module: {e}", 'red')
        return False
    except Exception as e:
        print_color(f"❌ Error displaying model info: {e}", 'red')
        return False

def run_comprehensive_test() -> Dict[str, bool]:
    """Run a comprehensive test of all neural voice components."""
    print_section("COMPREHENSIVE NEURAL VOICE SYSTEM TEST")
    
    results = {}
    
    # Test server connection
    print_color("Step 1: Testing server connection", 'cyan')
    results['server_connection'] = test_server_connection()
    
    # Test direct API synthesis
    if results['server_connection']:
        print_color("\nStep 2: Testing synthesis API directly", 'cyan')
        results['api_synthesis'] = test_synthesis_api_directly()
    else:
        print_color("\nSkipping API synthesis test due to server connection failure", 'yellow')
        results['api_synthesis'] = False
    
    # Test client library
    print_color("\nStep 3: Testing client library integration", 'cyan')
    results['client_library'] = test_client_library()
    
    # Show model info
    print_color("\nStep 4: Checking voice model information", 'cyan')
    results['model_info'] = display_voice_model_info()
    
    # Print summary
    print_section("Test Results Summary")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        color = "green" if result else "red"
        print_color(f"{test_name.replace('_', ' ').title()}: {status}", color)
    
    # Overall result
    if all(results.values()):
        print_color("\nAll tests passed successfully! The neural voice system is working correctly.", 'green')
    else:
        print_color("\nSome tests failed. See details above for troubleshooting.", 'yellow')
        
        # Provide troubleshooting advice
        if not results.get('server_connection', False):
            print_color("\nTroubleshooting server connection:", 'yellow')
            print("1. Make sure the neural voice server is running on the GPU server")
            print("2. Check that the server URL is correct (using: " + SERVER_URL + ")")
            print("3. Verify network connectivity to the GPU server")
            print("4. Try restarting the server with: ./scripts/gpu/manage_neural_server.sh restart")
    
    return results

def main():
    """Main entry point for the test script."""
    global SERVER_URL
    
    parser = argparse.ArgumentParser(description="Test neural voice synthesis capabilities")
    parser.add_argument("--server", default=SERVER_URL, help="Neural voice server URL")
    parser.add_argument("--server-only", action="store_true", help="Only test server connection")
    parser.add_argument("--api-only", action="store_true", help="Only test direct API synthesis")
    parser.add_argument("--client-only", action="store_true", help="Only test client library")
    parser.add_argument("--model-info", action="store_true", help="Only display voice model information")
    parser.add_argument("--text", type=str, help="Specific text to use for synthesis tests")
    args = parser.parse_args()
    
    # Update server URL from command line or environment
    if args.server:
        SERVER_URL = args.server
    
    # Determine which tests to run
    if args.server_only:
        test_server_connection()
    elif args.api_only:
        if test_server_connection():
            test_synthesis_api_directly()
    elif args.client_only:
        test_client_library()
    elif args.model_info:
        display_voice_model_info()
    else:
        # Run comprehensive test
        run_comprehensive_test()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_color("\nTest interrupted by user.", 'yellow')
        sys.exit(0)
    except Exception as e:
        print_color(f"\nUnexpected error: {e}", 'red')
        sys.exit(1)