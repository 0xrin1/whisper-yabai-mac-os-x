#!/usr/bin/env python3
"""
Speech synthesis module for the voice control system.
Provides natural-sounding TTS capabilities using macOS's native voices.
"""

import os
import subprocess
import threading
import time
import random
from typing import Optional, List, Dict

# Available high-quality macOS voices
AVAILABLE_VOICES = {
    "samantha": {"gender": "female", "accent": "american", "personality": "friendly"},
    "daniel": {"gender": "male", "accent": "british", "personality": "professional"},
    "karen": {"gender": "female", "accent": "australian", "personality": "warm"},
    "alex": {"gender": "male", "accent": "american", "personality": "natural"},
    "allison": {"gender": "female", "accent": "american", "personality": "professional"}
}

# Default voice to use
DEFAULT_VOICE = "samantha"

# Speaking rate (words per minute)
DEFAULT_RATE = 180

# Track if speech is currently in progress
_speaking_lock = threading.Lock()
_currently_speaking = False

# Queue for speech requests to prevent overlapping
_speech_queue = []
_queue_lock = threading.Lock()
_queue_thread = None
_queue_running = False

# Casual responses for common interactions
CASUAL_RESPONSES = {
    "greeting": [
        "Hello there.", 
        "Hi, how can I help?", 
        "Hello. What can I do for you?",
        "Hey there. I'm listening."
    ],
    "acknowledgment": [
        "Got it.",
        "I'm on it.",
        "Working on that now.",
        "Right away.",
        "Consider it done."
    ],
    "confirmation": [
        "That's done.",
        "I've completed that task.",
        "All finished.",
        "Task complete."
    ],
    "thinking": [
        "Let me think about that...",
        "Processing...",
        "Working on it...",
        "Give me a moment...",
        "Analyzing your request..."
    ],
    "uncertainty": [
        "I'm not sure about that.",
        "I didn't quite catch that.",
        "Could you rephrase that?",
        "I'm not sure how to help with that."
    ],
    "farewell": [
        "Goodbye for now.",
        "Signing off.",
        "Let me know if you need anything else.",
        "I'll be here if you need me."
    ]
}

def get_random_response(category: str) -> str:
    """Get a random response from a specific category.
    
    Args:
        category: The category of response to get
        
    Returns:
        A random response string
    """
    if category in CASUAL_RESPONSES:
        return random.choice(CASUAL_RESPONSES[category])
    return "I'm listening."

def speak(text: str, voice: str = DEFAULT_VOICE, rate: int = DEFAULT_RATE, 
          block: bool = False, volume: float = 1.0) -> None:
    """
    Speak the provided text using macOS TTS.
    
    Args:
        text: The text to speak
        voice: The voice to use
        rate: The speaking rate (words per minute)
        block: Whether to block until speech is complete
        volume: Volume level (0.0 to 1.0)
    """
    if not text:
        return
        
    # Sanitize input
    text = text.replace('"', '\\"')
    voice = voice.lower()
    
    # Ensure voice is valid
    if voice not in AVAILABLE_VOICES:
        voice = DEFAULT_VOICE
    
    # Normalize volume (0.0 to 1.0)
    volume = max(0.0, min(1.0, volume))
    
    # Add to queue
    with _queue_lock:
        _speech_queue.append({
            "text": text,
            "voice": voice,
            "rate": rate,
            "volume": volume
        })
        
    # Start queue processor if not already running
    _ensure_queue_processor_running()
    
    # If blocking mode requested, wait until this specific text is spoken
    if block:
        # Wait until our text is no longer in the queue and not currently speaking
        while True:
            with _queue_lock:
                text_in_queue = any(item["text"] == text for item in _speech_queue)
            
            with _speaking_lock:
                is_speaking = _currently_speaking
                
            if not text_in_queue and not is_speaking:
                break
                
            time.sleep(0.1)

