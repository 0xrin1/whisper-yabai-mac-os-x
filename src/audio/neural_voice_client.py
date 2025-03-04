#!/usr/bin/env python3
"""
Neural Voice Client - Connects to GPU-powered voice server
Enables high-quality neural voice synthesis on lightweight clients
"""

import os
import sys
import json
import time
import logging
import threading
import tempfile
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("neural-voice-client")

# Try to import required libraries
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.error("Requests library not available. Install with: pip install requests")

# Default settings
DEFAULT_SERVER = os.environ.get("NEURAL_SERVER", "http://localhost:5001")
TEMP_DIR = "tmp_neural_audio"
CACHE_DIR = "neural_cache"
MAX_CACHE_SIZE = 100  # Maximum number of cached audio files
CONNECTION_TIMEOUT = 2.0  # Server connection timeout in seconds

# Global state
server_url = DEFAULT_SERVER
cache = {}  # text -> file path
cache_lock = threading.Lock()
fallback_enabled = False  # Fallback is now disabled
last_connection_time = 0
connection_status = "unknown"  # "unknown", "connected", "disconnected"
last_connection_attempt = 0
connection_cooldown = 5.0  # Seconds to wait between connection attempts
server_info = None

def configure(server: str = DEFAULT_SERVER, enable_fallback: bool = False):
    """Configure the neural voice client.
    
    Args:
        server: URL of the neural voice server (including protocol and port)
        enable_fallback: Whether to enable fallback to local TTS if server is unavailable
                        (Kept for backward compatibility but defaults to False and is ignored)
    """
    global server_url, fallback_enabled, connection_status
    
    server_url = server
    fallback_enabled = False  # Always disable fallback regardless of parameter
    connection_status = "unknown"
    
    # Create cache directory
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Test connection
    check_server_connection()
    
    return connection_status == "connected"

def check_server_connection():
    """Check if the neural voice server is available.
    
    Returns:
        Boolean indicating if server is available
    """
    global connection_status, last_connection_time, server_info, last_connection_attempt
    
    # Throttle connection attempts
    current_time = time.time()
    if current_time - last_connection_attempt < connection_cooldown:
        return connection_status == "connected"
        
    last_connection_attempt = current_time
    
    if not REQUESTS_AVAILABLE:
        connection_status = "disconnected"
        return False
        
    try:
        # Test connection to server
        response = requests.get(f"{server_url}/info", timeout=CONNECTION_TIMEOUT)
        
        if response.status_code == 200:
            connection_status = "connected"
            last_connection_time = current_time
            server_info = response.json()
            logger.info(f"Connected to neural voice server: {server_url}")
            logger.info(f"Server model: {server_info.get('model', {}).get('name', 'unknown')}")
            logger.info(f"CUDA available: {server_info.get('stats', {}).get('cuda_available', False)}")
            return True
        else:
            connection_status = "disconnected"
            server_info = None
            logger.error(f"Failed to connect to neural voice server: HTTP {response.status_code}. Neural voice is required for this feature.")
            return False
            
    except requests.exceptions.RequestException as e:
        connection_status = "disconnected"
        server_info = None
        logger.error(f"Failed to connect to neural voice server: {e}. Neural voice is required for this feature.")
        return False

