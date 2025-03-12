#!/usr/bin/env python3
"""
Continuous recording module for voice control system.
Manages a rolling buffer of audio to detect trigger words.
"""

import time
import threading
import pyaudio
import numpy as np
import logging

from src.core.state_manager import state
from src.audio.trigger_detection import TriggerDetector

logger = logging.getLogger("continuous-recorder")


class ContinuousRecorder:
    """Records continuously in the background with a rolling buffer."""

    def __init__(self, buffer_seconds=5):
        """Initialize continuous recorder.

        Args:
            buffer_seconds: Number of seconds to keep in the rolling buffer
        """
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.buffer_seconds = buffer_seconds

        # Calculate buffer size
        self.frames_per_second = self.rate / self.chunk
        self.max_buffer_frames = int(self.frames_per_second * self.buffer_seconds)

        # Detection settings
        self.energy_threshold = 137  # Threshold from voice training
        self.silence_timeout = 0.8  # Seconds of silence before processing buffer

        # Add a cooldown mechanism to prevent rapid re-triggering
        self.last_processing_time = 0
        self.min_processing_interval = 2.0  # Minimum seconds between processing events

        # Create trigger detector
        self.trigger_detector = TriggerDetector()

        # Thread control
        self.running = False
        self.thread = None

    def start(self):
        """Start continuous recording in a background thread."""
        if self.running:
            logger.debug("Continuous recording already running")
            return

        logger.info("Starting continuous recording...")
        self.running = True
        self.thread = threading.Thread(target=self._recording_thread)
        self.thread.daemon = True
        self.thread.start()

        logger.debug(f"Continuous recording thread started: {self.thread.name}")

    def stop(self):
        """Stop continuous recording."""
        if not self.running:
            return

        logger.info("Stopping continuous recording...")
        self.running = False

        if self.thread:
            self.thread.join(2.0)  # Wait up to 2 seconds for thread to end

    def _recording_thread(self):
        """Main recording thread function."""
        logger.debug("Continuous recording thread starting")

        try:
            # Initialize audio recording
            p = pyaudio.PyAudio()

            # Initialize energy detection variables
            silence_frames = 0
            max_silence_frames = int(self.rate / self.chunk * self.silence_timeout)
            has_speech = False

            # Get default input device
            default_input_device_index = p.get_default_input_device_info().get("index")
            logger.debug(
                f"Continuous recording using input device index: {default_input_device_index}"
            )

            # Open stream with explicit input device index
            try:
                stream = p.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    input_device_index=default_input_device_index,
                    frames_per_buffer=self.chunk,
                )
                logger.debug("Continuous recording stream opened successfully")
            except Exception as e:
                logger.error(
                    f"Failed to open audio stream for continuous recording: {e}"
                )
                self.running = False
                return

            logger.debug("Beginning continuous audio buffering")

            # Main recording loop
            while self.running:
                # Skip recording if muted
                if state.is_muted():
                    time.sleep(0.1)
                    continue

                # If global recording is active, pause our continuous recording
                # This means another recording operation (like dictation) is in progress
                if state.is_recording():
                    logger.debug(
                        "Pausing continuous recording while active recording is in progress"
                    )
                    time.sleep(0.1)
                    continue

                try:
                    # Read audio data
                    data = stream.read(self.chunk, exception_on_overflow=False)

                    # Calculate audio energy/volume
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    energy = np.abs(audio_data).mean()

                    # Log energy occasionally (every 2 seconds approximately)
                    if len(state.audio_buffer) % int(self.frames_per_second * 2) == 0:
                        logger.debug(
                            f"Audio energy level: {energy:.0f}, buffer size: {len(state.audio_buffer)}"
                        )

                    # Detect speech activity
                    if energy > self.energy_threshold:
                        # High energy detected - could be speech
                        if not has_speech:
                            logger.debug(
                                f"Voice activity detected, energy: {energy:.0f}"
                            )
                            has_speech = True
                        silence_frames = 0
                    else:
                        # Low energy - might be silence
                        silence_frames += 1

                        # If we had speech and now detect enough silence, trigger processing
                        if has_speech and silence_frames >= max_silence_frames:
                            # Check cooldown period to prevent rapid re-triggering
                            current_time = time.time()
                            time_since_last = current_time - self.last_processing_time

                            if time_since_last < self.min_processing_interval:
                                logger.debug(
                                    f"Cooldown active - skipping processing ({time_since_last:.1f}s < {self.min_processing_interval:.1f}s)"
                                )
                                has_speech = False
                                silence_frames = 0
                                continue

                            logger.debug(
                                f"Potential trigger word - processing buffer after {silence_frames/self.frames_per_second:.1f}s silence"
                            )

                            # Update last processing time
                            self.last_processing_time = current_time

                            # We need to be careful about setting recording here to prevent race conditions
                            # Only process if we're not already in recording mode
                            if not state.is_recording():
                                # First set recording to True to block other recordings
                                state.start_recording()
                                # Process buffer in a separate thread to avoid blocking the continuous recording
                                process_thread = threading.Thread(
                                    target=self._process_buffer, daemon=True
                                )
                                process_thread.start()

                                # Wait a moment before continuing to prevent overlapping processing
                                # This gives the system time to properly handle the current speech segment
                                time.sleep(0.5)
                            else:
                                logger.debug(
                                    "Skipping buffer processing - already recording"
                                )

                            # Reset speech detection
                            has_speech = False
                            # Add a cooldown period to prevent immediate re-triggering
                            silence_frames = 0

                    # Add data to the rolling buffer with thread safety
                    with state.audio_buffer_lock:
                        state.audio_buffer.append(data)
                        # Keep buffer at maximum size
                        while len(state.audio_buffer) > self.max_buffer_frames:
                            state.audio_buffer.pop(0)

                except Exception as e:
                    logger.error(f"Error in continuous recording: {e}")
                    time.sleep(0.1)  # Brief pause on error

        except Exception as e:
            logger.error(f"Continuous recording thread error: {e}")
            import traceback

            logger.error(traceback.format_exc())
        finally:
            # Clean up resources
            try:
                stream.stop_stream()
                stream.close()
                p.terminate()
                logger.debug("Audio resources cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up audio resources: {e}")

            self.running = False

    def _process_buffer(self):
        """Process the audio buffer to detect trigger words."""
        try:
            # Make a copy of the buffer to process
            with state.audio_buffer_lock:
                if (
                    len(state.audio_buffer) < 10
                ):  # At least some minimum amount of frames
                    logger.debug("Buffer too small to process")
                    # Reset recording flag since we're aborting
                    state.stop_recording()
                    return

                buffer_copy = state.audio_buffer.copy()

            # Process buffer with trigger detector
            detection_result = self.trigger_detector.process_audio_buffer(buffer_copy)

            # Handle detection if needed
            if detection_result["detected"]:
                self.trigger_detector.handle_detection(detection_result)
            else:
                # Reset recording flag to allow future processing
                logger.debug("No trigger words detected in buffer")
                state.stop_recording()

        except Exception as e:
            logger.error(f"Error processing audio buffer: {e}")
            import traceback

            logger.error(traceback.format_exc())

            # Always reset recording flag in case of error
            state.stop_recording()
