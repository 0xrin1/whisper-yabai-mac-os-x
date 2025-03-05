#!/usr/bin/env python3
"""
Audio recording module for voice control system.
Handles recording from microphone with smart silence detection.
"""

import os
import time
import tempfile
import subprocess
import pyaudio
import wave
import numpy as np
import logging
from typing import Optional, Dict, List, Any

from src.core.state_manager import state

logger = logging.getLogger('audio-recorder')

class AudioRecorder:
    """Records audio from microphone with configurable parameters."""
    
    def __init__(self):
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.p = pyaudio.PyAudio()
    
    def play_sound(self, sound_type: str) -> None:
        """Play a sound to indicate recording status.
        
        Args:
            sound_type: Type of sound to play ('start', 'stop', 'dictation', 'command')
        """
        sound_map = {
            'start': "/System/Library/Sounds/Tink.aiff",   # Higher pitch
            'stop': "/System/Library/Sounds/Basso.aiff",   # Lower pitch
            'dictation': "/System/Library/Sounds/Glass.aiff",  # Distinctive for dictation
            'command': "/System/Library/Sounds/Pop.aiff",  # Distinctive for commands
            'muted': "/System/Library/Sounds/Submarine.aiff", # For mute toggle
            'unmuted': "/System/Library/Sounds/Funk.aiff"  # For unmute toggle
        }
        
        sound_file = sound_map.get(sound_type)
        if not sound_file:
            return
            
        try:
            subprocess.run(["afplay", sound_file], check=False)
        except Exception as e:
            logger.error(f"Could not play {sound_type} sound: {e}")
    
    def start_recording(self, duration: Optional[int] = None, 
                        dictation_mode: bool = False,
                        trigger_mode: bool = False,
                        force: bool = False) -> Optional[str]:
        """
        Start recording audio for specified duration.
        
        Args:
            duration: Recording duration in seconds
            dictation_mode: If True, recorded audio will be transcribed as text
            trigger_mode: If True, this is a short recording to detect trigger words
            force: If True, will force recording even if already recording
        
        Returns:
            Path to the recorded WAV file, or None if recording failed
        """
        # Import error handler for better error handling
        from src.core.error_handler import handle_error

        try:
            # If force is True, reset the recording flag before continuing
            if state.is_recording() and force:
                logger.debug("Force flag set - resetting recording state")
                state.stop_recording()
                time.sleep(0.1)  # Brief pause to ensure flag propagation
            
            # Check if still recording
            if state.is_recording() and not trigger_mode and not force:
                logger.debug("Already recording, ignoring request")
                return None
                
            # Use environment variable if duration not specified
            if duration is None:
                if trigger_mode:
                    # Increased duration for trigger detection for better reliability
                    duration = 2.0  # 2.0 seconds for more reliable trigger word detection
                elif dictation_mode:
                    # Longer duration for dictation mode
                    duration = int(os.getenv('DICTATION_DURATION', '12'))
                else:
                    # Standard duration for commands, increased for reliability
                    duration = int(os.getenv('RECORDING_DURATION', '10'))
            
            logger.debug(f"Recording duration set to {duration} seconds")
            
            if not trigger_mode:
                state.start_recording()
                # Play a sound to indicate recording has started, but only for full recordings
                try:
                    self.play_sound('start')
                except Exception as sound_error:
                    handle_error(sound_error, logger, context="Sound playback", 
                                notification_text=None, should_raise=False)
                    # Continue even if sound fails
            else:
                # For trigger detection, we don't want to play sounds or show notifications
                logger.debug("Silent trigger detection started")
            
            # Show appropriate notification
            mode = "Dictation" if dictation_mode else "Command"
            logger.info(f"{mode} mode: Listening for {duration} seconds...")
            
            # Import here to avoid circular imports
            try:
                from src.ui.toast_notifications import notify_listening
                notify_listening(duration)
            except Exception as notify_error:
                handle_error(notify_error, logger, context="Notification", 
                            notification_text=None, should_raise=False)
                # Continue even if notification fails
            
            # Create a temporary WAV file
            try:
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_filename = temp_file.name
                temp_file.close()
                logger.debug(f"Created temporary WAV file: {temp_filename}")
            except Exception as file_error:
                handle_error(file_error, logger, context="Temporary file creation",
                            notification_text="Failed to create temporary file", should_raise=True)
                # If we can't create a temp file, we can't continue
                return None
            
            # Set up audio stream
            try:
                logger.debug("Opening audio stream for recording")
                
                # Get available input devices for better error messages
                available_inputs = []
                info = self.p.get_host_api_info_by_index(0)
                num_devices = info.get('deviceCount')
                
                for i in range(num_devices):
                    if self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels') > 0:
                        device_name = self.p.get_device_info_by_host_api_device_index(0, i).get('name')
                        available_inputs.append(f"Input device {i}: {device_name}")
                
                # Get default input device
                try:
                    device_info = self.p.get_default_input_device_info()
                    default_input_device_index = device_info.get('index')
                    device_name = device_info.get('name', 'Unknown')
                    logger.debug(f"Default input device: {device_name} (index: {default_input_device_index})")
                except IOError as device_error:
                    error_msg = (f"No default input device found: {device_error}. "
                                f"Available devices: {', '.join(available_inputs)}")
                    logger.error(error_msg)
                    
                    from src.ui.toast_notifications import notify_error
                    notify_error("No microphone available")
                    
                    state.stop_recording()
                    return None
                
                # Open stream with explicit input device index and settings
                stream = self.p.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    input_device_index=default_input_device_index,
                    frames_per_buffer=self.chunk
                )
                
                # Test if we can read from the stream
                try:
                    test_data = stream.read(self.chunk, exception_on_overflow=False)
                    if len(test_data) == 0:
                        logger.warning("Audio stream test got empty data - microphone may not be working properly")
                    else:
                        logger.debug(f"Audio stream test successful, read {len(test_data)} bytes")
                except Exception as read_error:
                    handle_error(read_error, logger, context="Audio stream test",
                                notification_text="Failed to read from microphone", should_raise=True)
                    stream.close()
                    state.stop_recording()
                    return None
                    
                logger.debug("Audio stream opened successfully and tested")
                
            except OSError as e:
                error_msg = f"Failed to open audio stream: {e}"
                help_msg = "\n".join([
                    "Possible solutions:",
                    "1. Make sure your microphone is connected and not in use by another application",
                    "2. Check that macOS has microphone permissions granted for this application",
                    "3. Try a different microphone or restart your computer",
                    f"Available input devices: {', '.join(available_inputs) if available_inputs else 'None found'}"
                ])
                logger.error(f"{error_msg}\n{help_msg}")
                
                # Show user-friendly notification
                from src.ui.toast_notifications import notify_error
                notify_error("Microphone access failed - check permissions")
                
                state.stop_recording()
                return None
        except Exception as setup_error:
            handle_error(setup_error, logger, context="Recording setup",
                        notification_text="Failed to start recording", should_raise=False)
            state.stop_recording()
            return None
        
        # Import error handler for better error handling
        from src.core.error_handler import handle_error
        
        frames = []
        frames_per_second = self.rate / self.chunk
        
        # For silence detection - adjust thresholds based on mode
        if trigger_mode:
            SILENCE_THRESHOLD = 155  # Threshold from voice training
            max_silence_seconds = 0.7  # Slightly longer timeout for trigger detection
        elif dictation_mode:
            SILENCE_THRESHOLD = 119  # Threshold from voice training
            max_silence_seconds = 4.5  # Longer timeout for dictation to avoid premature cutoff
        else:
            # For command mode, use even lower threshold and longer timeout
            SILENCE_THRESHOLD = 100  # Threshold from voice training
            max_silence_seconds = 5.5  # Much longer timeout for commands (5.5 seconds)
            
        silence_frames = 0
        max_silence_frames = int(frames_per_second * max_silence_seconds)
        
        # Set maximum recording duration
        max_duration = 60 if dictation_mode else 15  # 60 seconds for dictation, 15 for commands
        total_frames = int(frames_per_second * max_duration)
        
        # Minimum recording duration - increased to ensure we get enough audio
        if trigger_mode:
            min_duration = 1.5  # Trigger detection at least 1.5 seconds for better detection
        elif dictation_mode:
            min_duration = 4  # At least 4 seconds for dictation to avoid premature cutoff
        else:
            min_duration = 4  # At least 4 seconds for commands to avoid premature cutoff
            
        min_frames = int(frames_per_second * min_duration)
        
        logger.debug(f"Beginning smart recording (max: {max_duration}s, min: {min_duration}s, silence timeout: {max_silence_seconds}s)")
        
        # Force a delay to ensure audio system is ready
        time.sleep(0.1)
        
        frames_recorded = 0
        start_time = time.time()
        has_speech = False
        recording_successful = False
        
        try:
            # Record until max duration reached, user stops recording, or silence detected after speech
            while frames_recorded < total_frames and state.is_recording():
                try:
                    # Read audio with a timeout to ensure we don't get stuck
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    frames.append(data)
                    frames_recorded += 1
                    
                    # Once we have at least one frame, we've started recording successfully
                    if frames_recorded == 1:
                        recording_successful = True
                    
                    # Convert to numpy array for audio processing
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    
                    # Calculate audio energy/volume
                    energy = np.abs(audio_data).mean()
                    
                    # Print progress every second (approximate)
                    if frames_recorded % int(frames_per_second) == 0:
                        seconds_recorded = frames_recorded / frames_per_second
                        current_time = time.time()
                        elapsed_real = current_time - start_time
                        
                        logger.debug(f"Recorded {seconds_recorded:.1f} sec (real: {elapsed_real:.1f}s), " 
                              f"Energy: {energy:.0f}")
                    
                    # Detect speech vs silence
                    if energy > SILENCE_THRESHOLD:
                        has_speech = True
                        silence_frames = 0
                    else:
                        silence_frames += 1
                        
                        # If we've recorded enough frames and detected sufficient silence after speech,
                        # end the recording automatically - but add special handling for command mode
                        if has_speech and frames_recorded > min_frames and silence_frames >= max_silence_frames:
                            # For regular command mode (not trigger or dictation), we want to be more careful
                            if not trigger_mode and not dictation_mode:
                                # Make sure we've captured enough total audio
                                min_seconds_required = 3.0  # At least 3 seconds
                                seconds_recorded = frames_recorded / frames_per_second
                                
                                if seconds_recorded < min_seconds_required:
                                    # Keep recording even if silence detected
                                    logger.debug(f"Ignoring silence detection as we need at least {min_seconds_required}s " +
                                          f"(currently: {seconds_recorded:.1f}s)")
                                    continue
                            
                            # OK to stop recording now
                            logger.debug(f"Stopping recording after detecting {silence_frames/frames_per_second:.1f}s of silence")
                            break
                            
                except Exception as rec_err:
                    handle_error(rec_err, logger, context="Reading audio frame", 
                                 notification_text=None, should_raise=False)
                    time.sleep(0.01)  # Small delay to avoid tight loop on error
                    
        except KeyboardInterrupt:
            logger.debug("Recording interrupted by user")
        except Exception as rec_loop_err:
            handle_error(rec_loop_err, logger, context="Recording loop", 
                         notification_text="Recording interrupted", should_raise=False)
            
        # Final timing check    
        elapsed = time.time() - start_time
        logger.debug(f"Recording complete - {frames_recorded} frames in {elapsed:.2f} seconds")
        
        # If we recorded for less than 80% of the intended time, log a warning
        if elapsed < (duration * 0.8) and state.is_recording():
            logger.warning(f"Recording completed prematurely: {elapsed:.2f}s instead of {duration}s")
        
        # Check if we've actually recorded anything
        if frames_recorded == 0:
            logger.error("No audio frames recorded - microphone may not be working")
            from src.ui.toast_notifications import notify_error
            notify_error("Failed to record audio - check microphone")
            state.stop_recording()
            
            # Cleanup
            try:
                stream.stop_stream()
                stream.close()
            except Exception as cleanup_err:
                handle_error(cleanup_err, logger, context="Stream cleanup after empty recording", 
                             notification_text=None, should_raise=False)
                
            return None
            
        # We have some frames, proceed with normal recording completion
        logger.debug("Stopping and closing audio stream")
        try:
            stream.stop_stream()
            stream.close()
        except Exception as stream_err:
            handle_error(stream_err, logger, context="Closing audio stream", 
                         notification_text=None, should_raise=False)
            # Continue anyway - we already have the frames
        
        # Save the recorded data as a WAV file
        logger.debug(f"Writing {len(frames)} audio frames to {temp_filename}")
        try:
            wf = wave.open(temp_filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.format))
            wf.setframerate(self.rate)
            
            # Join frames and write to file
            joined_frames = b''.join(frames)
            logger.debug(f"Joined audio data is {len(joined_frames)} bytes")
            wf.writeframes(joined_frames)
            wf.close()
            
            # Verify file exists and has content
            if os.path.exists(temp_filename):
                file_size = os.path.getsize(temp_filename)
                logger.debug(f"WAV file size: {file_size} bytes")
                if file_size < 1000:
                    logger.warning("WAV file seems very small, may not contain enough audio")
            else:
                logger.error(f"WAV file not found after writing: {temp_filename}")
                raise FileNotFoundError(f"WAV file not found: {temp_filename}")
                
        except Exception as wav_err:
            handle_error(wav_err, logger, context="Saving WAV file", 
                         notification_text="Failed to save recording", should_raise=True)
            state.stop_recording()
            return None
        
        logger.info(f"Recording saved to {temp_filename}")
        state.stop_recording()
        
        # Play a sound to indicate recording has ended
        try:
            self.play_sound('stop')
        except Exception as sound_err:
            handle_error(sound_err, logger, context="Sound playback", 
                        notification_text=None, should_raise=False)
            # Continue even if sound fails
        
        # Add to processing queue with appropriate flags
        try:
            if trigger_mode:
                logger.debug(f"Adding to queue as trigger detection: {temp_filename}")
                state.enqueue_audio(temp_filename, False, True)
            elif dictation_mode:
                logger.debug(f"Adding to queue as dictation: {temp_filename}")
                state.enqueue_audio(temp_filename, True, False)
            else:
                logger.debug(f"Adding to queue as command: {temp_filename}")
                state.enqueue_audio(temp_filename, False, False)
                
            # Send a notification that recording completed successfully
            if not trigger_mode:  # Don't show for trigger recordings
                try:
                    from src.ui.toast_notifications import notify_processing
                    notify_processing()
                except Exception as notify_err:
                    handle_error(notify_err, logger, context="Recording completion notification", 
                                notification_text=None, should_raise=False)
                    
        except Exception as queue_err:
            handle_error(queue_err, logger, context="Enqueueing audio", 
                         notification_text="Failed to process recording", should_raise=False)
            # Return the filename anyway so it can be handled upstream
            
        # Return the filename so caller can check it
        return temp_filename
    
    def stop_recording(self):
        """Stop the current recording."""
        state.stop_recording()
        logger.info("Recording stopped.")
    
    def cleanup(self):
        """Clean up PyAudio resources."""
        self.p.terminate()