def _speak_now(text: str, voice: str = DEFAULT_VOICE, rate: int = DEFAULT_RATE, 
               volume: float = 1.0) -> None:
    """
    Actually execute the TTS command (internal use).
    
    Args:
        text: The text to speak
        voice: The voice to use
        rate: The speaking rate
        volume: Volume level (0.0 to 1.0)
    """
    try:
        with _speaking_lock:
            _currently_speaking = True
            
        # macOS 'say' command with voice and rate parameters
        cmd = [
            "say", 
            "-v", voice,
            "-r", str(rate)
        ]
        
        # Add volume parameter if not default
        if volume != 1.0:
            # macOS say uses 0-100 for volume
            cmd.extend(["-v", str(int(volume * 100))])
            
        cmd.append(text)
        
        # Execute the command
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
    except Exception as e:
        print(f"TTS Error: {e}")
    finally:
        with _speaking_lock:
            _currently_speaking = False

def _process_speech_queue() -> None:
    """Process the speech queue in a separate thread."""
    global _queue_running
    
    _queue_running = True
    
    try:
        while True:
            # Get the next item from the queue
            with _queue_lock:
                if not _speech_queue:
                    _queue_running = False
                    break
                    
                item = _speech_queue.pop(0)
            
            # Speak the text
            _speak_now(
                item["text"],
                item["voice"],
                item["rate"],
                item["volume"]
            )
            
            # Small delay between queue items
            time.sleep(0.2)
    except Exception as e:
        print(f"Queue processor error: {e}")
        _queue_running = False

def _ensure_queue_processor_running() -> None:
    """Ensure the queue processor thread is running."""
    global _queue_thread, _queue_running
    
    if not _queue_running:
        _queue_thread = threading.Thread(target=_process_speech_queue, daemon=True)
        _queue_thread.start()

def stop_speaking() -> None:
    """Stop all speech immediately."""
    # Clear the queue
    with _queue_lock:
        _speech_queue.clear()
    
    # Kill any running say processes
    try:
        subprocess.run(["killall", "-9", "say"], check=False)
    except Exception:
        pass
        
    # Reset speaking state
    with _speaking_lock:
        _currently_speaking = False

def list_available_voices() -> Dict[str, Dict]:
    """Return a dictionary of available voices with their characteristics."""
    return AVAILABLE_VOICES

def get_voice_info(voice: str) -> Dict:
    """Get information about a specific voice.
    
    Args:
        voice: The voice name
        
    Returns:
        Dictionary with voice characteristics or None if voice doesn't exist
    """
    voice = voice.lower()
    return AVAILABLE_VOICES.get(voice, None)

def is_speaking() -> bool:
    """Check if the system is currently speaking.
    
    Returns:
        True if speaking, False otherwise
    """
    with _speaking_lock:
        return _currently_speaking

def greeting(name: Optional[str] = None) -> None:
    """Speak a greeting.
    
    Args:
        name: Optional name to personalize the greeting
    """
    if name:
        speak(f"Hello, {name}. How can I help you today?")
    else:
        speak(get_random_response("greeting"))

def acknowledge() -> None:
    """Speak an acknowledgment phrase."""
    speak(get_random_response("acknowledgment"))

def confirm() -> None:
    """Speak a confirmation phrase."""
    speak(get_random_response("confirmation"))

def thinking() -> None:
    """Indicate that the system is thinking."""
    speak(get_random_response("thinking"))

def farewell() -> None:
    """Speak a farewell phrase."""
    speak(get_random_response("farewell"))

# Test function
def test_voices():
    """Test all available voices with a sample phrase."""
    sample_text = "Hello, I'm your voice assistant. How can I help you today?"
    
    print("Testing available voices:")
    for voice in AVAILABLE_VOICES:
        print(f"Speaking with voice: {voice}")
        speak(f"This is the {voice} voice. {sample_text}", voice=voice, block=True)
        time.sleep(0.5)

if __name__ == "__main__":
    # Test the speech synthesis functionality
    test_voices()