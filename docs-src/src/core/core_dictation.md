# core_dictation

Core dictation processing module for voice control system.
Provides common functionality for all dictation implementations.

Source: `core/core_dictation.py`

## Class: CoreDictationProcessor

Core dictation functionality used by all dictation implementations.
    Handles text typing using multiple fallback methods.

## Function: `__init__(self)`

Initialize core dictation processor.

## Function: `type_text(self, transcription: str)`

Type text using multiple fallback methods.
        
        Args:
            transcription: The text to type
            
        Returns:
            bool: True if text was typed successfully

## Function: `_type_with_applescript(self, text: str)`

Type text using AppleScript (most reliable on macOS).
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful

## Function: `_type_with_clipboard(self, text: str)`

Type text using clipboard (pbcopy + cmd+v).
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful

## Function: `_type_with_pyautogui(self, text: str)`

Type text using PyAutoGUI direct typing.
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful

## Function: `_log_dictation(self, text: str)`

Log dictation text to file.
        
        Args:
            text: Text to log

## Function: `_play_completion_sound(self)`

Play a sound to indicate dictation is complete.

## Function: `_notify_dictation_complete(self, text: str, success: bool)`

Show notification for completed dictation.
        
        Args:
            text: The transcribed text
            success: Whether typing was successful

