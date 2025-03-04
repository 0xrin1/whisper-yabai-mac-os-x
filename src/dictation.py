#!/usr/bin/env python3
"""
Dictation processing module for voice control system.
Converts speech to text and types it at the cursor position.
"""

import os
import time
import subprocess
import logging
import pyautogui

from src.toast_notifications import notify_command_executed, notify_error

logger = logging.getLogger('dictation')

class DictationProcessor:
    """Process dictation by typing text at cursor."""
    
    def __init__(self):
        """Initialize dictation processor."""
        pass
    
    def process(self, transcription):
        """Process dictation by typing text at cursor.
        
        Args:
            transcription: The text to type
        
        Returns:
            bool: True if dictation was processed successfully
        """
        # Add more prominent logging
        logger.info(f"Dictation mode: typing '{transcription}'")
        
        try:
            # Try multiple paste methods in sequence
            success = False
            
            # Method 1: AppleScript (most reliable on macOS)
            try:
                logger.debug("Using AppleScript keystroke method...")
                
                # Save to temp file for AppleScript
                tmp_file = "/tmp/dictation_text.txt"
                with open(tmp_file, "w") as f:
                    f.write(transcription)
                logger.debug(f"Saved text to {tmp_file}")
                
                # AppleScript to keystroke the text - with better error handling
                script = '''
                set the_text to (do shell script "cat /tmp/dictation_text.txt")
                tell application "System Events"
                    delay 0.5
                    keystroke the_text
                end tell
                '''
                
                result = subprocess.run(["osascript", "-e", script], 
                                      check=False, 
                                      capture_output=True,
                                      text=True)
                
                if result.returncode == 0:
                    success = True
                    logger.debug("AppleScript succeeded")
                else:
                    logger.debug(f"AppleScript returned non-zero exit code: {result.returncode}")
                    logger.debug(f"AppleScript stderr: {result.stderr}")
                
                # Clean up temp file
                os.remove(tmp_file)
            except Exception as e1:
                logger.error(f"AppleScript method failed: {e1}")
                
            # Method 2: pbcopy + cmd+v (fallback)
            if not success:
                try:
                    logger.debug("Trying pbcopy + cmd+v method...")
                    
                    # Copy text to clipboard using pbcopy
                    process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                    process.communicate(transcription.encode('utf-8'))
                    time.sleep(1.0)  # Give clipboard time to update
                    
                    logger.debug("Pasting with cmd+v")
                    # Paste using command+v
                    pyautogui.hotkey('command', 'v')
                    success = True
                    logger.debug("Clipboard method succeeded")
                except Exception as e2:
                    logger.warning(f"Clipboard method failed: {e2}")
                
            # Method 3: Direct typing as last resort
            if not success:
                try:
                    logger.debug("Using direct typing as last resort...")
                    pyautogui.write(transcription, interval=0.03)
                    success = True
                    logger.debug("Direct typing succeeded")
                except Exception as e3:
                    logger.error(f"Direct typing failed: {e3}")
                    # Don't raise here, just log the error
                    logger.error("All typing methods failed")
            
            # ALWAYS save to log file, even if typing methods failed
            try:
                logger.debug(f"Writing to dictation log: '{transcription}'")
                with open('dictation_log.txt', 'a') as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {transcription}\n")
                logger.debug("Successfully wrote to dictation log")
            except Exception as log_err:
                logger.error(f"Failed to write to log: {log_err}")
            
            # Play completion sound
            try:
                self._play_completion_sound()
            except Exception as sound_err:
                logger.error(f"Failed to play completion sound: {sound_err}")
                
            # Show success notification
            try:
                notify_command_executed(f"Transcribed: {transcription}")
            except Exception as notif_err:
                logger.error(f"Failed to show notification: {notif_err}")
                
            logger.info("Dictation completed successfully")
            return success
            
        except Exception as e:
            logger.error(f"Failed to process dictation: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            try:
                notify_error(f"Failed to process dictation: {str(e)}")
            except:
                logger.error("Also failed to show error notification")
            
            return False
    
    def _play_completion_sound(self):
        """Play a sound to indicate dictation is complete."""
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Pop.aiff"], check=False)
        except Exception as e:
            logger.error(f"Could not play completion sound: {e}")

# Create a singleton instance
dictation = DictationProcessor()