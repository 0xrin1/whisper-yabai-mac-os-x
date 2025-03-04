#!/usr/bin/env python3
"""
Speech synthesis module for the voice control system.
Provides natural-sounding TTS capabilities using macOS's native voices or custom voice models.
Supports custom voice models created from your own voice samples.
"""

import os
import subprocess
import threading
import time
import random
import json
from typing import Optional, List, Dict, Any

# Available high-quality macOS voices
AVAILABLE_VOICES = {
    "samantha": {"gender": "female", "accent": "american", "personality": "friendly"},
    "daniel": {"gender": "male", "accent": "british", "personality": "professional"},
    "karen": {"gender": "female", "accent": "australian", "personality": "warm"}
    # Note: alex and allison voices were removed as they aren't available on all macOS versions
}

# Default voice to use
DEFAULT_VOICE = "daniel"  # Use Daniel as default for JARVIS-like experience

# Speaking rate (words per minute)
DEFAULT_RATE = 180

# Custom voice models
VOICE_MODELS_DIR = "voice_models"
CUSTOM_VOICE_MODE = True  # Set to False to disable custom voice model support
ACTIVE_VOICE_MODEL = None  # Will be loaded if available

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

def load_voice_model() -> Optional[Dict[str, Any]]:
    """Load the active custom voice model if available.
    
    Returns:
        Dictionary with voice model information or None if not available
    """
    if not CUSTOM_VOICE_MODE:
        return None
        
    # Check for active model config
    active_model_path = os.path.join(VOICE_MODELS_DIR, "active_model.json")
    if not os.path.exists(active_model_path):
        return None
        
    try:
        with open(active_model_path, 'r') as f:
            active_model_config = json.load(f)
            
        model_name = active_model_config.get("active_model")
        model_path = active_model_config.get("path")
        
        if not model_name or not model_path or not os.path.exists(model_path):
            return None
            
        # Load metadata
        metadata_path = os.path.join(model_path, "metadata.json")
        if not os.path.exists(metadata_path):
            return None
            
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            
        # Add path information
        metadata["path"] = model_path
        return metadata
    except Exception as e:
        print(f"Error loading voice model: {e}")
        return None

# Try to load active voice model at module initialization
ACTIVE_VOICE_MODEL = load_voice_model()
print(f"Custom voice model: {'Loaded' if ACTIVE_VOICE_MODEL else 'Not available'}")

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

def _speak_with_custom_voice(text: str, rate: int = DEFAULT_RATE, volume: float = 1.0) -> bool:
    """Use custom voice model for speech.
    
    Args:
        text: The text to speak
        rate: The speaking rate
        volume: Volume level (0.0 to 1.0)
    
    Returns:
        Boolean indicating success
    """
    if not ACTIVE_VOICE_MODEL:
        return False
        
    try:
        model_path = ACTIVE_VOICE_MODEL.get("path")
        model_name = ACTIVE_VOICE_MODEL.get("name")
        sample_count = ACTIVE_VOICE_MODEL.get("sample_count", 0)
        
        if not model_path or not model_name:
            return False
            
        # For custom voice synthesis, we experiment with different voice parameters
        # to find the best match for the user's voice
        
        # Create temp directory for enhanced voice processing
        temp_dir = os.path.join(model_path, "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Try different high-quality voices as the base
        # based on the first sample in the user's model
        
        # Determine best base voice from sample names
        samples = ACTIVE_VOICE_MODEL.get("samples", [])
        
        # Get voice profile from model metadata
        voice_profile = ACTIVE_VOICE_MODEL.get("voice_profile", {})
        
        # Set default parameters (in case there's no voice profile)
        base_voice = "Alex"  # Default
        pitch_modifier = 0.95  # Default
        speaking_rate_modifier = 1.0  # Default
        
        # If we have a voice profile, use its parameters
        if voice_profile:
            # Use recommended voice settings from the profile
            base_voice = voice_profile.get("base_voice", "Daniel")
            pitch_modifier = voice_profile.get("pitch_modifier", 0.97)
            speaking_rate_modifier = voice_profile.get("speaking_rate", 1.0)
            # Additional parameters could be used here if available
        elif sample_count > 0 and model_name == "user_voice":
            # Fallback if no voice profile but we have samples
            if sample_count > 30:
                # With many samples, we have better information about the voice
                base_voice = "Samantha"  # Female base voice
                pitch_modifier = 0.92    # Deeper tone for more unique sound
            else:
                # With fewer samples, use more subtle adjustments
                base_voice = "Daniel"    # Male base voice
                pitch_modifier = 0.97    # Slight pitch adjustment
                
        # Make the voice sound more like your voice based on training samples
        # Use different base voices for different types of phrases
        if "?" in text:
            # Questions use slightly higher pitch
            temp_pitch = pitch_modifier * 1.03
        elif "!" in text:
            # Exclamations use more energy
            temp_pitch = pitch_modifier * 0.98
            volume *= 1.15  # Increase volume slightly
        else:
            # Normal statements
            temp_pitch = pitch_modifier
            
        # Create unique temp file for this speech
        unique_id = int(time.time() * 1000)
        temp_audio = os.path.join(temp_dir, f"voice_{unique_id}.aiff")
        
        # Generate speech with macOS high-quality voice
        # Apply speaking rate modifier to the rate parameter
        adjusted_rate = int(rate * speaking_rate_modifier)
        
        base_cmd = [
            "say",
            "-v", base_voice,
            "-r", str(adjusted_rate),
            "-o", temp_audio,
            text
        ]
        
        subprocess.run(base_cmd, check=True, capture_output=True, text=True)
        
        # Play with customized parameters
        play_cmd = [
            "afplay",
            "-v", str(volume),
            "-r", str(temp_pitch),  # Adjusted pitch to sound more like user's voice
            temp_audio
        ]
        
        subprocess.run(play_cmd, check=True)
        
        # Clean up
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
            
        return True
    except Exception as e:
        print(f"Custom voice error: {e}")
        return False


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
            
        # Try custom voice model first if enabled
        if CUSTOM_VOICE_MODE and ACTIVE_VOICE_MODEL:
            if _speak_with_custom_voice(text, rate, volume):
                return
                
        # Fall back to standard macOS 'say' command with voice and rate parameters
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
    
    # Test custom voice if available
    if CUSTOM_VOICE_MODE and ACTIVE_VOICE_MODEL:
        model_name = ACTIVE_VOICE_MODEL.get("name", "Custom")
        print(f"Speaking with custom voice model: {model_name}")
        speak(f"This is your custom voice model. {sample_text}", block=True)
        time.sleep(0.5)
    
    # Test standard voices
    for voice in AVAILABLE_VOICES:
        print(f"Speaking with voice: {voice}")
        speak(f"This is the {voice} voice. {sample_text}", voice=voice, block=True)
        time.sleep(0.5)

def reload_voice_model():
    """Reload the active voice model (useful if a new model was just created)."""
    global ACTIVE_VOICE_MODEL
    ACTIVE_VOICE_MODEL = load_voice_model()
    return ACTIVE_VOICE_MODEL is not None

if __name__ == "__main__":
    # Test the speech synthesis functionality
    test_voices()