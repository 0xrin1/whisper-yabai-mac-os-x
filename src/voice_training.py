#!/usr/bin/env python3
"""
Voice training utility for whisper-yabai-mac-os-x.
This script records samples of your voice saying trigger words and commands,
then uses them to help optimize recognition settings.
"""

import os
import sys
import time
import pyaudio
import wave
import tempfile
import subprocess
import whisper
import numpy as np
import datetime
from typing import List, Dict, Tuple, Optional, Any, Union

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('voice-training')

# Constants
RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1024
TRAINING_DIR = "training_samples"
MODEL_SIZE = "tiny"  # Using smaller model for faster iteration

def ensure_training_dir():
    """Make sure the training directory exists."""
    if not os.path.exists(TRAINING_DIR):
        os.makedirs(TRAINING_DIR)
        logger.info(f"Created directory: {TRAINING_DIR}")

def record_sample(seconds: float = 3.0, prompt: str = None) -> str:
    """Record an audio sample of specified length.
    
    Args:
        seconds: Length of recording in seconds
        prompt: Optional text to display before recording
        
    Returns:
        Path to the recorded WAV file
    """
    if prompt:
        print(f"\n{prompt}")
        
    print(f"Recording for {seconds} seconds...")
    
    # Create temp file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(TRAINING_DIR, f"sample_{timestamp}.wav")
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Open stream
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    print("* Recording...")
    
    # Play a sound to indicate start
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], check=False)
    except:
        pass
    
    # Record audio
    frames = []
    for _ in range(0, int(RATE / CHUNK * seconds)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
    
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Play a sound to indicate end
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff"], check=False)
    except:
        pass
    
    print("* Recording complete")
    
    # Save to WAV file
    wf = wave.open(file_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print(f"* Saved to {file_path}")
    return file_path

def analyze_energy_levels(sample_path: str) -> Dict[str, float]:
    """Analyze energy levels in a sample to help calibrate thresholds.
    
    Args:
        sample_path: Path to WAV file
        
    Returns:
        Dictionary with min, max, avg energy levels
    """
    # Open the WAV file
    wf = wave.open(sample_path, 'rb')
    
    # Read all data
    raw_data = wf.readframes(wf.getnframes())
    wf.close()
    
    # Convert to numpy array
    data = np.frombuffer(raw_data, dtype=np.int16)
    
    # Calculate energy levels
    energy = np.abs(data)
    min_energy = energy.min()
    max_energy = energy.max()
    avg_energy = energy.mean()
    
    # Calculate chunks for better analysis
    chunk_size = RATE // 10  # 100ms chunks
    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    
    # Get energy per chunk
    chunk_energies = [np.abs(chunk).mean() for chunk in chunks if len(chunk) > 0]
    
    # Get the speech baseline (average of the top 50% of chunks)
    chunk_energies.sort(reverse=True)
    speech_chunks = chunk_energies[:len(chunk_energies)//2]
    speech_baseline = np.mean(speech_chunks) if speech_chunks else 0
    
    # Get the silence baseline (average of the bottom 30% of chunks)
    silence_chunks = chunk_energies[-int(len(chunk_energies)*0.3):]
    silence_baseline = np.mean(silence_chunks) if silence_chunks else 0
    
    # Recommended threshold (midway between silence and speech)
    recommended_threshold = (silence_baseline + speech_baseline) / 2
    
    return {
        "min_energy": float(min_energy),
        "max_energy": float(max_energy),
        "avg_energy": float(avg_energy),
        "speech_baseline": float(speech_baseline),
        "silence_baseline": float(silence_baseline),
        "recommended_threshold": float(recommended_threshold)
    }

def transcribe_sample(sample_path: str) -> Dict[str, Any]:
    """Transcribe a sample using Whisper and return results.
    
    Args:
        sample_path: Path to WAV file
        
    Returns:
        Dictionary with transcription results
    """
    print(f"Transcribing {sample_path}...")
    
    # Load model (or reuse if already loaded)
    global whisper_model
    if 'whisper_model' not in globals():
        print(f"Loading Whisper model ({MODEL_SIZE})...")
        whisper_model = whisper.load_model(MODEL_SIZE)
    
    # Transcribe
    result = whisper_model.transcribe(sample_path)
    
    # Return key information
    return {
        "text": result["text"],
        "confidence": result.get("confidence", 0),
        "language": result.get("language", "en"),
        "segments": len(result.get("segments", []))
    }

def collect_trigger_samples() -> List[str]:
    """Collect samples of trigger words.
    
    Returns:
        List of file paths for the samples
    """
    samples = []
    
    # Collect "hey" samples
    for i in range(3):
        sample = record_sample(
            seconds=2.0,
            prompt=f"Sample {i+1}/3: Say 'hey' clearly"
        )
        samples.append(sample)
        time.sleep(1)
    
    # Collect "type" samples
    for i in range(3):
        sample = record_sample(
            seconds=2.0,
            prompt=f"Sample {i+1}/3: Say 'type' clearly"
        )
        samples.append(sample)
        time.sleep(1)
    
    return samples

def collect_command_samples() -> List[str]:
    """Collect samples of various commands.
    
    Returns:
        List of file paths for the samples
    """
    commands = [
        "open safari", 
        "maximize window", 
        "focus chrome", 
        "type hello world"
    ]
    
    samples = []
    for cmd in commands:
        sample = record_sample(
            seconds=3.0,
            prompt=f"Say the command: '{cmd}'"
        )
        samples.append(sample)
        time.sleep(1)
    
    return samples

def calculate_optimal_thresholds(samples: List[str]) -> Dict[str, float]:
    """Calculate optimal energy thresholds based on samples.
    
    Args:
        samples: List of sample file paths
        
    Returns:
        Dictionary with recommended thresholds
    """
    # Analyze each sample
    all_results = [analyze_energy_levels(sample) for sample in samples]
    
    # Calculate average values
    avg_speech = np.mean([r["speech_baseline"] for r in all_results])
    avg_silence = np.mean([r["silence_baseline"] for r in all_results])
    
    # Calculate different thresholds
    trigger_threshold = avg_silence + (avg_speech - avg_silence) * 0.4
    dictation_threshold = avg_silence + (avg_speech - avg_silence) * 0.3
    command_threshold = avg_silence + (avg_speech - avg_silence) * 0.25
    
    return {
        "trigger_threshold": round(float(trigger_threshold)),
        "dictation_threshold": round(float(dictation_threshold)),
        "command_threshold": round(float(command_threshold)),
        "continuous_threshold": round(float(avg_silence + (avg_speech - avg_silence) * 0.35))
    }

def main():
    """Main function for voice training."""
    print("\n=== VOICE TRAINING UTILITY ===")
    print("This tool will help optimize the voice control system for your voice.")
    print("You'll be asked to record samples of various trigger words and commands.")
    print("The system will then analyze them and suggest optimal settings.\n")
    
    # Ensure training directory exists
    ensure_training_dir()
    
    # Ask user for consent
    consent = input("Ready to begin recording? (y/n): ").lower()
    if consent != 'y':
        print("Training cancelled.")
        return
    
    # Collect samples
    print("\n=== COLLECTING TRIGGER WORD SAMPLES ===")
    trigger_samples = collect_trigger_samples()
    
    print("\n=== COLLECTING COMMAND SAMPLES ===")
    command_samples = collect_command_samples()
    
    all_samples = trigger_samples + command_samples
    
    # Calculate optimal thresholds
    print("\n=== ANALYZING SAMPLES ===")
    thresholds = calculate_optimal_thresholds(all_samples)
    
    # Transcribe samples
    print("\n=== TRANSCRIBING SAMPLES ===")
    transcriptions = []
    for sample in all_samples:
        result = transcribe_sample(sample)
        print(f"  {os.path.basename(sample)}: \"{result['text']}\" (confidence: {result['confidence']:.2f})")
        transcriptions.append(result)
    
    # Generate recommendations
    print("\n=== RECOMMENDATIONS ===")
    print("Based on analysis of your voice samples, here are the recommended settings:")
    print(f"  Trigger detection threshold: {thresholds['trigger_threshold']}")
    print(f"  Dictation mode threshold: {thresholds['dictation_threshold']}")
    print(f"  Command mode threshold: {thresholds['command_threshold']}")
    print(f"  Continuous recording threshold: {thresholds['continuous_threshold']}")
    
    # Save recommendations to file
    output_file = os.path.join(TRAINING_DIR, "recommendations.txt")
    with open(output_file, 'w') as f:
        f.write("=== VOICE TRAINING RECOMMENDATIONS ===\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("Recommended silence thresholds:\n")
        f.write(f"  TRIGGER_MODE: SILENCE_THRESHOLD = {thresholds['trigger_threshold']}\n")
        f.write(f"  DICTATION_MODE: SILENCE_THRESHOLD = {thresholds['dictation_threshold']}\n")
        f.write(f"  COMMAND_MODE: SILENCE_THRESHOLD = {thresholds['command_threshold']}\n")
        f.write(f"  CONTINUOUS_RECORDING: energy_threshold = {thresholds['continuous_threshold']}\n\n")
        
        f.write("Sample transcriptions:\n")
        for i, result in enumerate(transcriptions):
            sample_name = os.path.basename(all_samples[i])
            f.write(f"  {sample_name}: \"{result['text']}\" (confidence: {result['confidence']:.2f})\n")
    
    print(f"\nRecommendations saved to: {output_file}")
    print("\nTo apply these settings, update the threshold values in daemon.py")
    print("Thank you for training the system with your voice!")

if __name__ == "__main__":
    main()