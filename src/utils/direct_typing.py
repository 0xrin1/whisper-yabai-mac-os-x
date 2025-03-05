#!/usr/bin/env python3
"""
Direct typing script that uses pure AppleScript to type text
"""

import subprocess
import sys
import os

def type_text(text):
    """Type text using pure AppleScript - no clipboard involved"""
    # Save to a temp file for the AppleScript
    with open("/tmp/direct_text.txt", "w") as f:
        f.write(text)
    
    # Create AppleScript to directly type the text
    script = '''
    set the_text to (do shell script "cat /tmp/direct_text.txt")
    tell application "System Events"
        keystroke the_text
    end tell
    '''
    
    subprocess.run(["osascript", "-e", script], check=True)
    print(f"Typed: {text}")
    
    # Clean up
    os.remove("/tmp/direct_text.txt")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        print(f"Attempting to type: {text}")
        type_text(text)
    else:
        print("Usage: python direct_typing.py \"Text to type\"")