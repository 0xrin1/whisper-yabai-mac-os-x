#!/usr/bin/env python3
"""
Test script for neural voice synthesis using GPU acceleration.
"""

import sys
import time
import os
from src import speech_synthesis as speech

def main():
    """Test voice synthesis with various phrases."""
    print("=== Enhanced Voice Model Test ===")
    
    # Check if custom voice model is loaded
    if speech.ACTIVE_VOICE_MODEL:
        print(f"✅ Custom voice model loaded: {speech.ACTIVE_VOICE_MODEL.get('name', 'Unknown')}")
        print(f"   Created: {speech.ACTIVE_VOICE_MODEL.get('created', 'Unknown')}")
        print(f"   Samples: {speech.ACTIVE_VOICE_MODEL.get('sample_count', 0)}")
    else:
        print("⚠️ No custom voice model detected. Using standard system voices.")
    
    # Test system voices first for comparison
    print("\nTesting system voices for comparison:")
    system_voices = ["daniel", "samantha", "karen"]
    test_phrase = "Hello, this is a test of the voice synthesis system."
    
    for voice in system_voices:
        print(f"\nSpeaking with system voice: {voice}")
        speech.speak(test_phrase, voice=voice, block=True)
        time.sleep(0.5)
    
    # Test custom voice with multiple phrases
    print("\nTesting custom voice model:")
    test_phrases = [
        "Hello, I'm your personal assistant using your custom voice model.",
        "This voice should sound more like you, since it uses your voice characteristics.",
        "The quick brown fox jumps over the lazy dog.",
        "How does this voice sound compared to the system voices? Is it more natural?"
    ]
    
    for i, phrase in enumerate(test_phrases):
        print(f"\nSpeaking phrase {i+1}/{len(test_phrases)}:")
        print(f"\"{phrase}\"")
        speech.speak(phrase, block=True)
        time.sleep(0.5)
    
    print("\nVoice test complete.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError during test: {e}")
        sys.exit(1)