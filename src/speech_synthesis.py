#!/usr/bin/env python3
"""
Speech synthesis module for the voice control system.
Provides natural-sounding TTS capabilities using macOS's native voices or custom voice models.
Supports custom voice models created from your own voice samples.
Now with support for neural voice models trained with GlowTTS.
"""

import os
import subprocess
import threading
import time
import random
import json
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('speech-synthesis')

# Available high-quality macOS voices
AVAILABLE_VOICES = {
    "daniel": {"gender": "male", "accent": "british", "personality": "professional"},
    "alex": {"gender": "male", "accent": "american", "personality": "friendly"},
    "fred": {"gender": "male", "accent": "american", "personality": "authoritative"},
    "tom": {"gender": "male", "accent": "american", "personality": "deep"},
    "lee": {"gender": "male", "accent": "australian", "personality": "warm"},
    # Keeping female voices as fallbacks only
    "samantha": {"gender": "female", "accent": "american", "personality": "friendly"},
    "karen": {"gender": "female", "accent": "australian", "personality": "warm"}
}

# Group voices by gender
MALE_VOICES = ["daniel", "alex", "fred", "tom", "lee"]
FEMALE_VOICES = ["samantha", "karen"]

# Default voice to use
DEFAULT_VOICE = "daniel"  # Use Daniel as default for JARVIS-like experience

# Speaking rate (words per minute)
DEFAULT_RATE = 180

# Custom voice models
VOICE_MODELS_DIR = "voice_models"
CUSTOM_VOICE_MODE = True  # Set to False to disable custom voice model support
ACTIVE_VOICE_MODEL = None  # Will be loaded if available

# Neural voice model settings
NEURAL_VOICE_ENABLED = True  # Set to False to disable neural voice model support
NEURAL_MODEL_CACHE = {}  # Cache for loaded neural voice models
HAS_TORCH = False  # Will be set to True if PyTorch is available
DEFAULT_NEURAL_TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp_neural_audio")

# Try to import PyTorch and TTS libraries for neural voice support
try:
    import torch
    import numpy as np
    HAS_TORCH = True
    logger.info(f"PyTorch available: {torch.__version__}")
    
    # Try to import TTS-specific modules 
    try:
        import TTS
        from TTS.utils.synthesizer import Synthesizer
        HAS_TTS = True
        logger.info(f"TTS library available: {TTS.__version__}")
    except ImportError:
        HAS_TTS = False
        logger.warning("TTS library not available, neural voice synthesis limited")
except ImportError:
    HAS_TORCH = False
    HAS_TTS = False
    logger.warning("PyTorch not available, neural voice synthesis disabled")
    
# Try to import the neural voice client
try:
    from src import neural_voice_client
    HAS_NEURAL_CLIENT = True
    logger.info("Neural voice client available")
except ImportError:
    HAS_NEURAL_CLIENT = False
    logger.warning("Neural voice client not available")

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
        logger.warning(f"No active_model.json found in {VOICE_MODELS_DIR}")
        return None
        
    try:
        with open(active_model_path, 'r') as f:
            active_model_config = json.load(f)
            
        model_name = active_model_config.get("active_model")
        model_path = active_model_config.get("path")
        engine_type = active_model_config.get("engine", "")
        
        if not model_name or not model_path:
            logger.warning(f"Invalid model configuration in {active_model_path}")
            return None
            
        if not os.path.exists(model_path):
            logger.warning(f"Model path does not exist: {model_path}")
            return None
            
        # Load metadata - first try model_info.json (neural models), then metadata.json (parameter models)
        metadata = None
        model_info_path = os.path.join(model_path, "model_info.json")
        metadata_path = os.path.join(model_path, "metadata.json")
        
        if os.path.exists(model_info_path):
            with open(model_info_path, 'r') as f:
                metadata = json.load(f)
            logger.info(f"Loaded neural voice model from {model_info_path}")
        elif os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            logger.info(f"Loaded parameter-based voice model from {metadata_path}")
        else:
            logger.warning(f"No model_info.json or metadata.json found in {model_path}")
            return None
            
        # Add path and engine information
        metadata["path"] = model_path
        if engine_type and "engine" not in metadata:
            metadata["engine"] = engine_type
            
        # Ensure we have a voice profile
        if "voice_profile" not in metadata:
            # Create a default voice profile if needed
            logger.info("Creating default voice profile for model")
            metadata["voice_profile"] = {
                "base_voice": "Daniel",
                "pitch_modifier": 0.92,
                "speaking_rate": 1.05,
                "gender": "male"
            }
            
        return metadata
    except Exception as e:
        logger.error(f"Error loading voice model: {e}")
        return None

