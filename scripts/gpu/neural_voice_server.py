#!/usr/bin/env python3
"""
Neural Voice Server - High-quality GPU-accelerated voice synthesis
Serves neural TTS requests from clients over HTTP
"""

import os
import sys
import time
import json
import logging
import argparse
import threading
import traceback
import numpy as np
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("neural_voice_server.log")
    ]
)
logger = logging.getLogger("neural-voice-server")

# Try to import required libraries
try:
    import torch
    TORCH_AVAILABLE = True
    logger.info(f"PyTorch available: {torch.__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"CUDA devices: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            logger.info(f"CUDA device {i}: {torch.cuda.get_device_name(i)}")
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available - server will start but synthesis will fail")

try:
    import TTS
    from TTS.utils.manage import ModelManager
    from TTS.utils.synthesizer import Synthesizer
    TTS_AVAILABLE = True
    logger.info(f"TTS available: {TTS.__version__}")
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("TTS not available - server will start but synthesis will fail")

try:
    from flask import Flask, request, send_file, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.error("Flask not available - server cannot start. Install with 'pip install flask'")

# Default settings
DEFAULT_PORT = 5001
DEFAULT_HOST = "0.0.0.0"
DEFAULT_MODEL_PATH = "voice_models/neural_voice"
AUDIO_OUTPUT_DIR = "audio_cache"
MAX_CACHE_SIZE = 1000  # Maximum number of cached audio files

# Global variables
app = Flask(__name__) if FLASK_AVAILABLE else None
synthesizer = None
model_info = None
synthesis_counter = 0
audio_cache = {}  # text -> file path
cache_lock = threading.Lock()

def load_model(model_path: str) -> Optional[Dict[str, Any]]:
    """Load neural TTS model.
    
    Args:
        model_path: Path to model directory
        
    Returns:
        Model information dictionary or None if failed
    """
    global synthesizer, model_info
    
    if not os.path.exists(model_path):
        logger.error(f"Model path does not exist: {model_path}")
        return None
    
    try:
        # Load model info
        model_info_path = os.path.join(model_path, "model_info.json")
        if not os.path.exists(model_info_path):
            logger.error(f"Model info file not found: {model_info_path}")
            return None
            
        with open(model_info_path, 'r') as f:
            model_info = json.load(f)
            
        logger.info(f"Loaded model info: {model_info.get('name', 'unknown')}")
        
        # Check for actual model files
        model_file = os.path.join(model_path, "best_model.pth")
        config_file = os.path.join(model_path, "config/config.json")
        vocoder_file = os.path.join(model_path, "vocoder_model.pth")
        vocoder_config = os.path.join(model_path, "vocoder_config.json")
        
        # Initialize synthesizer
        if (os.path.exists(model_file) or os.path.exists(os.path.join(model_path, "best_model.pth.tar"))) and os.path.exists(config_file):
            logger.info("Found trained model files, loading Coqui TTS synthesizer")
            
            # If path has .tar extension
            if not os.path.exists(model_file) and os.path.exists(os.path.join(model_path, "best_model.pth.tar")):
                model_file = os.path.join(model_path, "best_model.pth.tar")
            
            # Try to load synthesizer
            try:
                synthesizer = Synthesizer(
                    tts_checkpoint=model_file,
                    tts_config_path=config_file,
                    vocoder_checkpoint=vocoder_file if os.path.exists(vocoder_file) else None,
                    vocoder_config=vocoder_config if os.path.exists(vocoder_config) else None,
                    use_cuda=torch.cuda.is_available()
                )
                logger.info("Successfully loaded neural TTS synthesizer")
            except Exception as e:
                logger.error(f"Error initializing Coqui TTS synthesizer: {e}")
                logger.error(traceback.format_exc())
                # Fall back to placeholder
                synthesizer = {
                    "model_info": model_info,
                    "use_cuda": torch.cuda.is_available() if TORCH_AVAILABLE else False,
                    "loaded": True
                }
        else:
            logger.warning(f"No trained model files found in {model_path}, using fallback synthesizer")
            # Use a placeholder synthesizer
            synthesizer = {
                "model_info": model_info,
                "use_cuda": torch.cuda.is_available() if TORCH_AVAILABLE else False,
                "loaded": True
            }
        
        return model_info
        
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        logger.error(traceback.format_exc())
        return None

def synthesize_speech(text: str) -> Optional[str]:
    """Synthesize speech using loaded model.
    
    Args:
        text: Text to synthesize
        
    Returns:
        Path to output audio file or None if failed
    """
    global synthesis_counter
    
    if not text:
        return None
        
    if not synthesizer:
        logger.error("Synthesizer not loaded")
        return None
        
    # Check cache first
    with cache_lock:
        if text in audio_cache and os.path.exists(audio_cache[text]):
            logger.info(f"Using cached audio for: {text[:30]}...")
            return audio_cache[text]
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(time.time() * 1000)
        synthesis_counter += 1
        output_file = os.path.join(AUDIO_OUTPUT_DIR, f"speech_{timestamp}_{synthesis_counter}.wav")
        
        # Try to use neural TTS if available
        if isinstance(synthesizer, Synthesizer):
            try:
                logger.info(f"Using neural TTS for text: {text[:30]}...")
                start_time = time.time()
                
                # Use GPU if available
                use_cuda = torch.cuda.is_available()
                device = "cuda" if use_cuda else "cpu"
                logger.info(f"Synthesizing with device: {device}")
                
                # Generate speech with neural TTS
                wav = synthesizer.tts(text=text)
                
                # Save as WAV file
                import soundfile as sf
                sf.write(output_file, wav, 22050)
                
                end_time = time.time()
                logger.info(f"Neural synthesis completed in {end_time - start_time:.2f} seconds")
                
            except Exception as e:
                logger.error(f"Error in neural synthesis: {e}")
                logger.error(traceback.format_exc())
                # Fall back to alternative method
                logger.info("Falling back to alternative synthesis method")
                return synthesize_speech_fallback(text, output_file)
        else:
            # Use fallback method
            return synthesize_speech_fallback(text, output_file)
                
        # Add to cache
        with cache_lock:
            # Manage cache size
            if len(audio_cache) >= MAX_CACHE_SIZE:
                # Remove oldest item
                oldest_text = next(iter(audio_cache))
                oldest_file = audio_cache[oldest_text]
                if os.path.exists(oldest_file):
                    os.remove(oldest_file)
                del audio_cache[oldest_text]
                
            # Add new item to cache
            audio_cache[text] = output_file
            
        return output_file
        
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        logger.error(traceback.format_exc())
        return None

def synthesize_speech_fallback(text: str, output_file: str) -> Optional[str]:
    """Fallback method for speech synthesis when neural TTS fails.
    
    Args:
        text: Text to synthesize
        output_file: Path to save the output audio
        
    Returns:
        Path to output audio file or None if failed
    """
    try:
        # For macOS, use say command
        if sys.platform == "darwin":
            # We need to use an intermediate AIFF file since macOS say can't output WAV directly
            timestamp = int(time.time() * 1000)
            temp_file = os.path.join(AUDIO_OUTPUT_DIR, f"temp_{timestamp}.aiff")
            
            # Get voice parameters from model info
            voice = "Daniel"
            rate = 180
            
            if model_info and "voice_profile" in model_info:
                voice_profile = model_info["voice_profile"]
                if "base_voice" in voice_profile:
                    voice = voice_profile["base_voice"]
                if "speaking_rate" in voice_profile:
                    rate = int(170 * voice_profile["speaking_rate"])
            
            # Generate speech with macOS say
            cmd = [
                "say",
                "-v", voice,
                "-r", str(rate),
                "-o", temp_file,
                text
            ]
            
            import subprocess
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Convert to WAV with ffmpeg if available
            try:
                convert_cmd = [
                    "ffmpeg",
                    "-i", temp_file,
                    "-y",  # Overwrite if exists
                    output_file
                ]
                subprocess.run(convert_cmd, check=True, capture_output=True, text=True)
            except:
                # If ffmpeg fails, just use the original
                import shutil
                shutil.copy(temp_file, output_file)
                
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
            return output_file
                
        # For non-macOS systems
        elif TORCH_AVAILABLE:
            # Generate a simple audio signal based on the text
            logger.info("Using PyTorch-based audio generation as fallback")
            
            sample_rate = 22050
            
            # Create a more complex waveform for the fallback audio
            duration = min(10, 0.5 + len(text) * 0.05)  # Rough estimate of duration
            t = torch.arange(0, duration, 1/sample_rate)
            
            # Generate a mix of frequencies to make it sound more like speech
            frequencies = [440, 220, 330, 550, 660]
            amplitudes = [1.0, 0.5, 0.3, 0.2, 0.1]
            
            wave = torch.zeros_like(t)
            for freq, amp in zip(frequencies, amplitudes):
                wave += amp * torch.sin(2 * np.pi * freq * t)
            
            # Normalize
            wave = wave / torch.max(torch.abs(wave))
            
            # Add some amplitude modulation to simulate speech cadence
            mod_freq = 3  # 3 Hz modulation (syllable rate)
            modulation = 0.5 + 0.5 * torch.sin(2 * np.pi * mod_freq * t)
            wave = wave * modulation
            
            # Save as WAV
            try:
                import scipy.io.wavfile as wav
                wav.write(output_file, sample_rate, wave.numpy())
                return output_file
            except Exception as e:
                logger.error(f"Error saving fallback audio: {e}")
                return None
        else:
            logger.error("Cannot generate audio: PyTorch not available and not on macOS")
            return None
            
    except Exception as e:
        logger.error(f"Error in fallback synthesis: {e}")
        logger.error(traceback.format_exc())
        return None

def cleanup_old_files():
    """Clean up old audio files periodically."""
    if not os.path.exists(AUDIO_OUTPUT_DIR):
        return
        
    try:
        # Get list of files
        files = [os.path.join(AUDIO_OUTPUT_DIR, f) for f in os.listdir(AUDIO_OUTPUT_DIR) 
                 if os.path.isfile(os.path.join(AUDIO_OUTPUT_DIR, f))]
        
        # Sort by modification time (oldest first)
        files.sort(key=lambda x: os.path.getmtime(x))
        
        # Keep only the most recent MAX_CACHE_SIZE files
        files_to_delete = files[:-MAX_CACHE_SIZE] if len(files) > MAX_CACHE_SIZE else []
        
        # Delete old files
        for file in files_to_delete:
            try:
                os.remove(file)
                logger.debug(f"Deleted old audio file: {file}")
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error cleaning up old files: {e}")

# Flask routes
if FLASK_AVAILABLE:
    @app.route("/")
    def index():
        """Landing page"""
        return jsonify({
            "status": "running",
            "model": model_info["name"] if model_info else "Not loaded",
            "engine": model_info["engine"] if model_info else "Unknown",
            "cuda": torch.cuda.is_available() if TORCH_AVAILABLE else False
        })
        
    @app.route("/synthesize", methods=["POST"])
    def api_synthesize():
        """Synthesize speech API endpoint"""
        text = request.json.get("text", "")
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        output_file = synthesize_speech(text)
        if not output_file or not os.path.exists(output_file):
            return jsonify({"error": "Failed to synthesize speech"}), 500
            
        # Return audio file
        return send_file(output_file, mimetype="audio/wav")
        
    @app.route("/info")
    def api_info():
        """Get model info"""
        return jsonify({
            "model": model_info,
            "stats": {
                "synthesis_count": synthesis_counter,
                "cache_size": len(audio_cache),
                "cuda_available": torch.cuda.is_available() if TORCH_AVAILABLE else False,
                "gpu_info": {
                    "device_count": torch.cuda.device_count() if TORCH_AVAILABLE and torch.cuda.is_available() else 0,
                    "devices": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] 
                              if TORCH_AVAILABLE and torch.cuda.is_available() else []
                }
            }
        })

def main():
    """Start the neural voice server"""
    parser = argparse.ArgumentParser(description="Neural Voice Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server host")
    parser.add_argument("--model", default=DEFAULT_MODEL_PATH, help="Path to model directory")
    args = parser.parse_args()
    
    if not FLASK_AVAILABLE:
        logger.error("Flask not available. Install with: pip install flask")
        return False
        
    # Load model
    model_info = load_model(args.model)
    if not model_info:
        logger.error(f"Failed to load model from {args.model}")
        return False
        
    # Create output directory
    os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
    
    # Start cleanup thread
    def cleanup_thread():
        while True:
            cleanup_old_files()
            time.sleep(3600)  # Run every hour
            
    threading.Thread(target=cleanup_thread, daemon=True).start()
    
    # Start server
    logger.info(f"Starting neural voice server on {args.host}:{args.port}")
    logger.info(f"Model: {model_info.get('name', 'unknown')}")
    logger.info(f"Engine: {model_info.get('engine', 'unknown')}")
    logger.info(f"CUDA available: {torch.cuda.is_available() if TORCH_AVAILABLE else False}")
    
    app.run(host=args.host, port=args.port)
    return True

if __name__ == "__main__":
    main()