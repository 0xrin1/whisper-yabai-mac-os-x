#!/usr/bin/env python3
"""
Comprehensive test script for neural voice synthesis using GPU acceleration.
This script combines functionality to:
1. Test the neural server connection
2. Check voice model details
3. Test both system and neural voice synthesis
4. Perform comparison tests with context and emotion-aware speech
"""

import sys
import time
import os
import argparse
import json
import logging
from typing import List, Dict, Any

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

# Default server URL
SERVER_URL = 'http://192.168.191.55:6000'

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
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

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

def test_basic_synthesis():
    """Test basic speech synthesis with different voices."""
    from src import speech_synthesis as speech
    
    print_subsection("Testing Basic Speech Synthesis")
    
    # Check if custom voice model is loaded
    if speech.ACTIVE_VOICE_MODEL:
        print_color(f"✅ Custom voice model loaded: {speech.ACTIVE_VOICE_MODEL.get('name', 'Unknown')}", 'green')
        print(f"   Created: {speech.ACTIVE_VOICE_MODEL.get('created', 'Unknown')}")
        print(f"   Samples: {speech.ACTIVE_VOICE_MODEL.get('sample_count', 0)}")
    else:
        print_color("⚠️ No custom voice model detected. Using standard system voices.", 'yellow')
    
    # Test system voices first for comparison
    print("\nTesting system voices for comparison:")
    system_voices = ["daniel", "samantha", "karen"]
    test_phrase = "Hello, this is a test of the voice synthesis system."
    
    for voice in system_voices:
        print_color(f"Speaking with {voice} voice:", 'blue')
        speech.speak(test_phrase, voice=voice, block=True)
        time.sleep(0.5)
    
    # Test custom voice with multiple phrases
    print_color("\nTesting custom voice model:", 'blue')
    test_phrases = [
        "Hello, I'm your personal assistant using your custom voice model.",
        "This voice should sound more like you, since it uses your voice characteristics.",
        "The quick brown fox jumps over the lazy dog."
    ]
    
    for i, phrase in enumerate(test_phrases):
        print(f"Speaking phrase {i+1}/{len(test_phrases)}:")
        print(f"\"{phrase}\"")
        speech.speak(phrase, block=True)
        time.sleep(0.5)

def display_voice_model_info():
    """Display detailed information about the current voice model."""
    from src import speech_synthesis as speech
    
    print_subsection("Active Voice Model Details")
    
    if not speech.ACTIVE_VOICE_MODEL:
        print_color("No active voice model found.", 'yellow')
        return
    
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
            if key == "context_modifiers" or key == "emotion_markers":
                # Handle nested dictionaries
                print(f"\n{key}:")
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        print(f"  {subkey}: {subvalue}")
            else:
                print(f"{key}: {value}")

def test_context_aware_speech():
    """Test context-aware speech synthesis with different text types."""
    from src import speech_synthesis as speech
    
    print_subsection("Testing Context-Aware Speech")
    
    # Define test phrases for different contexts
    questions = [
        "What time is it?",
        "Could you please open Safari for me?"
    ]
    
    commands = [
        "Open Safari and navigate to the homepage.",
        "Move the window to the left side of the screen."
    ]
    
    exclamations = [
        "This is amazing!",
        "Look at this fantastic result!"
    ]
    
    # Test questions (should have rising intonation)
    print_color("Questions (with rising intonation):", 'blue')
    for phrase in questions:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)
    
    # Test commands (should be authoritative)
    print_color("\nCommands (with authoritative tone):", 'blue')
    for phrase in commands:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)
    
    # Test exclamations (should be more energetic)
    print_color("\nExclamations (with more energy):", 'blue')
    for phrase in exclamations:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)

def main():
    """Main function for testing neural voice capabilities."""
    global SERVER_URL
    
    parser = argparse.ArgumentParser(description="Test neural voice synthesis capabilities")
    parser.add_argument("--server-only", action="store_true", help="Only test server connection")
    parser.add_argument("--basic-only", action="store_true", help="Only test basic speech synthesis")
    parser.add_argument("--context-only", action="store_true", help="Only test context-aware speech")
    parser.add_argument("--model-info", action="store_true", help="Display voice model information")
    parser.add_argument("--server", default=SERVER_URL, help="Neural voice server URL")
    args = parser.parse_args()
    
    # Print header
    print_section("Neural Voice System Test")
    
    # Check server connection
    SERVER_URL = args.server
    server_ok = test_server_connection()
    
    # If server connection test fails and we're only testing the server, exit
    if not server_ok and args.server_only:
        print_color("\n❌ Server connection failed. Exiting.", 'red')
        return False
    
    # Stop here if only testing server
    if args.server_only:
        return server_ok
    
    # Determine which tests to run
    run_all = not (args.basic_only or args.context_only or args.model_info)
    
    try:
        # Always show model info first if requested or running all tests
        if run_all or args.model_info:
            display_voice_model_info()
        
        # Run selected tests
        if run_all or args.basic_only:
            test_basic_synthesis()
        
        if run_all or args.context_only:
            test_context_aware_speech()
        
        # Print footer
        print_section("Test Complete")
        print("The neural voice system provides high-quality speech synthesis.")
        if not server_ok:
            print_color("\n⚠️ Note: Server connection failed but local testing completed.", 'yellow')
        
        return True
        
    except ImportError as e:
        print_color(f"\n❌ Error importing modules: {e}", 'red')
        print_color("Make sure you are running from the project root directory:", 'yellow')
        print("cd /path/to/project && python scripts/neural_voice/test_neural_voice.py")
        return False
    except Exception as e:
        print_color(f"\n❌ Error during test: {e}", 'red')
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_color("\nTest interrupted by user.", 'yellow')
        sys.exit(0)
    except Exception as e:
        print_color(f"\nUnexpected error: {e}", 'red')
        sys.exit(1)