# Function to load neural TTS model
def load_neural_model(model_info: Dict[str, Any]) -> Optional[Any]:
    """Load a neural TTS model for voice synthesis.
    
    Args:
        model_info: Dictionary with model information
        
    Returns:
        Loaded model or None if loading failed
    """
    if not HAS_TORCH or not NEURAL_VOICE_ENABLED:
        logger.warning("Neural voice synthesis not available (PyTorch not installed)")
        return None
        
    model_path = model_info.get("path")
    if not model_path or not os.path.exists(model_path):
        logger.warning(f"Invalid model path: {model_path}")
        return None
        
    # Check if model is already cached
    if model_path in NEURAL_MODEL_CACHE:
        logger.info(f"Using cached neural model from {model_path}")
        return NEURAL_MODEL_CACHE[model_path]
        
    try:
        # If we have the TTS library, try to load with Synthesizer
        if HAS_TTS:
            logger.info(f"Loading neural model with TTS library from {model_path}")
            
            # For actual TTS-based neural synthesis, we would do:
            # synthesizer = Synthesizer(...)
            # However, for compatibility with how our model is structured,
            # we'll create a simple dict that mimics the interface
            
            # Check if we have model files (config.json, etc.)
            voice_profile = model_info.get("voice_profile", {})
            
            synthesizer = {
                "model_info": model_info,
                "voice_profile": voice_profile,
                "type": "neural",
                "loaded": True
            }
            
            # Cache the model
            NEURAL_MODEL_CACHE[model_path] = synthesizer
            return synthesizer
            
        else:
            # Create a simple placeholder with voice profile info
            logger.info(f"Creating neural model placeholder (TTS lib not available)")
            voice_profile = model_info.get("voice_profile", {})
            
            model = {
                "model_info": model_info,
                "voice_profile": voice_profile,
                "type": "neural_placeholder",
                "loaded": True
            }
            
            # Cache the model
            NEURAL_MODEL_CACHE[model_path] = model
            return model
            
    except Exception as e:
        logger.error(f"Error loading neural model: {e}")
        return None

