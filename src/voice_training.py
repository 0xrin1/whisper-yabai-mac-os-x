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

def record_sample(seconds: float = 3.0, prompt: str = None, interactive: bool = True) -> str:
    """Record an audio sample of specified length.
    
    Args:
        seconds: Length of recording in seconds
        prompt: Optional text to display before recording
        interactive: Whether to wait for user input before recording
        
    Returns:
        Path to the recorded WAV file
    """
    if prompt:
        print(f"\n{prompt}")
    
    # Create temp file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(TRAINING_DIR, f"sample_{timestamp}.wav")
    
    # In interactive mode, wait for user to press Enter
    if interactive:
        try:
            input("Press Enter when ready to begin recording...")
        except (EOFError, KeyboardInterrupt):
            print("\nProceeding with recording...")
    
    print(f"Recording for {seconds} seconds...")
    
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
    
    # Record audio with countdown display
    frames = []
    total_chunks = int(RATE / CHUNK * seconds)
    for i in range(total_chunks):
        # Show progress every ~0.5 seconds
        if i % int(total_chunks/4) == 0:
            time_left = (total_chunks - i) * CHUNK / RATE
            print(f"* {time_left:.1f} seconds remaining...")
            
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
    
    # In interactive mode, allow review of the recording
    if interactive:
        try:
            review = input("Would you like to listen to your recording? (y/n): ").lower()
            if review == 'y':
                print("* Playing recording...")
                subprocess.run(["afplay", file_path], check=False)
                
            redo = input("Would you like to re-record this sample? (y/n): ").lower()
            if redo == 'y':
                print("* Deleting previous recording...")
                try:
                    os.remove(file_path)
                except:
                    pass
                return record_sample(seconds, prompt, interactive)
        except (EOFError, KeyboardInterrupt):
            print("\nContinuing with current recording...")
    
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
    
    # Verify file exists
    if not os.path.exists(sample_path):
        print(f"Warning: Sample file {sample_path} not found!")
        return {
            "text": "[File not found]",
            "confidence": 0,
            "language": "en",
            "segments": 0
        }
    
    # Check if file is valid WAV
    try:
        with wave.open(sample_path, 'rb') as wf:
            if wf.getnchannels() == 0 or wf.getnframes() == 0:
                print(f"Warning: Sample file {sample_path} appears to be invalid!")
                return {
                    "text": "[Invalid audio file]",
                    "confidence": 0,
                    "language": "en",
                    "segments": 0
                }
    except Exception as e:
        print(f"Error checking audio file: {e}")
        # If it's not a WAV file at all, just return a placeholder
        return {
            "text": "[Invalid audio format]",
            "confidence": 0,
            "language": "en",
            "segments": 0
        }
    
    try:
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
    except Exception as e:
        print(f"Error during transcription: {e}")
        return {
            "text": f"[Transcription error: {str(e)}]",
            "confidence": 0,
            "language": "en",
            "segments": 0
        }

def collect_trigger_samples() -> List[str]:
    """Collect samples of trigger words.
    
    Returns:
        List of file paths for the samples
    """
    samples = []
    
    # Check if we're in interactive mode
    import sys
    interactive_mode = "--non-interactive" not in sys.argv
    
    try:
        # Collect "hey" samples
        for i in range(3):
            sample = record_sample(
                seconds=2.0,
                prompt=f"Sample {i+1}/3: Say 'hey' clearly",
                interactive=interactive_mode
            )
            samples.append(sample)
            time.sleep(1)
        
        # Collect "type" samples
        for i in range(3):
            sample = record_sample(
                seconds=2.0,
                prompt=f"Sample {i+1}/3: Say 'type' clearly",
                interactive=interactive_mode
            )
            samples.append(sample)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nRecording interrupted. Using samples collected so far.")
        if not samples:
            print("No samples collected. Using test samples instead.")
            # Create a dummy sample if interrupted before any samples were collected
            dummy_path = os.path.join(TRAINING_DIR, "dummy_sample.wav")
            subprocess.run(["cp", "/System/Library/Sounds/Tink.aiff", dummy_path], check=False)
            samples.append(dummy_path)
    
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
    
    # Check if we're in interactive mode
    import sys
    interactive_mode = "--non-interactive" not in sys.argv
    
    try:
        for cmd in commands:
            sample = record_sample(
                seconds=3.0,
                prompt=f"Say the command: '{cmd}'",
                interactive=interactive_mode
            )
            samples.append(sample)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCommand recording interrupted. Using samples collected so far.")
        if not samples:
            print("No command samples collected. Using test samples instead.")
            # Create a dummy sample if interrupted before any samples were collected
            dummy_path = os.path.join(TRAINING_DIR, "dummy_command_sample.wav")
            subprocess.run(["cp", "/System/Library/Sounds/Tink.aiff", dummy_path], check=False)
            samples.append(dummy_path)
    
    return samples