def synthesize_speech(text: str) -> Optional[str]:
    """Synthesize speech using the neural voice server.
    
    Args:
        text: Text to synthesize
        
    Returns:
        Path to output audio file or None if failed
    """
    if not text:
        return None
        
    # Check if server is available
    if connection_status != "connected":
        if time.time() - last_connection_attempt > connection_cooldown:
            check_server_connection()
            
    if connection_status != "connected":
        logger.error("Neural voice server not available. Connection required for neural voice synthesis.")
        return None
            
    # Check cache
    with cache_lock:
        cache_key = f"{text}_{server_url.replace('://', '_').replace(':', '_').replace('/', '_')}"
        if cache_key in cache and os.path.exists(cache[cache_key]):
            logger.info(f"Using cached audio for: {text[:30]}...")
            return cache[cache_key]
    
    if not REQUESTS_AVAILABLE:
        logger.error("Requests library not available. Required for neural voice synthesis.")
        return None
        
    try:
        # Generate unique filename
        timestamp = int(time.time() * 1000)
        rand_id = os.urandom(4).hex()
        output_file = os.path.join(CACHE_DIR, f"speech_{timestamp}_{rand_id}.wav")
        
        # Send request to server
        response = requests.post(
            f"{server_url}/synthesize",
            json={"text": text},
            timeout=10.0
        )
        
        if response.status_code != 200:
            logger.error(f"Neural voice server error: {response.status_code}")
            return None
            
        # Save audio to file
        with open(output_file, 'wb') as f:
            f.write(response.content)
            
        # Add to cache
        with cache_lock:
            # Manage cache size
            if len(cache) >= MAX_CACHE_SIZE:
                # Remove oldest item
                oldest_key = next(iter(cache))
                oldest_file = cache[oldest_key]
                if os.path.exists(oldest_file):
                    os.remove(oldest_file)
                del cache[oldest_key]
                
            # Add new item to cache
            cache[cache_key] = output_file
            
        return output_file
        
    except Exception as e:
        logger.error(f"Error synthesizing speech with neural voice: {e}")
        return None


def play_audio(file_path: str) -> bool:
    """Play an audio file.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Boolean indicating success
    """
    if not file_path or not os.path.exists(file_path):
        return False
        
    try:
        # Use platform-specific commands to play audio
        if sys.platform == "darwin":  # macOS
            cmd = ["afplay", file_path]
        elif sys.platform.startswith("linux"):  # Linux
            cmd = ["aplay", file_path]
        elif sys.platform == "win32":  # Windows
            cmd = ["powershell", "-c", f"(New-Object Media.SoundPlayer '{file_path}').PlaySync();"]
        else:
            logger.error(f"Unsupported platform: {sys.platform}")
            return False
            
        subprocess.run(cmd, check=True)
        return True
        
    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        return False

def speak(text: str, play: bool = True) -> Optional[str]:
    """Synthesize speech and optionally play it.
    
    Args:
        text: Text to speak
        play: Whether to play the audio
        
    Returns:
        Path to audio file or None if failed
    """
    output_file = synthesize_speech(text)
    
    if output_file and play:
        play_audio(output_file)
        
    return output_file

def get_server_info() -> Optional[Dict[str, Any]]:
    """Get information about the neural voice server.
    
    Returns:
        Server information or None if not connected
    """
    if connection_status != "connected":
        check_server_connection()
        
    return server_info

def cleanup():
    """Clean up temporary files."""
    try:
        # Clean up cache directory
        if os.path.exists(CACHE_DIR):
            files = [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) 
                    if os.path.isfile(os.path.join(CACHE_DIR, f))]
            
            # Sort by modification time (oldest first)
            files.sort(key=lambda x: os.path.getmtime(x))
            
            # Keep only the most recent MAX_CACHE_SIZE files
            files_to_delete = files[:-MAX_CACHE_SIZE] if len(files) > MAX_CACHE_SIZE else []
            
            # Delete old files
            for file in files_to_delete:
                try:
                    os.remove(file)
                except:
                    pass
                    
        # Clean up temp directory
        if os.path.exists(TEMP_DIR):
            for file in os.listdir(TEMP_DIR):
                try:
                    file_path = os.path.join(TEMP_DIR, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except:
                    pass
    except Exception as e:
        logger.error(f"Error cleaning up: {e}")

# Run cleanup when the module is unloaded
import atexit
atexit.register(cleanup)

# Initialize with default settings
configure()

if __name__ == "__main__":
    # Simple CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Neural Voice Client")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Neural voice server URL")
    parser.add_argument("--text", help="Text to synthesize")
    
    args = parser.parse_args()
    
    if args.server:
        configure(args.server)
        
    if args.text:
        print(f"Synthesizing: {args.text}")
        output_file = speak(args.text)
        if output_file:
            print(f"Audio saved to: {output_file}")
        else:
            print("Failed to synthesize speech")
    else:
        server_info = get_server_info()
        if server_info:
            import json
            print(json.dumps(server_info, indent=2))
        else:
            print(f"Not connected to server: {args.server}")
            print("Run with --text 'your text' to test speech synthesis")