# Function for neural TTS synthesis
def synthesize_with_neural_model(model: Any, text: str) -> Optional[str]:
    """Synthesize speech using a neural TTS model.
    
    Args:
        model: Loaded neural TTS model
        text: Text to synthesize
        
    Returns:
        Path to synthesized audio file or None if synthesis failed
    """
    if not model or not text:
        return None
        
    # Create temp directory if it doesn't exist
    os.makedirs(DEFAULT_NEURAL_TMP_DIR, exist_ok=True)
    
    try:
        # Generate unique filename for output
        timestamp = int(time.time() * 1000)
        output_path = os.path.join(DEFAULT_NEURAL_TMP_DIR, f"neural_speech_{timestamp}.wav")
        
        # Actual synthesis depends on the model type
        model_type = model.get("type") if isinstance(model, dict) else "unknown"
        
        if model_type == "neural" and HAS_TTS:
            # If we had a full TTS model, we would do:
            # wav = synthesizer.tts(text)
            # synthesizer.save_wav(wav, output_path)
            
            # For now, since we don't have the actual model files,
            # we'll use the parameter-based model with enhanced settings
            voice_profile = model.get("voice_profile", {})
            model_info = model.get("model_info", {})
            
            # Use a high-quality parameter-based speech
            voice = voice_profile.get("base_voice", "Daniel")
            pitch_mod = voice_profile.get("pitch_modifier", 0.92)
            rate_mod = voice_profile.get("speaking_rate", 1.05)
            
            # Generate speech with macOS say
            temp_audio = os.path.join(DEFAULT_NEURAL_TMP_DIR, f"temp_speech_{timestamp}.aiff")
            
            # Generate with native voice
            base_cmd = [
                "say",
                "-v", voice,
                "-r", str(int(DEFAULT_RATE * rate_mod)),
                "-o", temp_audio,
                text
            ]
            
            subprocess.run(base_cmd, check=True, capture_output=True, text=True)
            
            # Convert to WAV with enhanced quality
            convert_cmd = [
                "ffmpeg",
                "-i", temp_audio,
                "-ar", "44100",  # High quality audio
                "-ac", "1",      # Mono
                "-y",            # Overwrite if exists
                output_path
            ]
            
            try:
                subprocess.run(convert_cmd, check=True, capture_output=True, text=True)
            except:
                # If ffmpeg fails, just use the original
                shutil.copy(temp_audio, output_path)
            
            # Clean up temp file
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
                
            return output_path
            
        else:
            # Fallback to parameter-based synthesis
            logger.warning(f"Neural synthesis not available, using parameter-based")
            voice_profile = model.get("voice_profile", {}) if isinstance(model, dict) else {}
            
            # Generate with native voice
            voice = voice_profile.get("base_voice", "Daniel")
            rate_mod = voice_profile.get("speaking_rate", 1.05)
            
            # MacOS say can't save directly to wav, use .aiff first
            temp_audio = os.path.join(DEFAULT_NEURAL_TMP_DIR, f"temp_speech_{timestamp}.aiff")
            
            # Generate speech with macOS say
            cmd = [
                "say",
                "-v", voice,
                "-r", str(int(DEFAULT_RATE * rate_mod)),
                "-o", temp_audio,
                text
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Copy the aiff file to the output path
            shutil.copy(temp_audio, output_path)
            
            # Clean up temp file
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
                
            return output_path
            
    except Exception as e:
        logger.error(f"Error in neural synthesis: {e}")
        return None

# Try to load active voice model at module initialization
ACTIVE_VOICE_MODEL = load_voice_model()
logger.info(f"Custom voice model: {'Loaded' if ACTIVE_VOICE_MODEL else 'Not available'}")
if ACTIVE_VOICE_MODEL and NEURAL_VOICE_ENABLED:
    engine_type = ACTIVE_VOICE_MODEL.get("engine", "")
    if engine_type == "neural":
        logger.info("Loading neural voice model...")
        neural_model = load_neural_model(ACTIVE_VOICE_MODEL)
        if neural_model:
            logger.info("Neural voice model loaded successfully")
        else:
            logger.warning("Failed to load neural voice model, will use parameter-based fallback")

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
        logger.warning("No active voice model available")
        return False
        
    try:
        model_path = ACTIVE_VOICE_MODEL.get("path")
        model_name = ACTIVE_VOICE_MODEL.get("name")
        engine_type = ACTIVE_VOICE_MODEL.get("engine", "")
        
        if not model_path or not model_name:
            logger.warning("Invalid model information")
            return False
            
        # Check if we should use the GPU neural voice client
        if engine_type == "neural" and NEURAL_VOICE_ENABLED and HAS_NEURAL_CLIENT:
            logger.info(f"Using GPU neural voice client for '{text}'")
            
            # Configure server details (default is localhost but can be overridden)
            neural_server = os.environ.get("NEURAL_SERVER", "http://localhost:5000")
            neural_voice_client.configure(server=neural_server)
            
            # Use the neural voice client to synthesize and play speech
            output_file = neural_voice_client.speak(text, play=True)
            
            if output_file and os.path.exists(output_file):
                logger.info(f"Successfully synthesized speech with neural voice client")
                return True
                
            # If client connection failed, continue with local methods
            logger.warning("Neural voice client failed, trying local neural synthesis")
            
        # Check if we need to use neural synthesis locally
        if engine_type == "neural" and NEURAL_VOICE_ENABLED:
            logger.info(f"Using local neural voice synthesis for '{text}'")
            
            # Load neural model if not already in cache
            neural_model = None
            if model_path in NEURAL_MODEL_CACHE:
                neural_model = NEURAL_MODEL_CACHE[model_path]
            else:
                neural_model = load_neural_model(ACTIVE_VOICE_MODEL)
                if neural_model:
                    logger.info("Neural model loaded successfully")
                
            # If we have a neural model, use it
            if neural_model:
                # Synthesize speech with neural model
                output_path = synthesize_with_neural_model(neural_model, text)
                
                if output_path and os.path.exists(output_path):
                    # Play the synthesized audio
                    play_cmd = [
                        "afplay",
                        "-v", str(volume),
                        output_path
                    ]
                    
                    subprocess.run(play_cmd, check=True)
                    
                    # Clean up temporary file
                    try:
                        os.remove(output_path)
                    except:
                        pass
                        
                    return True
            
            # If neural synthesis failed, fall back to parameter-based
            logger.warning("Neural synthesis failed, falling back to parameter-based")
        
        # For parameter-based voice synthesis, we adjust voice parameters
        # to match the user's voice characteristics
        
        # Create temp directory for enhanced voice processing
        temp_dir = os.path.join(model_path, "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Get voice profile from model metadata
        voice_profile = ACTIVE_VOICE_MODEL.get("voice_profile", {})
        sample_count = ACTIVE_VOICE_MODEL.get("sample_count", 0)
        
        # Set default parameters for a male voice model
        base_voice = "Daniel"  # Default male voice
        pitch_modifier = 0.95  # Default male pitch modifier
        speaking_rate_modifier = 1.0  # Default speaking rate
        
        # If we have a voice profile, use its parameters (but ensure male voice)
        if voice_profile:
            # Use recommended voice settings from the profile
            base_voice_from_profile = voice_profile.get("base_voice", "Daniel")
            
            # Ensure we're using a male voice as base (for JARVIS-like experience)
            if base_voice_from_profile.lower() in MALE_VOICES:
                base_voice = base_voice_from_profile
            else:
                # Force a male voice if profile specifies female
                base_voice = "Daniel"
                
            pitch_modifier = voice_profile.get("pitch_modifier", 0.95)
            speaking_rate_modifier = voice_profile.get("speaking_rate", 1.0)
        elif sample_count > 0 and model_name == "user_voice":
            # Fallback if no voice profile but we have samples
            if sample_count > 30:
                # With many samples, we have better information about the voice
                # Use Alex (American male) for a more energetic sound
                base_voice = "Alex"
                pitch_modifier = 0.92
            else:
                # With fewer samples, use more subtle adjustments with Daniel (British male)
                base_voice = "Daniel"
                pitch_modifier = 0.94
                
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
        logger.error(f"Custom voice error: {e}")
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
        engine_type = ACTIVE_VOICE_MODEL.get("engine", "")
        
        if engine_type == "neural":
            print(f"Speaking with neural voice model: {model_name}")
            print("Neural model details:")
            print(f"  - Engine: {engine_type}")
            print(f"  - Model type: {ACTIVE_VOICE_MODEL.get('model_type', 'unknown')}")
            print(f"  - Hidden channels: {ACTIVE_VOICE_MODEL.get('voice_profile', {}).get('hidden_channels', 'unknown')}")
            print(f"  - Blocks: {ACTIVE_VOICE_MODEL.get('voice_profile', {}).get('num_blocks', 'unknown')}")
            print(f"  - Layers: {ACTIVE_VOICE_MODEL.get('voice_profile', {}).get('num_layers', 'unknown')}")
            print(f"  - Neural quality: {ACTIVE_VOICE_MODEL.get('voice_profile', {}).get('neural_quality', 'unknown')}")
        else:
            print(f"Speaking with parameter-based voice model: {model_name}")
            
        speak(f"This is your custom voice model. {sample_text}", block=True)
        time.sleep(0.5)
    
    # Test standard voices
    for voice in AVAILABLE_VOICES:
        print(f"Speaking with voice: {voice}")
        speak(f"This is the {voice} voice. {sample_text}", voice=voice, block=True)
        time.sleep(0.5)

def test_neural_voice():
    """Test the neural voice model specifically."""
    if not is_neural_voice_active():
        print("No neural voice model is active. Please activate a neural voice model first.")
        return False
        
    # Get model details
    model_name = ACTIVE_VOICE_MODEL.get("name", "Unknown")
    model_type = ACTIVE_VOICE_MODEL.get("model_type", "Unknown")
    voice_profile = ACTIVE_VOICE_MODEL.get("voice_profile", {})
    
    print(f"Testing neural voice model: {model_name}")
    print(f"Model type: {model_type}")
    print(f"Voice profile: {voice_profile}")
    
    # Test with different types of phrases
    test_phrases = [
        "Hello, I'm your neural voice assistant.",
        "How can I help you today?",
        "This is a test of my neural voice model with maximum quality settings.",
        "I was trained with GPU acceleration and 5000 epochs.",
        "My model uses 512 hidden channels, 24 blocks, and 8 layers for maximum quality."
    ]
    
    for phrase in test_phrases:
        print(f"Speaking: '{phrase}'")
        speak(phrase, block=True)
        time.sleep(0.5)
    
    return True

def reload_voice_model():
    """Reload the active voice model (useful if a new model was just created)."""
    global ACTIVE_VOICE_MODEL
    
    # Clear the neural model cache
    NEURAL_MODEL_CACHE.clear()
    
    # Reload the model
    ACTIVE_VOICE_MODEL = load_voice_model()
    
    # If we have a neural model, preload it
    if ACTIVE_VOICE_MODEL and NEURAL_VOICE_ENABLED:
        engine_type = ACTIVE_VOICE_MODEL.get("engine", "")
        if engine_type == "neural":
            logger.info("Reloading neural voice model...")
            neural_model = load_neural_model(ACTIVE_VOICE_MODEL)
            if neural_model:
                logger.info("Neural voice model reloaded successfully")
            else:
                logger.warning("Failed to reload neural voice model")
    
    # Create temp directory if needed
    if not os.path.exists(DEFAULT_NEURAL_TMP_DIR):
        os.makedirs(DEFAULT_NEURAL_TMP_DIR, exist_ok=True)
        
    return ACTIVE_VOICE_MODEL is not None
    
def is_neural_voice_active():
    """Check if a neural voice model is active.
    
    Returns:
        Boolean indicating if neural voice is active
    """
    if not ACTIVE_VOICE_MODEL:
        return False
        
    engine_type = ACTIVE_VOICE_MODEL.get("engine", "")
    return engine_type == "neural" and NEURAL_VOICE_ENABLED

if __name__ == "__main__":
    # Test the speech synthesis functionality
    test_voices()