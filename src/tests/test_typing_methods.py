#!/usr/bin/env python3
"""
Test script to compare different typing methods that might work with Dvorak layout
"""

import pyperclip
import pyautogui
import time
import keyboard
import subprocess
import os

test_text = "Test text with Dvorak layout - clipboard based solution"

def method_1_clipboard():
    """Test clipboard-based pasting (should work regardless of keyboard layout)"""
    print("\nMethod 1: Clipboard with pyautogui.hotkey('command', 'v')")
    print(f"Copying text: {test_text}")
    
    # Save original clipboard
    original = pyperclip.paste()
    
    # Use clipboard method
    pyperclip.copy(test_text)
    time.sleep(0.5)
    
    print("Pasting in 3 seconds...")
    time.sleep(3)
    pyautogui.hotkey('command', 'v')
    
    # Restore original clipboard
    time.sleep(0.5)
    pyperclip.copy(original)
    
def method_2_applescript():
    """Test AppleScript method"""
    print("\nMethod 2: AppleScript paste")
    print(f"Pasting text via AppleScript: {test_text}")
    
    # Save to a temp file for the AppleScript
    with open("/tmp/paste_text.txt", "w") as f:
        f.write(test_text)
    
    # Create AppleScript to paste text
    script = f'''
    set the_text to (do shell script "cat /tmp/paste_text.txt")
    tell application "System Events"
        keystroke the_text
    end tell
    '''
    
    print("Pasting in 3 seconds...")
    time.sleep(3)
    
    # Execute the AppleScript
    try:
        subprocess.run(["osascript", "-e", script], check=True)
        print("AppleScript execution completed")
    except Exception as e:
        print(f"AppleScript error: {e}")
    
    # Clean up
    os.remove("/tmp/paste_text.txt")
    
def method_3_pbpaste():
    """Test pbpaste method"""
    print("\nMethod 3: pbpaste with keyboard shortcut")
    print(f"Copying text via pbcopy: {test_text}")
    
    # Use pbcopy to copy text to clipboard
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(test_text.encode('utf-8'))
        print("Text copied to clipboard using pbcopy")
    except Exception as e:
        print(f"pbcopy error: {e}")
    
    print("Pasting in 3 seconds...")
    time.sleep(3)
    pyautogui.hotkey('command', 'v')

def method_4_direct_typing():
    """Test direct typing (will likely have issues with Dvorak)"""
    print("\nMethod 4: Direct typing with pyautogui.write()")
    print(f"Typing directly: {test_text}")
    
    print("Typing in 3 seconds...")
    time.sleep(3)
    pyautogui.write(test_text, interval=0.05)

if __name__ == "__main__":
    print("Testing different typing methods that might work with Dvorak layout")
    print("Please position your cursor where you want to type between tests")
    
    # Ask which method to test
    print("\nWhich method would you like to test?")
    print("1: Clipboard with pyautogui.hotkey('command', 'v')")
    print("2: AppleScript paste")
    print("3: pbpaste with keyboard shortcut")
    print("4: Direct typing with pyautogui.write()")
    print("5: Run all tests sequentially")
    
    choice = input("Enter choice (1-5): ")
    
    if choice == '1':
        method_1_clipboard()
    elif choice == '2':
        method_2_applescript()
    elif choice == '3':
        method_3_pbpaste()
    elif choice == '4':
        method_4_direct_typing()
    elif choice == '5':
        method_1_clipboard()
        input("Press Enter to continue to next test...")
        method_2_applescript()
        input("Press Enter to continue to next test...")
        method_3_pbpaste()
        input("Press Enter to continue to next test...")
        method_4_direct_typing()
    else:
        print("Invalid choice")