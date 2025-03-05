# hotkey_manager

Hotkey manager for voice control system.
Manages keyboard shortcuts for system control.

Source: `utils/hotkey_manager.py`

## Class: HotkeyManager

Manages keyboard hotkeys for voice control system.

## Function: `__init__(self)`

Initialize the hotkey manager.

## Function: `start(self)`

Start listening for keyboard hotkeys.

## Function: `stop(self)`

Stop listening for keyboard hotkeys.

## Function: `_on_press(self, key)`

Handle key press events.
        
        Args:
            key: The key that was pressed

## Function: `_on_release(self, key)`

Handle key release events.
        
        Args:
            key: The key that was released
        
        Returns:
            bool: False if the listener should stop, True otherwise

## Function: `_toggle_mute(self)`

Toggle mute state.

