# state_manager

State manager for the voice control system.
Centralizes state management to avoid global variables.

Source: `core/state_manager.py`

## Class: StateManager

Manages application state for the voice control system.

## Function: `start_recording(self)`

Set recording state to True and record start time.

## Function: `stop_recording(self)`

Set recording state to False.

## Function: `toggle_mute(self)`

Toggle mute state and notify listeners.

## Function: `is_recording(self)`

Check if currently recording.

## Function: `is_muted(self)`

Check if system is muted.

## Function: `set_key_state(self, key_name, state)`

Set state for a specific key.

## Function: `check_hotkey(self, *keys)`

Check if a combination of keys is pressed.

## Function: `enqueue_audio(self, audio_file, is_dictation=False, is_trigger=False)`

Add audio file to processing queue.

## Function: `get_next_audio(self, block=True, timeout=None)`

Get next audio file from queue.

## Function: `on_mute_change(self, callback)`

Register callback for mute state changes.

## Function: `on_recording_change(self, callback)`

Register callback for recording state changes.

## Function: `_notify_recording_change(self)`

Notify callbacks of recording state change.
