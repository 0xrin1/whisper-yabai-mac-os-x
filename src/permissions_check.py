#!/usr/bin/env python3
"""
Simple utility script to check for and request necessary permissions
for the voice control daemon to function properly.
"""

import os
import sys
import subprocess
import time
import pyaudio
from pynput import keyboard

def check_microphone_permission():
    """Check if we have microphone access."""
    print("Testing microphone access...")
    try:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        # Record a small amount of audio to test access
        for i in range(10):
            stream.read(1024)
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("✅ Microphone access granted.")
        return True
    except OSError as e:
        print("❌ Microphone access denied or device not available.")
        print(f"Error: {e}")
        print("\nPlease grant microphone access in System Preferences > Security & Privacy > Privacy > Microphone")
        print("Then run this script again.")
        return False

def check_accessibility_permission():
    """Check if we have accessibility access by testing keyboard monitoring."""
    print("\nTesting accessibility access for keyboard monitoring...")
    print("Press any key within 5 seconds...")
    
    try:
        # Set up flag to check if a key was pressed
        key_pressed = [False]
        
        def on_press(key):
            key_pressed[0] = True
            return False  # Stop listener
        
        # Start listener
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        
        # Wait for key press with timeout
        timeout = 5
        start_time = time.time()
        while time.time() - start_time < timeout and not key_pressed[0]:
            time.sleep(0.1)
        
        if key_pressed[0]:
            print("✅ Keyboard monitoring permission granted.")
            return True
        else:
            # For Ghostty, we'll prompt but also offer to proceed
            print("⚠️ Keyboard monitoring test unsuccessful.")
            print("\nIf you're using Ghostty and have already granted it accessibility permissions:")
            proceed = input("Would you like to proceed anyway? (y/n): ").lower().strip()
            if proceed == 'y' or proceed == 'yes':
                print("Proceeding with voice control daemon...")
                return True
            else:
                print("\nPlease grant accessibility access in System Preferences > Security & Privacy > Privacy > Accessibility")
                print("Make sure to add Ghostty to the list of allowed applications.")
                print("Then run this script again.")
                # Open System Preferences to the right location
                subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
                return False
    except Exception as e:
        print(f"Error testing keyboard access: {e}")
        print("⚠️ Unable to properly test keyboard accessibility.")
        proceed = input("Would you like to proceed anyway? (y/n): ").lower().strip()
        if proceed == 'y' or proceed == 'yes':
            print("Proceeding with voice control daemon...")
            return True
        else:
            return False

def main():
    """Main function to perform permission checks."""
    print("Voice Control Permission Check Utility")
    print("=====================================")
    print("This utility checks if your system has granted the necessary permissions")
    print("to run the Whisper Voice Control daemon.\n")
    
    mic_ok = check_microphone_permission()
    access_ok = check_accessibility_permission()
    
    print("\nPermission Check Summary:")
    print("------------------------")
    print(f"Microphone access: {'✅ Granted' if mic_ok else '❌ Denied'}")
    print(f"Accessibility access: {'✅ Granted' if access_ok else '❌ Denied'}")
    
    if mic_ok and access_ok:
        print("\n✅ All permissions are granted. Voice control daemon should work properly.")
        print("You can now run: python src/simplified_daemon.py")
    else:
        print("\n❌ Some permissions are missing. Please grant the required permissions")
        print("and run this check again before starting the voice control daemon.")
    
    return 0 if mic_ok and access_ok else 1

if __name__ == "__main__":
    sys.exit(main())