#!/usr/bin/env python3
"""
Hotkey manager for voice control system.
Manages keyboard shortcuts for system control.
"""

import logging
from pynput import keyboard

from src.state_manager import state
from src.audio_recorder import AudioRecorder

logger = logging.getLogger('hotkey-manager')

class HotkeyManager:
    """Manages keyboard hotkeys for voice control system."""
    
    def __init__(self):
        """Initialize the hotkey manager."""
        self.listener = None
        self.recorder = AudioRecorder()
    
    def start(self):
        """Start listening for keyboard hotkeys."""
        logger.info("Starting keyboard hotkey listener")
        
        # Start keyboard listener
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.daemon = True
        self.listener.start()
        
        logger.info("Keyboard listener started")
    
    def stop(self):
        """Stop listening for keyboard hotkeys."""
        if self.listener and self.listener.running:
            logger.info("Stopping keyboard listener")
            self.listener.stop()
    
    def _on_press(self, key):
        """Handle key press events.
        
        Args:
            key: The key that was pressed
        """
        try:
            logger.debug(f"Key pressed: {key}")
            
            # Update key state
            if key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                state.set_key_state('ctrl', True)
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                state.set_key_state('shift', True)
            elif key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                state.set_key_state('alt', True)
            elif key == keyboard.Key.cmd or key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r:
                state.set_key_state('cmd', True)
            elif key == keyboard.Key.space:
                state.set_key_state('space', True)
            elif isinstance(key, keyboard.KeyCode) and hasattr(key, 'char') and key.char:
                char = key.char.lower()
                if char == 'd':
                    state.set_key_state('d', True)
                elif char == 'm':
                    state.set_key_state('m', True)
            
            # Check for mute toggle hotkey (Ctrl+Shift+M)
            if state.check_hotkey('ctrl', 'shift', 'm'):
                logger.info("Mute toggle hotkey detected: Ctrl+Shift+M")
                self._toggle_mute()
        
        except Exception as e:
            logger.error(f"Error in key press handler: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _on_release(self, key):
        """Handle key release events.
        
        Args:
            key: The key that was released
        
        Returns:
            bool: False if the listener should stop, True otherwise
        """
        try:
            logger.debug(f"Key released: {key}")
            
            # Update key state
            if key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                state.set_key_state('ctrl', False)
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                state.set_key_state('shift', False)
            elif key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                state.set_key_state('alt', False)
            elif key == keyboard.Key.cmd or key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r:
                state.set_key_state('cmd', False)
            elif key == keyboard.Key.space:
                state.set_key_state('space', False)
            elif isinstance(key, keyboard.KeyCode) and hasattr(key, 'char') and key.char:
                char = key.char.lower()
                if char == 'd':
                    state.set_key_state('d', False)
                elif char == 'm':
                    state.set_key_state('m', False)
            
            # Stop listener if escape key is pressed
            if key == keyboard.Key.esc:
                logger.info("ESC key pressed - exiting application")
                return False
        
        except Exception as e:
            logger.error(f"Error in key release handler: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return True
    
    def _toggle_mute(self):
        """Toggle mute state."""
        # If currently recording, stop it
        if state.is_recording():
            state.stop_recording()
            logger.info("Stopping active recording due to mute toggle")
        
        # Toggle mute state
        state.toggle_mute()
        
        # Play feedback sound based on new state
        sound_type = 'muted' if state.is_muted() else 'unmuted'
        self.recorder.play_sound(sound_type)
        
        # Show notification of current mute state
        status = "MUTED" if state.is_muted() else "UNMUTED"
        
        # Use toast notification to show status
        try:
            # Import here to avoid circular imports
            from toast_notifications import send_notification
            send_notification(
                f"Microphone {status}",
                f"Voice control is {'paused' if state.is_muted() else 'active'}",
                "whisper-voice-mute-toggle",
                3,
                True
            )
        except Exception as e:
            logger.error(f"Could not show mute notification: {e}")

# Create a singleton instance
hotkeys = HotkeyManager()