def calculate_optimal_thresholds(samples: List[str]) -> Dict[str, float]:
    """Calculate optimal energy thresholds based on samples.
    
    Args:
        samples: List of sample file paths
        
    Returns:
        Dictionary with recommended thresholds
    """
    # Default values in case analysis fails
    default_thresholds = {
        "trigger_threshold": 200,
        "dictation_threshold": 150,
        "command_threshold": 120,
        "continuous_threshold": 180
    }
    
    if not samples:
        print("No samples available for analysis. Using default threshold values.")
        return default_thresholds
    
    # Analyze each sample
    try:
        # Filter out any sample paths that might be problematic
        valid_samples = [s for s in samples if os.path.exists(s) and os.path.getsize(s) > 0]
        
        if not valid_samples:
            print("No valid samples available for analysis. Using default threshold values.")
            return default_thresholds
            
        all_results = []
        for sample in valid_samples:
            try:
                result = analyze_energy_levels(sample)
                all_results.append(result)
            except Exception as e:
                print(f"Error analyzing sample {sample}: {e}")
        
        if not all_results:
            print("Failed to analyze any samples. Using default threshold values.")
            return default_thresholds
        
        # Calculate average values
        avg_speech = np.mean([r["speech_baseline"] for r in all_results])
        avg_silence = np.mean([r["silence_baseline"] for r in all_results])
        
        # Handle edge case where avg_speech <= avg_silence
        if avg_speech <= avg_silence:
            print("Warning: Speech baseline is not higher than silence baseline. Using default thresholds.")
            return default_thresholds
        
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
    except Exception as e:
        print(f"Error calculating thresholds: {e}. Using default values.")
        return default_thresholds

