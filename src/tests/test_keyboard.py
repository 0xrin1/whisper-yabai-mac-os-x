#!/usr/bin/env python3
"""
Test script to verify keyboard hotkey detection
"""

import logging
from pynput import keyboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('keyboard-test')

# Track currently pressed keys
current_keys = set()

def on_press(key):
    """Handle key press events."""
    try:
        logger.info(f"Key pressed: {key}")
        current_keys.add(key)
        
        # Check for various key combinations
        if keyboard.Key.ctrl in current_keys and keyboard.Key.shift in current_keys:
            if keyboard.KeyCode.from_char('d') in current_keys:
                logger.info("*** DETECTED: Ctrl+Shift+D ***")
            elif keyboard.Key.space in current_keys:
                logger.info("*** DETECTED: Ctrl+Shift+Space ***")
                
        # Print all currently held keys
        logger.info(f"Currently held keys: {current_keys}")
            
    except Exception as e:
        logger.error(f"Error in key press handler: {e}")

def on_release(key):
    """Handle key release events."""
    try:
        logger.info(f"Key released: {key}")
        if key in current_keys:
            current_keys.remove(key)
    except Exception as e:
        logger.error(f"Error in key release handler: {e}")
    
    # Stop listener if escape key is pressed
    if key == keyboard.Key.esc:
        logger.info("Escape pressed, exiting...")
        return False

if __name__ == "__main__":
    logger.info("Starting keyboard test...")
    logger.info("Press Ctrl+Shift+D to test dictation hotkey")
    logger.info("Press Ctrl+Shift+Space to test command hotkey")
    logger.info("Press ESC to exit")
    
    # Start keyboard listener
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
    
    logger.info("Keyboard test completed")