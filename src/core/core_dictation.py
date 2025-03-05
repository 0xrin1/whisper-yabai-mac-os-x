#!/usr/bin/env python3
"""
Core dictation processing module for voice control system.
Provides common functionality for all dictation implementations.
"""

import os
import time
import logging
import subprocess
import traceback
from typing import Optional, List, Dict, Any, Callable

from src.config.config import config
from src.core.error_handler import handle_error, safe_execute

logger = logging.getLogger('core-dictation')

class CoreDictationProcessor:
    """
    Core dictation functionality used by all dictation implementations.
    Handles text typing using multiple fallback methods.
    """
    
    def __init__(self):
        """Initialize core dictation processor."""
        # Load configured sound for completion
        self.completion_sound = config.get('DICTATION_COMPLETION_SOUND', 'Pop')
        
        # Configure log file path
        self.log_file = config.get('DICTATION_LOG_FILE', 'dictation_log.txt')
        
        # Typing methods in order of preference
        self.typing_methods = [
            self._type_with_applescript,
            self._type_with_clipboard,
            self._type_with_pyautogui
        ]
    
    def type_text(self, transcription: str) -> bool:
        """
        Type text using multiple fallback methods.
        
        Args:
            transcription: The text to type
            
        Returns:
            bool: True if text was typed successfully
        """
        logger.info(f"Typing text: '{transcription}'")
        
        if not transcription or transcription.strip() == "":
            logger.warning("Empty text provided, nothing to type")
            return False
        
        # Try each typing method in sequence
        success = False
        errors = []
        
        for method in self.typing_methods:
            if success:
                break
                
            try:
                logger.debug(f"Trying typing method: {method.__name__}")
                result = method(transcription)
                if result:
                    success = True
                    logger.debug(f"Method {method.__name__} succeeded")
                else:
                    logger.debug(f"Method {method.__name__} failed")
            except Exception as e:
                error_msg = f"{method.__name__} failed: {e}"
                logger.debug(error_msg)
                errors.append(error_msg)
        
        # Always log the dictation text
        self._log_dictation(transcription)
        
        # Play completion sound if enabled
        if config.get('PLAY_COMPLETION_SOUND', True):
            self._play_completion_sound()
        
        # Show notification if enabled
        if config.get('SHOW_DICTATION_NOTIFICATIONS', True):
            self._notify_dictation_complete(transcription, success)
        
        # If all methods failed, log errors
        if not success:
            logger.error("All typing methods failed")
            for error in errors:
                logger.error(f"  - {error}")
        
        return success
    
    def _type_with_applescript(self, text: str) -> bool:
        """
        Type text using AppleScript (most reliable on macOS).
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful
        """
        try:
            # Save to temp file for AppleScript
            tmp_file = "/tmp/dictation_text.txt"
            with open(tmp_file, "w") as f:
                f.write(text)
            
            # AppleScript to keystroke the text
            script = '''
            set the_text to (do shell script "cat /tmp/dictation_text.txt")
            tell application "System Events"
                delay 0.5
                keystroke the_text
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script], 
                check=False, 
                capture_output=True,
                text=True
            )
            
            # Clean up temp file
            try:
                os.remove(tmp_file)
            except Exception as e:
                logger.debug(f"Failed to remove temp file: {e}")
            
            return result.returncode == 0
            
        except Exception as e:
            handle_error(e, logger, "AppleScript typing")
            return False
    
    def _type_with_clipboard(self, text: str) -> bool:
        """
        Type text using clipboard (pbcopy + cmd+v).
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful
        """
        try:
            # Copy text to clipboard using pbcopy
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            
            # Add delay to ensure clipboard is updated
            time.sleep(config.get('CLIPBOARD_DELAY', 1.0))
            
            # Paste using command+v
            import pyautogui
            pyautogui.hotkey('command', 'v')
            
            return True
            
        except Exception as e:
            handle_error(e, logger, "Clipboard typing")
            return False
    
    def _type_with_pyautogui(self, text: str) -> bool:
        """
        Type text using PyAutoGUI direct typing.
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful
        """
        try:
            import pyautogui
            pyautogui.write(text, interval=config.get('TYPING_INTERVAL', 0.03))
            return True
            
        except Exception as e:
            handle_error(e, logger, "PyAutoGUI typing")
            return False
    
    def _log_dictation(self, text: str) -> None:
        """
        Log dictation text to file.
        
        Args:
            text: Text to log
        """
        try:
            with open(self.log_file, 'a') as f:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{timestamp}: {text}\n")
                
            logger.debug(f"Dictation logged to {self.log_file}")
            
        except Exception as e:
            handle_error(e, logger, "Dictation logging")
    
    def _play_completion_sound(self) -> None:
        """Play a sound to indicate dictation is complete."""
        try:
            from src.audio.resource_manager import play_system_sound
            play_system_sound(self.completion_sound)
        except Exception as e:
            # Fallback if resource_manager not available
            try:
                subprocess.run(["afplay", f"/System/Library/Sounds/{self.completion_sound}.aiff"], check=False)
            except Exception as inner_e:
                handle_error(inner_e, logger, "Completion sound playback")
    
    def _notify_dictation_complete(self, text: str, success: bool) -> None:
        """
        Show notification for completed dictation.
        
        Args:
            text: The transcribed text
            success: Whether typing was successful
        """
        try:
            # Import here to avoid circular imports
            from src.ui.toast_notifications import notify_command_executed, notify_error
            
            if success:
                notify_command_executed(f"Transcribed: {text}")
            else:
                notify_error("Failed to type dictated text")
                
        except Exception as e:
            handle_error(e, logger, "Dictation notification")

# Create a singleton instance
core_dictation = CoreDictationProcessor()