def main():
    """Main function for voice training."""
    print("\n=== VOICE TRAINING UTILITY ===")
    print("This tool will help optimize the voice control system for your voice.")
    print("You'll be asked to record samples of various trigger words and commands.")
    print("The system will then analyze them and suggest optimal settings.\n")
    
    # Check command line args
    import sys
    interactive_mode = "--non-interactive" not in sys.argv
    
    print(f"Running in {'interactive' if interactive_mode else 'non-interactive'} mode")
    
    # Ensure training directory exists
    ensure_training_dir()
    
    # Ask user for consent in interactive mode
    if interactive_mode:
        try:
            consent = input("Ready to begin recording? (y/n): ").lower()
            if consent != 'y':
                print("Training cancelled.")
                return
        except (EOFError, KeyboardInterrupt):
            print("\nInput interrupted. Assuming 'y' to continue...")
            consent = 'y'
    else:
        print("Non-interactive mode: proceeding without user confirmation.")
    
    # Collect samples
    print("\n=== COLLECTING TRIGGER WORD SAMPLES ===")
    trigger_samples = collect_trigger_samples() if interactive_mode else []
    
    print("\n=== COLLECTING COMMAND SAMPLES ===")
    command_samples = collect_command_samples() if interactive_mode else []
    
    # If in non-interactive mode or no samples collected, use test files
    if not interactive_mode or (not trigger_samples and not command_samples):
        print("\nUsing test audio files instead of recordings...")
        # Use system sounds as test files
        test_files = []
        system_sounds = [
            "/System/Library/Sounds/Tink.aiff",
            "/System/Library/Sounds/Basso.aiff",
            "/System/Library/Sounds/Ping.aiff",
            "/System/Library/Sounds/Pop.aiff"
        ]
        
        for i, sound in enumerate(system_sounds):
            if os.path.exists(sound):
                test_path = os.path.join(TRAINING_DIR, f"test_sample_{i}.wav")
                try:
                    # Convert to WAV for compatibility
                    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", sound, test_path], check=True)
                    test_files.append(test_path)
                    print(f"* Created test file: {test_path}")
                except Exception as e:
                    print(f"* Error creating test file: {e}")
        
        # Use these test files instead of real recordings
        trigger_samples = test_files[:2] if test_files else []
        command_samples = test_files[2:] if len(test_files) > 2 else []
    
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
            sample_name = os.path.basename(all_samples[i]) if i < len(all_samples) else f"sample_{i}"
            f.write(f"  {sample_name}: \"{result['text']}\" (confidence: {result['confidence']:.2f})\n")
        
        # Add instructions for applying settings
        f.write("\n=== HOW TO APPLY THESE SETTINGS ===\n")
        f.write("1. Edit src/audio_recorder.py:\n")
        f.write("   - Find the AudioRecorder class\n")
        f.write("   - Update the SILENCE_THRESHOLD values in the start_recording method:\n")
        f.write(f"     if trigger_mode:\n            SILENCE_THRESHOLD = {thresholds['trigger_threshold']}  # Trigger detection\n")
        f.write(f"     elif dictation_mode:\n            SILENCE_THRESHOLD = {thresholds['dictation_threshold']}  # Dictation mode\n")
        f.write(f"     else:\n            SILENCE_THRESHOLD = {thresholds['command_threshold']}  # Command mode\n\n")
        
        f.write("2. Edit src/continuous_recorder.py:\n")
        f.write("   - Find the ContinuousRecorder class\n")
        f.write(f"   - Update the energy_threshold value to {thresholds['continuous_threshold']}\n\n")
        
        f.write("3. Restart the daemon after making these changes\n")
    
    print(f"\nRecommendations saved to: {output_file}")
    print("\nTo apply these settings:")
    print(f"1. Edit src/audio_recorder.py - update SILENCE_THRESHOLD values:")
    print(f"   - Trigger mode: {thresholds['trigger_threshold']}")
    print(f"   - Dictation mode: {thresholds['dictation_threshold']}")
    print(f"   - Command mode: {thresholds['command_threshold']}")
    print(f"2. Edit src/continuous_recorder.py - set energy_threshold to {thresholds['continuous_threshold']}")
    print(f"3. Restart the daemon after making these changes")
    print("\nThank you for training the system with your voice!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError running voice training: {e}")
        print("Generating default recommendations anyway...")
        
        # Create directory if needed
        if not os.path.exists(TRAINING_DIR):
            os.makedirs(TRAINING_DIR)
            
        # Generate default recommendations file
        output_file = os.path.join(TRAINING_DIR, "recommendations.txt")
        with open(output_file, 'w') as f:
            f.write("=== VOICE TRAINING RECOMMENDATIONS (DEFAULT VALUES) ===\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("Default silence thresholds:\n")
            f.write("  TRIGGER_MODE: SILENCE_THRESHOLD = 200\n")
            f.write("  DICTATION_MODE: SILENCE_THRESHOLD = 150\n")
            f.write("  COMMAND_MODE: SILENCE_THRESHOLD = 120\n")
            f.write("  CONTINUOUS_RECORDING: energy_threshold = 180\n")
            
        print(f"Default recommendations saved to: {output_file}")