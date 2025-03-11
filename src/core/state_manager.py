#!/usr/bin/env python3
"""
State manager for the voice control system.
Centralizes state management to avoid global variables.
"""

import threading
import time
import logging
import queue

logger = logging.getLogger("state-manager")


class StateManager:
    """Manages application state for the voice control system."""

    def __init__(self):
        # Recording state
        self.recording = False
        self.recording_start_time = 0
        self.audio_queue = queue.Queue()

        # Audio processing state
        self.whisper_model = None
        self.model_size = "medium"  # Default, will be overridden from env

        # Modality state
        self.muted = False
        self.continuous_listening = True

        # Trigger detection
        self.trigger_detected = False
        self.trigger_buffer = []
        self.command_trigger = "hey"
        self.dictation_trigger = "type"

        # Mutex for trigger detection
        self.trigger_detection_running = False
        self.trigger_mutex = threading.Lock()

        # Audio buffer
        self.audio_buffer = []
        self.audio_buffer_seconds = 5
        self.audio_buffer_lock = threading.Lock()

        # Hotkey tracking
        self.key_states = {
            "ctrl": False,
            "shift": False,
            "alt": False,
            "cmd": False,
            "space": False,
            "d": False,
            "m": False,
        }

        # Callbacks
        self._on_mute_callbacks = []
        self._on_recording_change_callbacks = []

    def start_recording(self):
        """Set recording state to True and record start time."""
        self.recording = True
        self.recording_start_time = time.time()
        self._notify_recording_change()
        logger.debug("Recording state set to True")

    def stop_recording(self):
        """Set recording state to False."""
        self.recording = False
        self._notify_recording_change()
        logger.debug("Recording state set to False")

    def toggle_mute(self):
        """Toggle mute state and notify listeners."""
        self.muted = not self.muted
        status = "MUTED" if self.muted else "UNMUTED"
        logger.info(f"Microphone {status}")

        # Notify registered callbacks
        for callback in self._on_mute_callbacks:
            try:
                callback(self.muted)
            except Exception as e:
                logger.error(f"Error in mute callback: {e}")

    def is_recording(self):
        """Check if currently recording."""
        return self.recording

    def is_muted(self):
        """Check if system is muted."""
        return self.muted

    def set_key_state(self, key_name, state):
        """Set state for a specific key."""
        if key_name in self.key_states:
            self.key_states[key_name] = state

    def check_hotkey(self, *keys):
        """Check if a combination of keys is pressed."""
        return all(self.key_states.get(k, False) for k in keys)

    def enqueue_audio(self, audio_file, is_dictation=False, is_trigger=False):
        """Add audio file to processing queue."""
        self.audio_queue.put((audio_file, is_dictation, is_trigger))
        logger.debug(
            f"Added to queue: {audio_file} (dictation={is_dictation}, trigger={is_trigger})"
        )

    def get_next_audio(self, block=True, timeout=None):
        """Get next audio file from queue."""
        try:
            return self.audio_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def on_mute_change(self, callback):
        """Register callback for mute state changes."""
        if callback not in self._on_mute_callbacks:
            self._on_mute_callbacks.append(callback)

    def on_recording_change(self, callback):
        """Register callback for recording state changes."""
        if callback not in self._on_recording_change_callbacks:
            self._on_recording_change_callbacks.append(callback)

    def _notify_recording_change(self):
        """Notify callbacks of recording state change."""
        for callback in self._on_recording_change_callbacks:
            try:
                callback(self.recording)
            except Exception as e:
                logger.error(f"Error in recording callback: {e}")


# Create a singleton instance
state = StateManager()
