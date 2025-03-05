#!/usr/bin/env python3
"""
Test script to verify clipboard and paste functionality
"""

import pyperclip
import pyautogui
import time

# Copy text to clipboard
text = "Test text"
print(f"Original clipboard content: {pyperclip.paste()}")
print(f"Copying text to clipboard: {text}")
pyperclip.copy(text)

# Wait a moment for clipboard to process
time.sleep(0.5)

# Verify text is in clipboard
clipboard_content = pyperclip.paste()
print(f"Clipboard content after copy: {clipboard_content}")

print("Will paste clipboard contents in 3 seconds...")
print("Please focus where you want to paste text")
time.sleep(3)

# Paste the text (Cmd+V on Mac)
print("Pasting now...")
pyautogui.hotkey('command', 'v')

print("Done!")