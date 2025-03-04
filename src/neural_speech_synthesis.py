#!/usr/bin/env python3
"""
Neural speech synthesis module using GPU server for voice conversion.
This module builds on the standard speech_synthesis.py but adds neural voice support.
"""

import os
import sys
import subprocess
import threading
import time
import random
import json
import tempfile
import dotenv
from typing import Optional, List, Dict, Any
from src import speech_synthesis as speech

# Load environment variables
dotenv.load_dotenv()

# GPU Server settings
GPU_SERVER_HOST = os.getenv("GPU_SERVER_HOST", "")
GPU_SERVER_USER = os.getenv("GPU_SERVER_USER", "")
GPU_SERVER_PASSWORD = os.getenv("GPU_SERVER_PASSWORD", "")
GPU_SERVER_PORT = os.getenv("GPU_SERVER_PORT", "22")
USE_GPU_ACCELERATION = os.getenv("USE_GPU_ACCELERATION", "false").lower() == "true"

# Local paths
TEMP_DIR = "tmp"

# Track if synthesis is in progress
_synthesis_lock = threading.Lock()
_currently_synthesizing = False

def ensure_temp_dir():
    """Make sure the temporary directory exists."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

def run_ssh_command(command: str) -> str:
    """Run a command on the GPU server via SSH.
    
    Args:
        command: The command to run
        
    Returns:
        Command output
    """
    if not GPU_SERVER_HOST or not GPU_SERVER_USER or not GPU_SERVER_PASSWORD:
        raise ValueError("GPU server connection details not configured in .env file")
    
    ssh_command = [
        "sshpass", "-p", GPU_SERVER_PASSWORD,
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-p", GPU_SERVER_PORT,
        f"{GPU_SERVER_USER}@{GPU_SERVER_HOST}",
        command
    ]
    
    result = subprocess.run(ssh_command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"SSH Error: {result.stderr}")
        return ""
    
    return result.stdout

def scp_file_from_server(remote_path: str, local_path: str) -> bool:
    """Copy a file from the GPU server to the local machine.
    
    Args:
        remote_path: Path to the file on the remote server
        local_path: Local destination path
        
    Returns:
        Boolean indicating success
    """
    ensure_temp_dir()
    
    scp_command = [
        "sshpass", "-p", GPU_SERVER_PASSWORD,
        "scp", "-o", "StrictHostKeyChecking=no",
        "-P", GPU_SERVER_PORT,
        f"{GPU_SERVER_USER}@{GPU_SERVER_HOST}:{remote_path}",
        local_path
    ]
    
    result = subprocess.run(scp_command, capture_output=True, text=True)
    return result.returncode == 0

def convert_text_to_speech(text: str) -> str:
    """Convert text to speech using neural voice model on GPU server.
    
    Args:
        text: The text to convert to speech
        
    Returns:
        Path to the generated audio file
    """
    with _synthesis_lock:
        _currently_synthesizing = True
    
    try:
        # Generate a unique ID for this conversion
        unique_id = int(time.time())
        remote_output_path = f"~/neural_voice_model/output_{unique_id}.wav"
        local_output_path = os.path.join(TEMP_DIR, f"output_{unique_id}.wav")
        
        # Escape the text for passing in command
        escaped_text = text.replace('"', '\\"')
        
        # Run the voice conversion on the GPU server
        command = f'cd ~/neural_voice_model && python3 -c "import sys; sys.path.append(\'code\'); from voice_conversion import VoiceConverter; converter = VoiceConverter(); converter.add_voice_sample(\'samples/sample_20250304_194015.wav\'); converter.convert_text_to_speech(\'{escaped_text}\', \'{remote_output_path}\')"'
        
        print(f"Running neural speech synthesis: {text}")
        run_ssh_command(command)
        
        # Download the generated audio file
        if scp_file_from_server(remote_output_path, local_output_path):
            return local_output_path
        else:
            print("Failed to download generated speech file")
            return ""
    except Exception as e:
        print(f"Neural speech synthesis error: {e}")
        return ""
    finally:
        with _synthesis_lock:
            _currently_synthesizing = False

def speak(text: str, block: bool = False, rate: float = 1.0) -> None:
    """Speak the provided text using neural voice conversion.
    
    Args:
        text: The text to speak
        block: Whether to block until speech is complete
        rate: Speaking rate multiplier
    """
    if not text:
        return
    
    if not USE_GPU_ACCELERATION or not is_server_available():
        # Fall back to standard speech synthesis
        speech.speak(text, block=block)
        return
    
    # Use neural voice synthesis
    output_path = convert_text_to_speech(text)
    if output_path and os.path.exists(output_path):
        # Play the generated audio
        cmd = [
            "afplay",
            "-r", str(rate),
            output_path
        ]
        
        if block:
            subprocess.run(cmd, check=True)
        else:
            subprocess.Popen(cmd)
    else:
        # Fall back to standard speech synthesis
        speech.speak(text, block=block)

def is_server_available() -> bool:
    """Check if the GPU server is available.
    
    Returns:
        Boolean indicating if server is available
    """
    if not GPU_SERVER_HOST or not GPU_SERVER_USER or not GPU_SERVER_PASSWORD:
        return False
    
    try:
        result = run_ssh_command("echo 'Connection test'")
        return "Connection test" in result
    except Exception:
        return False

def is_synthesizing() -> bool:
    """Check if speech synthesis is in progress.
    
    Returns:
        Boolean indicating if synthesis is in progress
    """
    with _synthesis_lock:
        return _currently_synthesizing

def greeting(name: Optional[str] = None) -> None:
    """Speak a greeting."""
    if name:
        speak(f"Hello, {name}. How can I help you today?")
    else:
        speak(speech.get_random_response("greeting"))

def acknowledge() -> None:
    """Speak an acknowledgment phrase."""
    speak(speech.get_random_response("acknowledgment"))

def confirm() -> None:
    """Speak a confirmation phrase."""
    speak(speech.get_random_response("confirmation"))

def farewell() -> None:
    """Speak a farewell phrase."""
    speak(speech.get_random_response("farewell"))

def test_neural_voice():
    """Test the neural voice synthesis."""
    ensure_temp_dir()
    
    print("Testing neural voice synthesis...")
    if not is_server_available():
        print("GPU server is not available. Neural voice synthesis is disabled.")
        return
    
    test_phrases = [
        "Hello, I'm your neural voice assistant. How can I help you today?",
        "This voice model was created using your voice samples.",
        "The quick brown fox jumps over the lazy dog."
    ]
    
    for phrase in test_phrases:
        print(f"Speaking: {phrase}")
        speak(phrase, block=True)
        time.sleep(0.5)

if __name__ == "__main__":
    # Test the neural speech synthesis
    test_neural_voice()