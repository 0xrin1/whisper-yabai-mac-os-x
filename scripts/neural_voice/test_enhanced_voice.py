#!/usr/bin/env python3
"""
Test script for enhanced voice training and speech synthesis features.
Demonstrates the advanced voice profiling and context-aware speech.
"""

import os
import sys
import time
import json
import argparse
from typing import List, Dict, Any

# Add the project root to the Python path so we can find the src modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.append(project_root)

# Import speech synthesis module
try:
    import src.audio.speech_synthesis as speech
    from src.audio.voice_training import create_voice_model, install_voice_model
except ImportError:
    print("Error: Could not import speech synthesis module.")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path}")
    sys.exit(1)

# ANSI color codes for terminal output
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
RESET = '\033[0m'

def print_color(text: str, color: str = GREEN) -> None:
    """Print colored text to the terminal."""
    print(f"{color}{text}{RESET}")

def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 60)
    print_color(f" {title}", CYAN)
    print("=" * 60)

def print_subsection(title: str) -> None:
    """Print a subsection header."""
    print("\n" + "-" * 50)
    print_color(f" {title}", MAGENTA)
    print("-" * 50)

def display_voice_model_info() -> None:
    """Display information about the current voice model."""
    if not speech.ACTIVE_VOICE_MODEL:
        print_color("No active voice model found.", YELLOW)
        return
    
    model = speech.ACTIVE_VOICE_MODEL
    print_subsection("Active Voice Model Details")
    
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

def test_basic_speech() -> None:
    """Test basic speech synthesis with different voices."""
    print_subsection("Testing Basic Speech Synthesis")
    
    voices = [
        "Daniel",  # British male
        "Alex",    # American male
        "Fred",    # American male (deeper)
        "Samantha" # American female
    ]
    
    test_phrase = "Hello, I'm your voice assistant. How can I help you today?"
    
    for voice in voices:
        print_color(f"Speaking with {voice} voice:", BLUE)
        speech.speak(test_phrase, voice=voice.lower(), block=True)
        time.sleep(0.5)
    
    # Test custom voice if available
    if speech.ACTIVE_VOICE_MODEL:
        print_color("\nSpeaking with your custom voice model:", BLUE)
        speech.speak(test_phrase, block=True)
        time.sleep(0.5)

def test_context_aware_speech() -> None:
    """Test context-aware speech synthesis with different text types."""
    print_subsection("Testing Context-Aware Speech")
    
    # Define test phrases for different contexts
    questions = [
        "What time is it?",
        "Could you please open Safari for me?",
        "How long will it take to finish this task?"
    ]
    
    commands = [
        "Open Safari and navigate to the homepage.",
        "Move the window to the left side of the screen.",
        "Focus on the terminal application."
    ]
    
    exclamations = [
        "This is amazing!",
        "Look at this fantastic result!",
        "I can't believe how well this works!"
    ]
    
    dictation_phrases = [
        "Type the following text: meeting scheduled for tomorrow at 2pm.",
        "Transcribe this sentence into the document.",
        "Write down these notes for later reference."
    ]
    
    # Test questions (should have rising intonation)
    print_color("Questions (with rising intonation):", BLUE)
    for phrase in questions:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)
    
    # Test commands (should be authoritative)
    print_color("\nCommands (with authoritative tone):", BLUE)
    for phrase in commands:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)
    
    # Test exclamations (should be more energetic)
    print_color("\nExclamations (with more energy):", BLUE)
    for phrase in exclamations:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)
    
    # Test dictation phrases (should be clear and measured)
    print_color("\nDictation phrases (clear and measured):", BLUE)
    for phrase in dictation_phrases:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)

def test_emotion_aware_speech() -> None:
    """Test emotion-aware speech synthesis with different emotional contexts."""
    print_subsection("Testing Emotion-Aware Speech")
    
    # Define test phrases for different emotions
    enthusiastic_phrases = [
        "This is absolutely fantastic news!",
        "What an amazing achievement! Great work!",
        "Wow! This is the most awesome result I've ever seen!"
    ]
    
    authoritative_phrases = [
        "Attention! This is an important announcement.",
        "Listen carefully to these critical instructions.",
        "Warning: You must complete this task immediately."
    ]
    
    warm_phrases = [
        "I'm so glad to hear you're feeling better today.",
        "It's always a pleasure to help you with your tasks.",
        "Welcome back! I've missed our conversations."
    ]
    
    clear_phrases = [
        "Let me explain this concept step by step.",
        "The instructions are as follows: first, open the application.",
        "These are the exact specifications you requested."
    ]
    
    # Test enthusiastic phrases
    print_color("Enthusiastic phrases:", BLUE)
    for phrase in enthusiastic_phrases:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)
    
    # Test authoritative phrases
    print_color("\nAuthoritative phrases:", BLUE)
    for phrase in authoritative_phrases:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)
    
    # Test warm phrases
    print_color("\nWarm phrases:", BLUE)
    for phrase in warm_phrases:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)
    
    # Test clear phrases
    print_color("\nClear phrases:", BLUE)
    for phrase in clear_phrases:
        print(f"> {phrase}")
        speech.speak(phrase, block=True)
        time.sleep(0.5)

def main() -> None:
    """Main function for testing enhanced voice features."""
    parser = argparse.ArgumentParser(description="Test enhanced voice training features")
    parser.add_argument("--reload", action="store_true", help="Reload the voice model before testing")
    parser.add_argument("--basic-only", action="store_true", help="Only test basic speech synthesis")
    parser.add_argument("--context-only", action="store_true", help="Only test context-aware speech")
    parser.add_argument("--emotion-only", action="store_true", help="Only test emotion-aware speech")
    args = parser.parse_args()
    
    # Print header
    print_section("Enhanced Voice Training Test Script")
    print("This script demonstrates the advanced voice profiling and context-aware speech features.")
    
    # Reload voice model if requested
    if args.reload:
        print_color("Reloading voice model...", YELLOW)
        speech.reload_voice_model()
    
    # Display active voice model information
    display_voice_model_info()
    
    # Determine which tests to run
    run_all = not (args.basic_only or args.context_only or args.emotion_only)
    
    # Run selected tests
    if run_all or args.basic_only:
        test_basic_speech()
    
    if run_all or args.context_only:
        test_context_aware_speech()
    
    if run_all or args.emotion_only:
        test_emotion_aware_speech()
    
    # Print footer
    print_section("Test Complete")
    print("The enhanced voice training system provides context-aware and emotion-aware speech synthesis.")
    print("Voice profiles contain detailed information about pitch, timbre, expressiveness, and more.")
    print("For best results, record at least 40 diverse voice samples during training.")

if __name__ == "__main__":
    main()