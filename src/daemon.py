#!/usr/bin/env python3
"""
Voice command daemon using Whisper and Yabai for Mac OS X control.
Now includes JARVIS-style conversational assistant capabilities.
"""

import os
import re
import time
import json
import subprocess
import threading
import queue
import logging
import signal
import tempfile
import pyaudio
import wave
import numpy as np
import whisper
import pyautogui
from pynput import keyboard
from dotenv import load_dotenv

# Import our LLM interpreter
from llm_interpreter import CommandInterpreter
# Import assistant module (for JARVIS-like functionality)
import assistant
import speech_synthesis as tts
# Import toast notifications
from toast_notifications import (
    notify_listening, 
    notify_processing, 
    notify_command_executed, 
    notify_error
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('voice-control')

# Set debug level for keyboard detection
# Comment this out for normal operation
logger.setLevel(logging.DEBUG)

# Load environment variables
load_dotenv()

# Global variables
RECORDING = False
AUDIO_QUEUE = queue.Queue()
WHISPER_MODEL = None
MODEL_SIZE = os.getenv('WHISPER_MODEL_SIZE', 'tiny')
COMMANDS = {}

class AudioRecorder:
    """Records audio from microphone when activated."""
    
    def __init__(self):
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.p = pyaudio.PyAudio()
        
    # This method is defined again below with more parameters
    # Removing this duplicate definition
        
    def _play_start_sound(self):
        """Play a sound to indicate recording has started."""
        try:
            # Use macOS built-in 'Tink' sound (higher pitch)
            subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], check=False)
        except Exception as e:
            logger.error(f"Could not play start sound: {e}")
            
    def _play_stop_sound(self):
        """Play a sound to indicate recording has stopped."""
        try:
            # Use macOS built-in 'Basso' sound (lower pitch)
            subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff"], check=False)
        except Exception as e:
            logger.error(f"Could not play stop sound: {e}")
            
    def start_recording(self, duration=None, dictation_mode=False, trigger_mode=False, force=False):
        """
        Start recording audio for specified duration.
        
        Args:
            duration (int, optional): Recording duration in seconds
            dictation_mode (bool): If True, recorded audio will be transcribed directly to text
                                  rather than interpreted as a command
            trigger_mode (bool): If True, this is a short recording to detect trigger words
            force (bool): If True, will force recording even if RECORDING flag is True
        """
        global RECORDING, TRIGGER_DETECTED, TRIGGER_BUFFER
        
        # If force is True, reset the RECORDING flag before continuing
        if RECORDING and force:
            print("DEBUG: Force flag set - resetting RECORDING flag in start_recording")
            RECORDING = False
            time.sleep(0.1)  # Brief pause to ensure flag propagation
        
        # Now check if still recording
        if RECORDING and not trigger_mode and not force:
            print("DEBUG: Already recording, ignoring request")
            return
            
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
            
        print(f"DEBUG: Recording duration set to {duration} seconds")
        
        if not trigger_mode:
            RECORDING = True
            print("DEBUG: RECORDING flag set to True")
            
            # Play a sound to indicate recording has started, but only for full recordings
            self._play_start_sound()
        else:
            # For trigger detection, we don't want to play sounds or show notifications
            print("DEBUG: Silent trigger detection started")
            
        # Reset trigger state if this is a full recording
        if not trigger_mode:
            TRIGGER_DETECTED = False
            TRIGGER_BUFFER = []
        
        # Show appropriate notification
        mode = "Dictation" if dictation_mode else "Command"
        print(f"DEBUG: {mode} mode activated - recording for {duration} seconds")
        if dictation_mode:
            logger.info(f"Dictation mode: Listening for {duration} seconds...")
            notify_listening(duration)
        else:
            logger.info(f"Command mode: Listening for {duration} seconds...")
            notify_listening(duration)
        
        # Create a temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_filename = temp_file.name
        temp_file.close()
        print(f"DEBUG: Created temporary WAV file: {temp_filename}")
        
        # Set up audio stream
        try:
            print("DEBUG: Opening audio stream for recording")
            print(f"DEBUG: Audio format: {self.format}, Channels: {self.channels}, Rate: {self.rate}, Chunk: {self.chunk}")
            
            # List available audio devices
            info = self.p.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            print(f"DEBUG: Found {num_devices} audio devices")
            
            default_input_device_index = self.p.get_default_input_device_info().get('index')
            print(f"DEBUG: Default input device index: {default_input_device_index}")
            
            # Show input devices
            for i in range(0, num_devices):
                if (self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                    name = self.p.get_device_info_by_host_api_device_index(0, i).get('name')
                    print(f"DEBUG: Input device {i}: {name}")
            
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
            test_data = stream.read(self.chunk, exception_on_overflow=False)
            if len(test_data) > 0:
                print(f"DEBUG: Audio stream test successful - got {len(test_data)} bytes")
            else:
                print("WARNING: Audio stream test got empty data")
                
            print("DEBUG: Audio stream opened successfully and tested")
            
        except OSError as e:
            logger.error(f"Failed to open audio stream: {e}")
            logger.error("Make sure your microphone is connected and permissions are granted.")
            print(f"DEBUG: Audio stream error: {e}")
            RECORDING = False
            return
        
        frames = []
        frames_per_second = self.rate / self.chunk
        
        # For silence detection - adjust thresholds based on mode
        # Lower threshold means more audio will be considered "speech" rather than "silence"
        if trigger_mode:
            SILENCE_THRESHOLD = 500  # Standard for trigger detection
            max_silence_seconds = 0.5  # Quick timeout for trigger detection
        elif dictation_mode:
            SILENCE_THRESHOLD = 350  # Even lower for dictation to catch softer speech
            max_silence_seconds = 4.0  # Longer timeout for dictation to avoid premature cutoff
        else:
            # For command mode, use even lower threshold and longer timeout
            SILENCE_THRESHOLD = 250  # Much lower threshold to avoid cutting off commands
            max_silence_seconds = 5.0  # Much longer timeout for commands (5 seconds)
            
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
        
        print(f"DEBUG: Beginning smart recording (max: {max_duration}s, min: {min_duration}s, silence timeout: {max_silence_seconds}s)")
        
        # Force a delay to ensure audio system is ready
        time.sleep(0.1)
        
        frames_recorded = 0
        start_time = time.time()
        has_speech = False
        
        try:
            # Record until max duration reached, user stops recording, or silence detected after speech
            while frames_recorded < total_frames and RECORDING:
                try:
                    # Read audio with a timeout to ensure we don't get stuck
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    frames.append(data)
                    frames_recorded += 1
                    
                    # Convert to numpy array for audio processing
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    
                    # Calculate audio energy/volume
                    energy = np.abs(audio_data).mean()
                    
                    # Print progress every second (approximate)
                    if frames_recorded % int(frames_per_second) == 0:
                        seconds_recorded = frames_recorded / frames_per_second
                        current_time = time.time()
                        elapsed_real = current_time - start_time
                        
                        print(f"DEBUG: Recorded {seconds_recorded:.1f} sec (real: {elapsed_real:.1f}s), " 
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
                                    print(f"DEBUG: Ignoring silence detection as we need at least {min_seconds_required}s " +
                                          f"(currently: {seconds_recorded:.1f}s)")
                                    continue
                            
                            # OK to stop recording now
                            print(f"DEBUG: Stopping recording after detecting {silence_frames/frames_per_second:.1f}s of silence")
                            break
                            
                except Exception as rec_err:
                    print(f"DEBUG: Error reading audio frame: {rec_err}")
                    time.sleep(0.01)  # Small delay to avoid tight loop on error
                    
        except KeyboardInterrupt:
            print("DEBUG: Recording interrupted by user")
            
        # Final timing check    
        elapsed = time.time() - start_time
        print(f"DEBUG: Recording complete - {frames_recorded} frames in {elapsed:.2f} seconds")
        
        # If we recorded for less than 80% of the intended time, log a warning
        if elapsed < (duration * 0.8) and RECORDING:
            print(f"WARNING: Recording completed too quickly ({elapsed:.2f} sec instead of {duration} sec)!")
            logger.warning(f"Recording completed prematurely: {elapsed:.2f}s instead of {duration}s")
            
        print("DEBUG: Stopping and closing audio stream")
        stream.stop_stream()
        stream.close()
        print("DEBUG: Audio stream closed")
        
        # Save the recorded data as a WAV file
        print(f"DEBUG: Writing {len(frames)} audio frames to {temp_filename}")
        try:
            wf = wave.open(temp_filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.format))
            wf.setframerate(self.rate)
            
            # Join frames and write to file
            joined_frames = b''.join(frames)
            print(f"DEBUG: Joined audio data is {len(joined_frames)} bytes")
            wf.writeframes(joined_frames)
            wf.close()
            print(f"DEBUG: WAV file written successfully: {temp_filename}")
            
            # Verify file exists and has content
            if os.path.exists(temp_filename):
                file_size = os.path.getsize(temp_filename)
                print(f"DEBUG: WAV file size: {file_size} bytes")
                if file_size < 1000:
                    print("WARNING: WAV file seems very small, may not contain enough audio")
            else:
                print(f"ERROR: WAV file not found after writing: {temp_filename}")
                
        except Exception as wav_err:
            print(f"DEBUG: Error saving WAV file: {wav_err}")
            # Try to continue anyway
        
        logger.info(f"Recording saved to {temp_filename}")
        RECORDING = False
        print("DEBUG: RECORDING flag set to False")
        
        # Play a sound to indicate recording has ended
        self._play_stop_sound()
        print("DEBUG: Stop sound played")
        
        # Add to processing queue with appropriate flags
        if trigger_mode:
            print(f"DEBUG: Adding to queue as trigger detection: {temp_filename}")
            AUDIO_QUEUE.put((temp_filename, False, True))  # format: (path, is_dictation, is_trigger)
            print("DEBUG: Item added to queue with trigger flag")
        elif dictation_mode:
            print(f"DEBUG: Adding to queue as dictation: {temp_filename}")
            AUDIO_QUEUE.put((temp_filename, True, False))  # format: (path, is_dictation, is_trigger)
            print("DEBUG: Item added to queue with dictation flag")
        else:
            print(f"DEBUG: Adding to queue as command: {temp_filename}")
            AUDIO_QUEUE.put((temp_filename, False, False))  # format: (path, is_dictation, is_trigger)
            print("DEBUG: Item added to queue")
            
        # Return the filename so caller can check it
        return temp_filename
    
    def stop_recording(self):
        """Stop the current recording."""
        global RECORDING
        RECORDING = False
        logger.info("Recording stopped.")
    
    def cleanup(self):
        """Clean up PyAudio resources."""
        self.p.terminate()


class CommandProcessor:
    """Processes voice commands and executes corresponding actions."""
    
    def __init__(self):
        # Load command mappings
        self.load_commands()
        
        # Initialize LLM interpreter
        model_path = os.getenv('LLM_MODEL_PATH')
        self.llm_interpreter = CommandInterpreter(model_path)
        self.use_llm = os.getenv('USE_LLM', 'true').lower() == 'true'
        
        if self.use_llm:
            logger.info("LLM command interpretation enabled")
        else:
            logger.info("Using simple command parsing (LLM disabled)")
    
    def load_commands(self):
        """Load command mappings from commands.json if it exists."""
        global COMMANDS
        
        default_commands = {
            "open": self.open_application,
            "focus": self.focus_application,
            "type": self.type_text,
            "move": self.move_window,
            "resize": self.resize_window,
            "space": self.move_to_space,
            "maximize": self.maximize_window,
            "close": self.close_window,
            "click": self.click_mouse,
        }
        
        try:
            with open('commands.json', 'r') as f:
                custom_data = json.load(f)
                if 'custom_commands' in custom_data:
                    default_commands.update(custom_data['custom_commands'])
                else:
                    default_commands.update(custom_data)
        except FileNotFoundError:
            logger.warning("commands.json not found, using default commands only")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing commands.json: {e}")
        
        COMMANDS = default_commands
    
    def execute_command(self, command_text):
        """Parse and execute the given command."""
        logger.info(f"Processing: {command_text}")
        
        # Clean and normalize the text
        clean_text = command_text.lower().strip()
        
        if not clean_text:
            logger.warning("Empty command received")
            notify_error("Empty command received")
            return
            
        # Check for dictation mode command first - with more robust detection
        dictation_keywords = ["dictate", "dictation", "start dictation", "begin dictation", 
                             "start typing", "take dictation", "type this", "type what i say",
                             "typing mode", "write this", "write what i say", "write this down",
                             "take notes", "voice typing", "text input", "text mode", 
                             "type", "typing", "write", "text"]  # Added simple keywords

        print(f"DEBUG: Checking for dictation command in: '{clean_text}'")
        
        # More lenient dictation mode detection - try multiple methods
        is_dictation_command = False
        
        # Method 1: Check if any of our dictation keywords are exact matches or contained in the command
        for keyword in dictation_keywords:
            # Exact match
            if keyword == clean_text:
                print(f"DEBUG: EXACT dictation keyword match: '{keyword}'")
                is_dictation_command = True
                break
                
            # Keyword surrounded by spaces (word boundary)
            if f" {keyword} " in f" {clean_text} ":
                print(f"DEBUG: WORD BOUNDARY dictation keyword match: '{keyword}'")
                is_dictation_command = True
                break
                
            # Keyword at start or end of text
            if clean_text.startswith(f"{keyword} ") or clean_text.endswith(f" {keyword}"):
                print(f"DEBUG: START/END dictation keyword match: '{keyword}'")
                is_dictation_command = True
                break
                
            # Substring match as last resort
            if keyword in clean_text:
                print(f"DEBUG: SUBSTRING dictation keyword match: '{keyword}'")
                is_dictation_command = True
                break
        
        # Method 2: Additional heuristic - if "type", "dict", "text" fragments are in the text
        if not is_dictation_command:
            for fragment in ["dict", "type", "text"]:
                if fragment in clean_text:
                    print(f"DEBUG: Found '{fragment}' fragment in command, treating as dictation")
                    is_dictation_command = True
                    break
                    
        print(f"DEBUG: Dictation command detection result: {is_dictation_command}")
        
        if is_dictation_command:
            logger.info(f"Detected dictation command in: '{clean_text}'")
            print(f"DEBUG: Voice command triggered dictation mode: '{clean_text}'")
            
            # Show clear feedback that we're switching to dictation mode
            print("DEBUG: Switching to DICTATION MODE - everything you say will be typed")
            logger.info("Switching to DICTATION MODE - your speech will be typed at cursor")
            
            try:
                # Visual notification of mode switch
                from toast_notifications import send_notification
                send_notification(
                    "Dictation Mode Active", 
                    "Speaking will now be typed as text | Pause to return to command mode",
                    "whisper-dictation-mode",
                    5,
                    True
                )
                
                # Play a distinctive sound to indicate mode switch
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
            except Exception as e:
                logger.error(f"Failed to show dictation mode notification: {e}")
            
            # Start dictation mode through the same path the hotkey would use
            # Use threading to avoid blocking this function
            time.sleep(0.5)  # Add a short delay before starting dictation
            threading.Thread(target=start_recording_thread, args=('dictation', True), daemon=True).start()
            return
        
        # Use LLM interpretation if enabled
        if self.use_llm and self.llm_interpreter.llm is not None:
            # Interpret the command using the LLM
            command, args = self.llm_interpreter.interpret_command(clean_text)
            
            # If we got a recognized command, execute it
            if command and command != "none" and command in COMMANDS:
                logger.info(f"LLM interpreted command: {command} with args: {args}")
                self._execute_parsed_command(command, args)
                return
            elif command == "none":
                logger.info("LLM determined input was not a command")
                return
            
            # If no command was recognized, try to get a dynamic response
            logger.info("No direct command match, trying dynamic interpretation")
            dynamic_response = self.llm_interpreter.generate_dynamic_response(clean_text)
            
            if dynamic_response.get('is_command', False):
                action = dynamic_response.get('action', '')
                app = dynamic_response.get('application', '')
                params = dynamic_response.get('parameters', [])
                
                logger.info(f"Dynamic interpretation: {action} {app} {params}")
                
                # Map dynamic response to executable commands
                if action == "open" and app:
                    self.open_application([app])
                    return
                elif action == "focus" and app:
                    self.focus_application([app])
                    return
                elif action == "maximize":
                    self.maximize_window([])
                    return
                elif action == "move" and params:
                    self.move_window(params)
                    return
                elif action == "resize" and params:
                    self.resize_window(params)
                    return
                elif action == "close":
                    self.close_window([])
                    return
                elif action == "type" and params:
                    self.type_text(params)
                    return
                # Enhanced dictation activation via LLM
                elif action in ["dictate", "dictation", "type", "write", "text", "input", "note", "notes"] or "dict" in action:
                    print(f"DEBUG: LLM suggested dictation mode with action: '{action}'")
                    logger.info(f"LLM interpreter triggered dictation mode with action: '{action}'")
                    
                    # Add a notification to clearly show we're entering dictation mode from LLM
                    try:
                        from toast_notifications import send_notification
                        send_notification(
                            "Starting Dictation Mode", 
                            "LLM detected dictation request - will type what you say",
                            "whisper-dictation-llm",
                            3,
                            True
                        )
                        
                        # Play a distinctive sound for dictation mode
                        subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
                    except Exception as e:
                        print(f"DEBUG: Failed to show LLM dictation notification: {e}")
                        
                    # Add a slight delay before starting dictation
                    time.sleep(0.5)
                    threading.Thread(target=start_recording_thread, args=('dictation', True), daemon=True).start()
                    return
            
            # If we still haven't found a command, fall back to simple parsing
            logger.info("Falling back to simple command parsing")
        
        # Simple command parsing (fallback)
        # Look for known command patterns
        if "open" in clean_text and " " in clean_text:
            # Extract app name after "open"
            app_part = clean_text[clean_text.find("open") + 4:].strip()
            logger.info(f"Detected open command for app: {app_part}")
            self.open_application([app_part])
            return
            
        if "browser" in clean_text or "safari" in clean_text or "chrome" in clean_text:
            logger.info("Detected browser command")
            self.execute_shell_command("open -a 'Safari'")
            return
            
        if "terminal" in clean_text:
            logger.info("Detected terminal command")
            self.execute_shell_command("open -a 'Terminal'")
            return
            
        if "maximize" in clean_text or "full screen" in clean_text:
            logger.info("Detected maximize command")
            self.maximize_window([])
            return
            
        # Explicit check for dictation mode as fallback - with improved detection
        dictation_fragments = ["dictate", "dictation", "dict", "type", "write", "text", "note"]
        
        for fragment in dictation_fragments:
            if fragment in clean_text:
                logger.info(f"Detected dictation command via simple parsing: '{fragment}' in '{clean_text}'")
                print(f"DEBUG: Simple parsing caught dictation command using fragment '{fragment}'")
                
                # Add a notification to clearly show we're entering dictation mode
                try:
                    from toast_notifications import send_notification
                    send_notification(
                        "Entering Dictation Mode", 
                        "Everything you say will be typed at cursor",
                        "whisper-dictation-simple",
                        3,
                        True
                    )
                except Exception as e:
                    print(f"DEBUG: Failed to show dictation notification: {e}")
                    
                # Start dictation mode directly
                time.sleep(0.5)  # Add a short delay before starting dictation
                threading.Thread(target=start_recording_thread, args=('dictation', True), daemon=True).start()
                return
        
        # Standard command processing
        parts = clean_text.split()
        
        if not parts:
            logger.warning("Empty command received")
            return
        
        # Extract the command and arguments
        command = parts[0]
        args = parts[1:]
        
        # Execute the parsed command
        self._execute_parsed_command(command, args)
    
    def _execute_parsed_command(self, command, args):
        """Execute a parsed command with its arguments."""
        # Check if command exists and execute it
        if command in COMMANDS:
            cmd_action = COMMANDS[command]
            if callable(cmd_action):
                try:
                    cmd_action(args)
                    # Show success notification
                    notify_command_executed(f"{command} {' '.join(args)}")
                except Exception as e:
                    logger.error(f"Error executing command '{command}': {e}")
                    notify_error(f"Error executing '{command}': {str(e)}")
            else:
                # Handle string command
                cmd_str = cmd_action
                
                # Check if command contains pyautogui
                if "pyautogui." in cmd_str:
                    try:
                        # We need to handle pyautogui commands directly
                        if "pyautogui.hotkey" in cmd_str:
                            # Extract the hotkey arguments
                            key_args = cmd_str.split("pyautogui.hotkey(")[1].split(")")[0]
                            keys = [k.strip("'\" ") for k in key_args.split(",")]
                            logger.info(f"Executing hotkey: {keys}")
                            pyautogui.hotkey(*keys)
                            notify_command_executed(f"Hotkey: {'+'.join(keys)}")
                        elif "pyautogui.write" in cmd_str:
                            # Extract the text to write
                            text = cmd_str.split("pyautogui.write(")[1].split(")")[0].strip("'\" ")
                            logger.info(f"Writing text: {text}")
                            pyautogui.write(text)
                            notify_command_executed(f"Type: {text}")
                        else:
                            logger.error(f"Unsupported pyautogui command: {cmd_str}")
                            notify_error(f"Unsupported command: {cmd_str}")
                    except Exception as e:
                        logger.error(f"Error executing pyautogui command: {e}")
                        notify_error(f"Error with keyboard/mouse command: {str(e)}")
                else:
                    # Handle shell command (Yabai or other)
                    success = self.execute_shell_command(cmd_str)
                    if success:
                        notify_command_executed(f"{command}: {cmd_str}")
                    else:
                        notify_error(f"Failed to run: {cmd_str}")
        else:
            logger.warning(f"Unknown command: {command}, looking in full text for commands")
            notify_error(f"Unknown command: {command}")
            
            # Try to find command in custom_commands even if not at start of sentence
            clean_text = " ".join([command] + args)
            for cmd_name, cmd_action in COMMANDS.items():
                if isinstance(cmd_name, str) and cmd_name in clean_text:
                    logger.info(f"Found command '{cmd_name}' in text")
                    # Recursive call to reuse the logic above
                    self._execute_parsed_command(cmd_name, [])
    
    def execute_shell_command(self, command):
        """Execute a shell command.
        
        Returns:
            bool: True if command succeeded, False otherwise
        """
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"Command executed: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Command execution failed: {e.stderr}")
            return False
    
    def open_application(self, args):
        """Open an application."""
        if not args:
            return
            
        app_name = " ".join(args)
        logger.info(f"Opening application: {app_name}")
        
        # Use open command to launch application
        self.execute_shell_command(f"open -a '{app_name}'")
    
    def focus_application(self, args):
        """Focus on an application using Yabai."""
        if not args:
            return
            
        app_name = " ".join(args)
        logger.info(f"Focusing application: {app_name}")
        
        # Use Yabai to focus the application
        self.execute_shell_command(f"yabai -m window --focus \"$(/usr/bin/grep -i '{app_name}' <(/usr/bin/yabai -m query --windows | /usr/bin/jq -r '.[].app') | head -n1)\"")
    
    def type_text(self, args):
        """Type text."""
        if not args:
            return
            
        text = " ".join(args)
        logger.info(f"Typing text: {text}")
        
        pyautogui.write(text)
    
    def move_window(self, args):
        """Move the focused window to a position."""
        if len(args) < 1:
            return
            
        direction = args[0]
        
        if direction in ["left", "right", "top", "bottom"]:
            self.execute_shell_command(f"yabai -m window --move {direction}")
        else:
            logger.warning(f"Unknown direction: {direction}")
    
    def resize_window(self, args):
        """Resize the focused window."""
        if len(args) < 1:
            return
            
        direction = args[0]
        
        if direction in ["left", "right", "top", "bottom"]:
            self.execute_shell_command(f"yabai -m window --resize {direction}:20:20")
        else:
            logger.warning(f"Unknown direction: {direction}")
    
    def move_to_space(self, args):
        """Move the focused window to a space."""
        if not args or not args[0].isdigit():
            return
            
        space = args[0]
        logger.info(f"Moving window to space: {space}")
        
        self.execute_shell_command(f"yabai -m window --space {space}")
    
    def maximize_window(self, args):
        """Maximize the focused window."""
        logger.info("Maximizing window")
        
        self.execute_shell_command("yabai -m window --toggle zoom-fullscreen")
    
    def close_window(self, args):
        """Close the focused window."""
        logger.info("Closing window")
        
        # Simulate Cmd+W
        pyautogui.hotkey('command', 'w')
    
    def click_mouse(self, args):
        """Click the mouse at the current position."""
        logger.info("Clicking mouse")
        
        pyautogui.click()


def process_audio():
    """Process audio files in the queue and convert to text using Whisper."""
    global WHISPER_MODEL
    
    print("DEBUG: Audio processing thread starting...")
    logger.info(f"Loading Whisper model: {MODEL_SIZE}")
    
    # Load the Whisper model
    try:
        print(f"DEBUG: Loading Whisper model '{MODEL_SIZE}'")
        start_time = time.time()
        WHISPER_MODEL = whisper.load_model(MODEL_SIZE)
        load_time = time.time() - start_time
        print(f"DEBUG: Whisper model loaded in {load_time:.2f} seconds")
    except Exception as model_err:
        print(f"ERROR: Failed to load Whisper model: {model_err}")
        logger.error(f"Failed to load Whisper model: {model_err}")
        return
    
    command_processor = CommandProcessor()
    
    # Set minimum confidence threshold for command processing
    min_confidence_threshold = float(os.getenv('MIN_CONFIDENCE', '0.5'))
    print(f"DEBUG: Confidence threshold: {min_confidence_threshold}")
    print("DEBUG: Audio processing thread ready and listening for queue items...")
    
    # Main processing loop
    while True:
        audio_file = None
        
        try:
            # Get the next audio file from the queue
            print("DEBUG: Waiting for item in audio queue...")
            audio_item = AUDIO_QUEUE.get()
            
            if audio_item is None:
                print("DEBUG: Found None in queue, exiting thread")
                break
            
            # Process audio item - determine mode and extract file path
            is_dictation_mode = False
            is_trigger_mode = False
            
            if isinstance(audio_item, tuple):
                if len(audio_item) == 3:
                    # New format: (file_path, is_dictation, is_trigger)
                    audio_file = audio_item[0]
                    is_dictation_mode = bool(audio_item[1])
                    is_trigger_mode = bool(audio_item[2])
                    
                    if is_trigger_mode:
                        print(f"DEBUG: Processing audio for trigger word detection")
                    else:
                        print(f"DEBUG: Processing audio in {'dictation' if is_dictation_mode else 'command'} mode")
                        
                elif len(audio_item) == 2:
                    # Old format: (file_path, is_dictation)
                    audio_file = audio_item[0]
                    is_dictation_mode = bool(audio_item[1])
                    print(f"DEBUG: Processing audio in {'dictation' if is_dictation_mode else 'command'} mode")
            elif isinstance(audio_item, str):
                # Simple file path - command mode
                audio_file = audio_item
                print("DEBUG: Processing audio in command mode")
            else:
                print(f"DEBUG: Unknown audio queue item format: {type(audio_item)}")
                AUDIO_QUEUE.task_done()
                continue
                
            if not os.path.exists(audio_file):
                print(f"ERROR: Audio file not found: {audio_file}")
                AUDIO_QUEUE.task_done()
                continue
                
            logger.info(f"Processing audio file: {audio_file}")
            notify_processing()
            
            # Transcribe audio using Whisper
            try:
                print(f"DEBUG: Starting Whisper transcription of {audio_file}")
                
                # Special handling for trigger detection mode
                if is_trigger_mode:
                    # Use process_trigger_audio function for trigger detection
                    trigger_detected = process_trigger_audio(audio_file)
                    print(f"DEBUG: Trigger detection result: {'Detected' if trigger_detected else 'Not detected'}")
                    
                    # Clean up the audio file
                    try:
                        os.unlink(audio_file)
                    except Exception as unlink_err:
                        print(f"DEBUG: Failed to delete temp file: {unlink_err}")
                    
                    AUDIO_QUEUE.task_done()
                    continue
                
                # Normal transcription for command/dictation modes
                result = WHISPER_MODEL.transcribe(audio_file)
                transcription = result["text"].strip()
                confidence = result.get("confidence", 1.0)
                print(f"DEBUG: Transcription: '{transcription}', confidence: {confidence:.2f}")
                
                # Clean up the audio file
                try:
                    os.unlink(audio_file)
                except Exception as unlink_err:
                    print(f"DEBUG: Failed to delete temp file: {unlink_err}")
                
                # Always make sure RECORDING flag is reset even if transcription is empty
                RECORDING = False
                print("DEBUG: Reset RECORDING flag to False after processing")
                
                # Skip empty or noise transcriptions
                if not transcription or len(transcription) < 3 or all(c.isspace() or c in ".,;!?" for c in transcription):
                    logger.warning(f"Empty or noise transcription: '{transcription}'")
                    notify_error("No clear speech detected")
                    AUDIO_QUEUE.task_done()
                    continue
                
                # Process based on mode
                if is_dictation_mode:
                    print(f"DEBUG: Processing as dictation text: '{transcription}'")
                    process_dictation(transcription)
                    print("DEBUG: Dictation processing completed")
                elif confidence >= min_confidence_threshold:
                    print("DEBUG: ========== PROCESSING COMMAND ==========")
                    print(f"DEBUG: Processing as command: '{transcription}'")
                    
                    # Try executing the command
                    try:
                        command_processor.execute_command(transcription)
                        print("DEBUG: Command processing completed successfully")
                        
                        # Show a clear notification that the command was recognized 
                        try:
                            from toast_notifications import send_notification
                            send_notification(
                                "Command Recognized", 
                                f"Processing: {transcription}",
                                "whisper-command-recognized",
                                3,
                                True
                            )
                        except Exception as e:
                            print(f"DEBUG: Failed to show command notification: {e}")
                            
                    except Exception as e:
                        print(f"DEBUG: Error executing command: {e}")
                        import traceback
                        print(f"DEBUG: {traceback.format_exc()}")
                        
                    print("DEBUG: Command processing flow completed")
                else:
                    logger.warning(f"Low confidence command: {confidence:.2f} < {min_confidence_threshold}")
                    notify_error(f"Low confidence: {transcription}")
                
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                notify_error(f"Failed to transcribe audio: {str(e)}")
                # Clean up if error occurred
                if audio_file and os.path.exists(audio_file):
                    try:
                        os.unlink(audio_file)
                    except:
                        pass
            
            AUDIO_QUEUE.task_done()
            
            # After processing, if continuous listening is enabled and not muted, 
            # start listening again after a short delay
            if CONTINUOUS_LISTENING and not MUTED:
                print("DEBUG: Restarting continuous listening after processing")
                
                # If we're coming back from dictation mode, show a notification about returning to command mode
                if is_dictation_mode:
                    print("DEBUG: Returning to COMMAND MODE after dictation")
                    logger.info("Returning to COMMAND MODE")
                    
                    try:
                        # Visual notification of mode switch back to commands
                        from toast_notifications import send_notification
                        send_notification(
                            "Command Mode Active", 
                            "You can now speak commands | Say 'dictate' for typing",
                            "whisper-command-mode",
                            3,
                            True
                        )
                        
                        # Play a different sound for returning to command mode
                        subprocess.run(["afplay", "/System/Library/Sounds/Bottle.aiff"], check=False)
                    except Exception as e:
                        logger.error(f"Failed to show command mode notification: {e}")
                
                # Add a small delay to avoid CPU overuse
                time.sleep(0.5)
                threading.Thread(target=start_continuous_listening, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
            notify_error(f"Error processing audio: {str(e)}")
            # Make sure to call task_done even if an exception occurs
            AUDIO_QUEUE.task_done()


def process_dictation(transcription):
    """Process dictation by typing text at cursor.
    
    Args:
        transcription (str): The text to type
    """
    # Add more prominent logging
    print("========== DICTATION TEXT RECEIVED ==========")
    print(f"DICTATION TEXT: '{transcription}'")
    print("============================================")
    logger.info(f"Dictation mode: typing '{transcription}'")
    
    try:
        # Try multiple paste methods in sequence
        success = False
        
        # Add more debug logging to diagnose paste issues
        print(f"DEBUG: Attempting to paste transcribed text: '{transcription}'")
        
        # Method 1: AppleScript (most reliable on macOS)
        try:
            logger.info("Using AppleScript keystroke method...")
            print("DEBUG: Trying AppleScript method")
            
            # No need to remove 'v' characters anymore since we're using different hotkeys
            
            # Save to temp file for AppleScript
            tmp_file = "/tmp/dictation_text.txt"
            with open(tmp_file, "w") as f:
                f.write(transcription)
            print(f"DEBUG: Saved text to {tmp_file}")
            
            # AppleScript to keystroke the text - with better error handling
            script = '''
            set the_text to (do shell script "cat /tmp/dictation_text.txt")
            tell application "System Events"
                delay 0.5
                keystroke the_text
            end tell
            '''
            
            print("DEBUG: Running AppleScript")
            result = subprocess.run(["osascript", "-e", script], 
                                  check=False, 
                                  capture_output=True,
                                  text=True)
            
            if result.returncode == 0:
                success = True
                print("DEBUG: AppleScript succeeded")
            else:
                print(f"DEBUG: AppleScript returned non-zero exit code: {result.returncode}")
                print(f"DEBUG: AppleScript stderr: {result.stderr}")
            
            # Clean up temp file
            os.remove(tmp_file)
        except Exception as e1:
            logger.error(f"AppleScript method failed: {e1}")
            print(f"DEBUG: AppleScript method failed: {e1}")
            import traceback
            print(f"DEBUG: {traceback.format_exc()}")
            
        # Method 2: pbcopy + cmd+v (fallback)
        if not success:
            try:
                logger.info("Trying pbcopy + cmd+v method...")
                print("DEBUG: Using pbcopy to copy text to clipboard")
                
                # Copy text to clipboard using pbcopy
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(transcription.encode('utf-8'))
                time.sleep(1.0)  # Give clipboard time to update
                
                print("DEBUG: Pasting with cmd+v")
                # Paste using command+v
                pyautogui.hotkey('command', 'v')
                success = True
                print("DEBUG: Clipboard method succeeded")
            except Exception as e2:
                logger.warning(f"Clipboard method failed: {e2}")
                print(f"DEBUG: Clipboard method failed: {e2}")
                import traceback
                print(f"DEBUG: {traceback.format_exc()}")
            
        # Method 3: Direct typing as last resort
        if not success:
            try:
                logger.info("Using direct typing as last resort...")
                print("DEBUG: Typing text directly with pyautogui")
                pyautogui.write(transcription, interval=0.03)
                success = True
                print("DEBUG: Direct typing succeeded")
            except Exception as e3:
                logger.error(f"Direct typing failed: {e3}")
                print(f"DEBUG: Direct typing failed: {e3}")
                import traceback
                print(f"DEBUG: {traceback.format_exc()}")
                # Don't raise here, just log the error
                print("DEBUG: All typing methods failed")
        
        # ALWAYS save to log file, even if typing methods failed
        try:
            print(f"DEBUG: Writing to dictation log: '{transcription}'")
            with open('dictation_log.txt', 'a') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {transcription}\n")
            print("DEBUG: Successfully wrote to dictation log")
        except Exception as log_err:
            logger.error(f"Failed to write to log: {log_err}")
            print(f"DEBUG: Failed to write to dictation log: {log_err}")
        
        # Play completion sound
        try:
            print("DEBUG: Playing completion sound")
            subprocess.run(["afplay", "/System/Library/Sounds/Pop.aiff"], check=False)
        except Exception as sound_err:
            print(f"DEBUG: Failed to play completion sound: {sound_err}")
            
        # Show success notification
        try:
            print("DEBUG: Showing dictation success notification")
            notify_command_executed(f"Transcribed: {transcription}")
        except Exception as notif_err:
            print(f"DEBUG: Failed to show notification: {notif_err}")
            
        logger.info("Dictation completed successfully")
        print("DEBUG: Dictation processing completed successfully")
        print("========== END DICTATION PROCESSING ==========")
        
    except Exception as e:
        logger.error(f"Failed to process dictation: {e}")
        print(f"ERROR: Failed to process dictation: {e}")
        import traceback
        print(f"DEBUG: {traceback.format_exc()}")
        
        try:
            notify_error(f"Failed to process dictation: {str(e)}")
        except:
            print("DEBUG: Also failed to show error notification")


def signal_handler(sig, frame):
    """Handle termination signals."""
    logger.info("Shutting down...")
    
    # Stop recording if active
    global RECORDING
    RECORDING = False
    
    # Add None to the queue to signal the processor to exit
    AUDIO_QUEUE.put(None)
    
    # Clean up recorder
    recorder.cleanup()
    
    # Exit
    os._exit(0)


# Define simpler hotkey detection mechanism
CTRL_PRESSED = False
SHIFT_PRESSED = False
ALT_PRESSED = False
CMD_PRESSED = False
SPACE_PRESSED = False
D_PRESSED = False
M_PRESSED = False  # For mute toggle

# System states
MUTED = False
CONTINUOUS_LISTENING = True  # Always listen unless muted
TRIGGER_DETECTED = False  # Whether a vocal trigger has been detected
TRIGGER_BUFFER = []  # Buffer to store recent audio for trigger detection
COMMAND_TRIGGER = "hey"  # The trigger word for command mode
DICTATION_TRIGGER = "type"  # The trigger word for dictation mode

# Add a mutex to prevent multiple trigger detections running at once
TRIGGER_DETECTION_RUNNING = False
TRIGGER_MUTEX = threading.Lock()  # Mutex for trigger detection

# Rolling audio buffer for continuous listening
AUDIO_BUFFER = []  # Stores audio chunks
AUDIO_BUFFER_SECONDS = 5  # Keep last 5 seconds of audio
AUDIO_BUFFER_LOCK = threading.Lock()  # Mutex for audio buffer

def start_recording_thread(mode, force=False):
    """Start a recording thread with specified mode.
    
    Args:
        mode (str): Either 'command' or 'dictation'
        force (bool): If True, will force start a new recording even if one is in progress
        
    IMPORTANT DIFFERENCE BETWEEN MODES:
    - Command mode: System listens for voice commands to control your computer
      Example: "open Safari", "maximize window", etc.
    - Dictation mode: System captures your speech and types it as text at the current cursor position
      Example: When you say "Hello world", it will type "Hello world" where your cursor is
    """
    global MUTED, TRIGGER_DETECTED, RECORDING
    
    # Normalize the mode parameter
    if mode.lower() in ['dictate', 'dictation', 'typing']:
        mode = 'dictation'
    else:
        mode = 'command'
    
    # Check if muted
    if MUTED:
        print(f"DEBUG: Microphone is muted, ignoring {mode} request")
        
        # Show muted notification
        try:
            from toast_notifications import send_notification
            send_notification(
                "Microphone Muted", 
                "Press Ctrl+Shift+M to unmute",
                "whisper-voice-muted",
                3,
                True
            )
        except Exception as e:
            print(f"DEBUG: Failed to show mute notification: {e}")
            
        # Make sure to reset the RECORDING flag since we're aborting
        RECORDING = False
        return
    
    # Check if already recording and not forced
    if RECORDING and not force:
        print(f"DEBUG: Already recording, ignoring {mode} request (set force=True to override)")
        return
        
    # If we're force-starting a new recording, reset the RECORDING flag first
    if RECORDING and force:
        print(f"DEBUG: Force-resetting RECORDING flag before starting new {mode} recording")
        RECORDING = False
        time.sleep(0.2)  # Small delay to ensure flag is reset
    
    is_dictation = (mode == 'dictation')
    mode_name = "Dictation" if is_dictation else "Command"
    
    # For dictation mode, add a notification immediately to show it's activated
    if is_dictation:
        try:
            # Extra notification right at the start
            from toast_notifications import send_notification
            send_notification(
                "Starting Dictation Mode", 
                "Get ready to speak...",
                "whisper-dictation-preparing",
                2,
                True
            )
        except Exception as e:
            print(f"DEBUG: Failed to show dictation preparation notification: {e}")
    
    print(f"DEBUG: {mode_name} mode triggered")
    logger.info(f"{mode_name} mode triggered - starting voice recording...")
    
    # Set the RECORDING flag to True before starting the thread
    # This helps avoid race conditions where the thread might not set it in time
    print(f"DEBUG: Setting RECORDING flag to True before starting {mode} recording thread")
    RECORDING = True
    
    def recording_thread_func():
        print(f"DEBUG: Starting {mode_name.lower()} recording")
        
        try:
            # Ensure recording completes before this function returns
            print(f"DEBUG: About to start {mode_name} recording via recorder...")
            result = recorder.start_recording(dictation_mode=is_dictation, force=True)
            print(f"DEBUG: {mode_name} recording completed, audio file: {result}")
            
            # Verify the file was created and has content before continuing
            if result and os.path.exists(result):
                size = os.path.getsize(result)
                print(f"DEBUG: Audio file size: {size} bytes")
                if size < 1000:
                    print("WARNING: Audio file suspiciously small, may not contain speech")
        except Exception as e:
            print(f"DEBUG: Error in recording thread: {e}")
            import traceback
            print(f"DEBUG: {traceback.format_exc()}")
        finally:
            # Always reset RECORDING flag when we're done
            print("DEBUG: Resetting RECORDING flag to False after recording completion")
            RECORDING = False
    
    # Create a thread that will block until recording is complete
    thread = threading.Thread(target=recording_thread_func)
    thread.daemon = True
    thread.start()
    
    print(f"DEBUG: {mode_name} recording thread started: {thread.name}")
    
    # IMPORTANT: Add a small delay to ensure thread starts properly
    # This prevents immediate return of the function
    time.sleep(0.7)  # Increased from 0.5 to 0.7 for more reliable startup

# We've now removed keyboard shortcuts for recording and only use the mute toggle

def toggle_mute_callback():
    """Toggle mute state."""
    global MUTED, RECORDING
    
    # If currently recording, stop it
    if RECORDING:
        RECORDING = False
        logger.info("Stopping active recording due to mute toggle")
    
    # Toggle mute state
    MUTED = not MUTED
    
    # Show notification of current mute state
    status = "MUTED" if MUTED else "UNMUTED"
    logger.info(f"Microphone {status}")
    
    # Play feedback sound first (more reliable)
    try:
        sound = "/System/Library/Sounds/Submarine.aiff" if MUTED else "/System/Library/Sounds/Funk.aiff"
        subprocess.run(["afplay", sound], check=False)
    except Exception as e:
        logger.error(f"Could not play mute toggle sound: {e}")
        
    # Use toast notification to show status (wrapped in try/except)
    try:
        # Import here to avoid circular imports
        from toast_notifications import send_notification
        send_notification(
            f"Microphone {status}",
            f"Voice control is {'paused' if MUTED else 'active'}",
            "whisper-voice-mute-toggle",
            3,
            True
        )
    except Exception as e:
        logger.error(f"Could not show mute notification: {e}")
        # Still log the status change
        print(f"DEBUG: Microphone is now {status}")
        
    # If unmuted, start continuous listening with our rolling buffer approach
    if not MUTED and CONTINUOUS_LISTENING:
        # Start listening in a separate thread to avoid blocking
        threading.Thread(target=start_continuous_listening, daemon=True).start()


# We've replaced this function with the continuous_recording_thread and process_audio_buffer functions

def process_trigger_audio(audio_file):
    """Process audio to detect trigger words.
    
    Args:
        audio_file (str): Path to the audio file to process
    
    Returns:
        bool: True if trigger word detected, False otherwise
    """
    global TRIGGER_DETECTED, COMMAND_TRIGGER, DICTATION_TRIGGER, RECORDING
    
    # Add a marker for debugging
    print("DEBUG: ========== TRIGGER DETECTION STARTED ==========")
    
    # Double-check that we're not already recording (safety check)
    if RECORDING:
        print("DEBUG: Already recording, skipping trigger detection")
        return False
    
    try:
        # Check if file exists and has reasonable size
        if not os.path.exists(audio_file):
            print(f"DEBUG: Trigger audio file not found: {audio_file}")
            return False
            
        file_size = os.path.getsize(audio_file)
        if file_size < 1000:  # Less than 1KB is probably noise or empty
            print(f"DEBUG: Trigger audio file too small ({file_size} bytes), likely no speech")
            return False
        
        # Use the same model but with a shorter output
        result = WHISPER_MODEL.transcribe(
            audio_file, 
            language="en",
            fp16=False  # Use more precise but slower processing for trigger detection
        )
        transcription = result["text"].strip().lower()
        
        print(f"DEBUG: Trigger detection heard: '{transcription}'")
        
        # Check for command trigger variations (hey, etc.)
        command_variations = [COMMAND_TRIGGER.lower(), "hay", "he", "hey", "hi", "okay", "ok"]
        contains_command_trigger = any(variation in transcription.lower() for variation in command_variations)
        
        # Check for dictation trigger variations (type, etc.)
        # Use a much longer list of variations to improve detection
        dictation_variations = [
            DICTATION_TRIGGER.lower(), "typing", "write", "note", "text", "speech to text",
            "tight", "tipe", "types", "typed", "typ", "tape", "time", "tip", "tie",
            "type please", "please type", "start typing", "begin typing", "activate typing",
            "time please", "time this", "type this", "dictate", "dictation", "take dictation",
            "start dictation", "dictate this", "write this", "take notes", "ti", "ty", "tai"
        ]
        
        # Check for JARVIS assistant trigger
        jarvis_variations = ["jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "ok jarvis"]
        contains_jarvis_trigger = False
        
        # Check for Jarvis trigger in the transcription
        for variation in jarvis_variations:
            if variation in transcription.lower():
                print(f"DEBUG: JARVIS TRIGGER MATCH found for '{variation}' in '{transcription}'")
                contains_jarvis_trigger = True
                break
                
        # Add strong debugging for trigger detection
        print(f"DEBUG: Trigger word check for: '{transcription}'")
        print(f"DEBUG: Command trigger: {contains_command_trigger}, Dictation trigger: {contains_dictation_trigger}, JARVIS trigger: {contains_jarvis_trigger}")
        
        # More robust detection for dictation - looking for exact word matches or the word embedded in a phrase
        contains_dictation_trigger = False
        for variation in dictation_variations:
            # Full exact match
            if variation == transcription.lower().strip():
                print(f"DEBUG: EXACT MATCH found for '{variation}'")
                contains_dictation_trigger = True
                break
                
            # Word boundary match - the trigger word surrounded by spaces or at start/end
            if (f" {variation} " in f" {transcription.lower()} " or
                transcription.lower().startswith(f"{variation} ") or
                transcription.lower().endswith(f" {variation}")):
                print(f"DEBUG: WORD BOUNDARY MATCH found for '{variation}' in '{transcription}'")
                contains_dictation_trigger = True
                break
                
            # Check for string similarity - handles slight variations in pronunciation
            if variation in transcription.lower():
                print(f"DEBUG: SUBSTRING MATCH found for '{variation}' in '{transcription}'")
                contains_dictation_trigger = True
                break
                
        # Log trigger detection result
        print(f"DEBUG: Dictation trigger detected: {contains_dictation_trigger}")
        
        # Process JARVIS assistant trigger first (highest priority)
        if contains_jarvis_trigger:
            print(f"DEBUG: JARVIS ASSISTANT TRIGGER DETECTED: '{transcription}'")
            print("DEBUG: ========== ACTIVATING JARVIS ASSISTANT ==========")
            logger.info(f"JARVIS assistant trigger detected: '{transcription}'")
            TRIGGER_DETECTED = True
            
            # Play a notification sound
            try:
                subprocess.run(["afplay", "/System/Library/Sounds/Submarine.aiff"], check=False)
            except Exception as e:
                print(f"DEBUG: Failed to play JARVIS notification sound: {e}")
                
            # Forward to the assistant module
            try:
                assistant.process_voice_command(transcription)
                print("DEBUG: Voice command processed by JARVIS assistant")
                return True
            except Exception as e:
                print(f"DEBUG: Error processing JARVIS command: {e}")
                import traceback
                print(f"DEBUG: {traceback.format_exc()}")
                return False
        
        # Process dictation trigger next (medium priority)
        elif contains_dictation_trigger:
            print(f"DEBUG: DICTATION TRIGGER DETECTED: '{DICTATION_TRIGGER}'")
            print("DEBUG: ========== STARTING DICTATION MODE DIRECTLY ==========")
            logger.info(f"Dictation trigger word detected: '{DICTATION_TRIGGER}'")
            TRIGGER_DETECTED = True
            
            # Play a different sound for dictation mode
            try:
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
            except Exception:
                pass
                
            # Add a notification to clearly show we're entering dictation mode
            try:
                from toast_notifications import send_notification
                send_notification(
                    "Dictation Mode Activated", 
                    "Everything you say will be typed as text",
                    "whisper-dictation-direct",
                    3,
                    True
                )
            except Exception as e:
                print(f"DEBUG: Failed to show dictation notification: {e}")
                
            # Longer delay for dictation mode to allow user to prepare
            time.sleep(0.5)
            
            # Start dictation mode directly
            print("DEBUG: Starting dictation recording after trigger detection")
            start_recording_thread('dictation', force=True)
            print("DEBUG: Dictation recording thread started")
            return True
            
        # Otherwise check for command trigger (lowest priority)
        elif contains_command_trigger:
            print(f"DEBUG: COMMAND TRIGGER DETECTED: '{COMMAND_TRIGGER}'")
            print("DEBUG: ========== STARTING FULL COMMAND RECORDING ==========")
            logger.info(f"Command trigger word detected: '{COMMAND_TRIGGER}'")
            TRIGGER_DETECTED = True
            
            # Play a subtle notification sound for command detection
            try:
                subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], check=False)
            except Exception:
                pass
                
            # Add a notification to show we're listening for a command
            try:
                from toast_notifications import send_notification
                send_notification(
                    "Command Mode Activated", 
                    "Listening for your command...",
                    "whisper-command-direct",
                    3,
                    False
                )
            except Exception as e:
                print(f"DEBUG: Failed to show command notification: {e}")
                
            # Add a small delay to ensure proper transition
            time.sleep(0.3)
            
            # Start full recording for command mode
            print("DEBUG: Starting command recording after trigger detection")
            start_recording_thread('command', force=True)
            print("DEBUG: Command recording thread started")
            return True
    except Exception as e:
        print(f"DEBUG: Error in trigger detection: {e}")
        import traceback
        print(f"DEBUG: {traceback.format_exc()}")
    
    try:
        # Clean up the audio file
        if os.path.exists(audio_file):
            os.unlink(audio_file)
            print(f"DEBUG: Cleaned up trigger audio file: {audio_file}")
    except Exception as clean_err:
        print(f"DEBUG: Error cleaning up trigger audio: {clean_err}")
    
    # If we get here, no trigger was detected
    # Wait longer to prevent excessive CPU usage and rapid audio capture
    time.sleep(1.0)  # Increased delay to 1 second
    
    # Check if we're still in a state where we should restart trigger detection
    if not MUTED and not RECORDING and CONTINUOUS_LISTENING:
        # Use a timer to restart after delay to avoid thread buildup
        print("DEBUG: Scheduling next trigger detection in 2 seconds")
        
        def safe_restart_trigger():
            # This function makes sure we don't get into a recursive nightmare
            global RECORDING, TRIGGER_DETECTION_RUNNING
            
            if RECORDING or MUTED or not CONTINUOUS_LISTENING:
                print("DEBUG: Conditions changed, not restarting trigger detection")
                return
                
            if TRIGGER_DETECTION_RUNNING:
                print("DEBUG: Trigger detection already running, not starting another")
                return
                
            # Start trigger detection from scratch
            print("DEBUG: Now restarting trigger detection after delay")
            start_trigger_detection()
            
        # Schedule the restart with a longer delay
        timer = threading.Timer(2.0, safe_restart_trigger)
        timer.daemon = True
        timer.start()
    else:
        print("DEBUG: Not restarting trigger detection - system state prevents it")
        
    return False

def continuous_recording_thread():
    """Continuously record audio into a rolling buffer."""
    global AUDIO_BUFFER, MUTED, RECORDING
    
    logger.info("Starting continuous recording background thread")
    print("DEBUG: Continuous recording thread starting")
    
    # Set up a local variable to track our own recording state
    # This is separate from the global RECORDING variable
    continuous_recording_active = True
    
    try:
        # Initialize audio recording
        chunk = 1024
        format = pyaudio.paInt16
        channels = 1
        rate = 16000
        p = pyaudio.PyAudio()
        
        # Initialize energy detection variables
        energy_threshold = 300  # Threshold for detecting voice activity
        silence_frames = 0
        max_silence_frames = int(rate / chunk * 0.5)  # 0.5 seconds of silence
        has_speech = False
        
        # Calculate buffer size
        frames_per_second = rate / chunk
        max_buffer_frames = int(frames_per_second * AUDIO_BUFFER_SECONDS)
        
        # Get default input device
        default_input_device_index = p.get_default_input_device_info().get('index')
        print(f"DEBUG: Continuous recording using input device index: {default_input_device_index}")
        
        # Open stream with explicit input device index
        try:
            stream = p.open(
                format=format,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=default_input_device_index,
                frames_per_buffer=chunk
            )
            print("DEBUG: Continuous recording stream opened successfully")
        except Exception as e:
            logger.error(f"Failed to open audio stream for continuous recording: {e}")
            return
        
        print("DEBUG: Beginning continuous audio buffering")
        
        # Main recording loop
        while continuous_recording_active:
            # Skip recording if muted
            if MUTED:
                time.sleep(0.1)
                continue
                
            # If global RECORDING is active, pause our continuous recording
            # This means another recording operation (like dictation) is in progress
            if RECORDING:
                print("DEBUG: Pausing continuous recording while active recording is in progress")
                time.sleep(0.1)
                continue
            
            try:
                # Read audio data
                data = stream.read(chunk, exception_on_overflow=False)
                
                # Calculate audio energy/volume
                audio_data = np.frombuffer(data, dtype=np.int16)
                energy = np.abs(audio_data).mean()
                
                # Log energy occasionally (every 1 second approximately)
                if len(AUDIO_BUFFER) % int(frames_per_second) == 0:
                    print(f"DEBUG: Audio energy level: {energy:.0f}, buffer size: {len(AUDIO_BUFFER)}")
                
                # Detect speech activity
                if energy > energy_threshold:
                    # High energy detected - could be speech
                    if not has_speech:
                        print(f"DEBUG: Voice activity detected, energy: {energy:.0f}")
                        has_speech = True
                    silence_frames = 0
                else:
                    # Low energy - might be silence
                    silence_frames += 1
                    
                    # If we had speech and now detect enough silence, trigger processing
                    if has_speech and silence_frames >= max_silence_frames:
                        print(f"DEBUG: Potential trigger word - processing buffer after {silence_frames/frames_per_second:.1f}s silence")
                        
                        # We need to be careful about setting RECORDING here to prevent race conditions
                        # Only process if we're not already in recording mode
                        if not RECORDING:
                            # First set recording to True to block other recordings
                            RECORDING = True
                            # Process buffer in a separate thread to avoid blocking the continuous recording
                            threading.Thread(target=process_audio_buffer, daemon=True).start()
                        else:
                            print("DEBUG: Skipping buffer processing - already recording")
                            
                        has_speech = False
                
                # Add data to the rolling buffer with thread safety
                with AUDIO_BUFFER_LOCK:
                    AUDIO_BUFFER.append(data)
                    # Keep buffer at maximum size
                    while len(AUDIO_BUFFER) > max_buffer_frames:
                        AUDIO_BUFFER.pop(0)
                
            except Exception as e:
                print(f"DEBUG: Error in continuous recording: {e}")
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
        except:
            pass

def process_audio_buffer():
    """Process the audio buffer to detect trigger words."""
    global AUDIO_BUFFER, TRIGGER_DETECTED, RECORDING
    
    # RECORDING flag should already be set before this function is called
    # to prevent race conditions with other audio processing
    
    # Skip if buffer is too small
    with AUDIO_BUFFER_LOCK:
        if len(AUDIO_BUFFER) < 10:  # At least some minimum amount of frames
            print("DEBUG: Buffer too small to process")
            # Reset recording flag since we're aborting
            RECORDING = False
            return
            
        # Make a copy of the buffer to process
        buffer_copy = AUDIO_BUFFER.copy()
        
    print(f"DEBUG: Processing audio buffer with {len(buffer_copy)} frames")
    
    # Save buffer to a temporary WAV file
    try:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_filename = temp_file.name
        temp_file.close()
        
        wf = wave.open(temp_filename, 'wb')
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(16000)  # 16kHz
        
        # Join frames and write to file
        joined_frames = b''.join(buffer_copy)
        wf.writeframes(joined_frames)
        wf.close()
        
        print(f"DEBUG: Audio buffer saved to {temp_filename}")
        
        # Use Whisper to transcribe the buffer
        result = WHISPER_MODEL.transcribe(
            temp_filename,
            language="en",
            fp16=False
        )
        transcription = result["text"].strip().lower()
        
        print(f"DEBUG: Buffer transcription: '{transcription}'")
        
        # Check for command trigger
        command_variations = [COMMAND_TRIGGER.lower(), "hay", "he", "hey", "hi", "okay", "ok"]
        contains_command_trigger = any(variation in transcription.lower() for variation in command_variations)
        
        # Check for JARVIS assistant trigger
        jarvis_variations = ["jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "ok jarvis"]
        contains_jarvis_trigger = any(variation in transcription.lower() for variation in jarvis_variations)
        
        # Check for dictation trigger with robust detection
        dictation_variations = [
            DICTATION_TRIGGER.lower(), "typing", "write", "note", "text", "speech to text",
            "tight", "tipe", "types", "typed", "typ", "tape", "time", "tip", "tie"
        ]
        
        # More robust dictation detection
        contains_dictation_trigger = False
        for variation in dictation_variations:
            if (variation == transcription.lower().strip() or 
                f" {variation} " in f" {transcription.lower()} " or
                transcription.lower().startswith(f"{variation} ") or 
                transcription.lower().endswith(f" {variation}") or
                variation in transcription.lower()):
                print(f"DEBUG: Found dictation trigger '{variation}' in buffer transcription")
                contains_dictation_trigger = True
                break
        
        # Process trigger detections
        # First check for JARVIS assistant trigger (highest priority)
        if contains_jarvis_trigger:
            print(f"DEBUG: JARVIS ASSISTANT TRIGGER DETECTED in buffer: '{transcription}'")
            logger.info(f"JARVIS assistant trigger detected in buffered audio")
            
            # Play distinctive feedback sound
            try:
                subprocess.run(["afplay", "/System/Library/Sounds/Submarine.aiff"], check=False)
            except Exception as e:
                print(f"DEBUG: Failed to play JARVIS notification sound: {e}")
                
            # Show notification
            try:
                from toast_notifications import send_notification
                send_notification(
                    "JARVIS Activated", 
                    "How can I help you?",
                    "whisper-jarvis-buffer",
                    3,
                    True
                )
            except Exception as e:
                print(f"DEBUG: Failed to show JARVIS notification: {e}")
                
            # Forward the transcription to the assistant module
            try:
                assistant.process_voice_command(transcription)
                print("DEBUG: Voice command processed by JARVIS assistant")
            except Exception as e:
                print(f"DEBUG: Error processing JARVIS command: {e}")
                import traceback
                print(f"DEBUG: {traceback.format_exc()}")
            
            # Reset recording flag after processing
            RECORDING = False
            
        # Then check for dictation trigger (medium priority)    
        elif contains_dictation_trigger:
            print(f"DEBUG: DICTATION TRIGGER DETECTED in buffer: '{transcription}'")
            logger.info(f"Dictation trigger detected in buffered audio")
            
            # Play feedback sound
            try:
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
            except Exception:
                pass
                
            # Show notification
            try:
                from toast_notifications import send_notification
                send_notification(
                    "Dictation Mode Activated", 
                    "Everything you say will be typed as text",
                    "whisper-dictation-buffer",
                    3,
                    True
                )
            except Exception as e:
                print(f"DEBUG: Failed to show notification: {e}")
                
            # Start dictation mode
            time.sleep(0.5)
            start_recording_thread('dictation', force=True)
            
        # Finally check for command trigger (lowest priority)
        elif contains_command_trigger:
            print(f"DEBUG: COMMAND TRIGGER DETECTED in buffer: '{transcription}'")
            logger.info(f"Command trigger detected in buffered audio")
            
            # Play feedback sound
            try:
                subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], check=False)
            except Exception:
                pass
                
            # Show notification
            try:
                from toast_notifications import send_notification
                send_notification(
                    "Command Mode Activated", 
                    "Listening for your command...",
                    "whisper-command-buffer",
                    3,
                    False
                )
            except Exception as e:
                print(f"DEBUG: Failed to show notification: {e}")
                
            # Start command mode
            time.sleep(0.3)
            start_recording_thread('command', force=True)
        
        # Clean up the temporary file
        try:
            os.unlink(temp_filename)
        except Exception as e:
            print(f"DEBUG: Failed to delete temp file: {e}")
        
        # If no trigger was detected, we need to reset the RECORDING flag
        if not contains_command_trigger and not contains_dictation_trigger and not contains_jarvis_trigger:
            print("DEBUG: No trigger words detected in buffer, returning to listening mode")
            RECORDING = False
            
    except Exception as e:
        print(f"DEBUG: Error processing audio buffer: {e}")
        import traceback
        print(f"DEBUG: {traceback.format_exc()}")
        # Always make sure to reset RECORDING flag in case of error
        RECORDING = False

def start_continuous_listening():
    """Start continuous listening for voice commands."""
    global TRIGGER_DETECTED
    
    # Don't start if muted or already recording
    if MUTED or RECORDING:
        return
        
    # Reset trigger detection state
    TRIGGER_DETECTED = False
    
    logger.info("Starting continuous listening...")
    print("DEBUG: Starting continuous listening")
    
    # Start the new continuous recording thread that maintains a buffer
    # This replaces the old trigger detection approach
    threading.Thread(target=continuous_recording_thread, daemon=True).start()

def on_press(key):
    """Handle key press events."""
    global CTRL_PRESSED, SHIFT_PRESSED, ALT_PRESSED, CMD_PRESSED, SPACE_PRESSED, D_PRESSED, M_PRESSED
    
    # Don't process hotkeys if muted (except for unmute hotkey)
    global MUTED
    
    try:
        # Always log the key for debugging
        logger.debug(f"Key pressed: {key}")
        print(f"DEBUG: Key pressed: {key}")
        
        # Update key state
        if key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            CTRL_PRESSED = True
            print("DEBUG: CTRL key pressed")
        elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            SHIFT_PRESSED = True
            print("DEBUG: SHIFT key pressed")
        elif key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            ALT_PRESSED = True
            print("DEBUG: ALT key pressed")
        elif key == keyboard.Key.cmd:
            CMD_PRESSED = True
            print("DEBUG: CMD key pressed")
        elif key == keyboard.Key.space:
            SPACE_PRESSED = True
            print("DEBUG: SPACE key pressed")
        elif isinstance(key, keyboard.KeyCode):
            # Handle character keys with better detection
            if hasattr(key, 'char') and key.char:
                char = key.char.lower()
                print(f"DEBUG: Character key pressed: '{char}'")
                if char == 'd':
                    D_PRESSED = True
                    print("DEBUG: D key detected")
                elif char == 'm':
                    M_PRESSED = True
                    print("DEBUG: M key detected")
        
        # Log key states for debug
        print(f"DEBUG: Key states - CTRL:{CTRL_PRESSED} SHIFT:{SHIFT_PRESSED} ALT:{ALT_PRESSED} SPACE:{SPACE_PRESSED} D:{D_PRESSED} M:{M_PRESSED}")
            
        # Check for mute toggle hotkey (Ctrl+Shift+M) - always active
        if CTRL_PRESSED and SHIFT_PRESSED and M_PRESSED:
            print("DEBUG: Mute toggle hotkey detected: Ctrl+Shift+M")
            logger.info("Mute toggle hotkey detected: Ctrl+Shift+M")
            try:
                toggle_mute_callback()
            except Exception as e:
                print(f"DEBUG: Error in mute toggle: {e}")
                logger.error(f"Error toggling mute: {e}")
            return  # Process this hotkey and return
            
    except Exception as e:
        logger.error(f"Error in key press handler: {e}")
        print(f"DEBUG: Key press handler error: {e}")
        import traceback
        logger.error(traceback.format_exc())

def on_release(key):
    """Handle key release events."""
    global CTRL_PRESSED, SHIFT_PRESSED, ALT_PRESSED, CMD_PRESSED, SPACE_PRESSED, D_PRESSED, M_PRESSED
    
    try:
        logger.debug(f"Key released: {key}")
        print(f"DEBUG: Key released: {key}")
        
        # Update key state
        if key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            CTRL_PRESSED = False
            print("DEBUG: CTRL key released")
        elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            SHIFT_PRESSED = False
            print("DEBUG: SHIFT key released")
        elif key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            ALT_PRESSED = False
            print("DEBUG: ALT key released")
        elif key == keyboard.Key.cmd:
            CMD_PRESSED = False
            print("DEBUG: CMD key released")
        elif key == keyboard.Key.space:
            SPACE_PRESSED = False
            print("DEBUG: SPACE key released")
        elif isinstance(key, keyboard.KeyCode):
            if hasattr(key, 'char') and key.char:
                char = key.char.lower() if key.char else ""
                if char == 'd':
                    D_PRESSED = False
                    print("DEBUG: D key released")
                elif char == 'm':
                    M_PRESSED = False
                    print("DEBUG: M key released")
            
    except Exception as e:
        logger.error(f"Error in key release handler: {e}")
        print(f"DEBUG: Key release handler error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Stop listener if escape key is pressed
    if key == keyboard.Key.esc:
        print("DEBUG: ESC key pressed - exiting application")
        # Add None to the queue to signal the processor to exit
        AUDIO_QUEUE.put(None)
        return False

if __name__ == "__main__":
    try:
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize audio recorder
        logger.info("Initializing audio recorder...")
        recorder = AudioRecorder()
        
        # Initialize JARVIS assistant
        logger.info("Initializing JARVIS assistant...")
        try:
            assistant.init_assistant()
            logger.info("JARVIS assistant initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing JARVIS assistant: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue without JARVIS if it fails to initialize
        
        # Test the speech synthesis system
        logger.info("Testing speech synthesis...")
        try:
            # Quick test of speech synthesis with minimal output
            tts.speak("Voice assistant initialized", block=True)
            logger.info("Speech synthesis working correctly")
        except Exception as e:
            logger.error(f"Error testing speech synthesis: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue without speech if it fails
        
        # Check if whisper model can be loaded
        try:
            logger.info(f"Testing Whisper model load: {MODEL_SIZE}")
            test_model = whisper.load_model(MODEL_SIZE)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            import traceback
            logger.error(traceback.format_exc())
            os._exit(1)
        
        # Start audio processing thread
        logger.info("Starting audio processing thread...")
        audio_thread = threading.Thread(target=process_audio)
        audio_thread.daemon = True
        audio_thread.start()

        # Only mute toggle hotkey is used now (Ctrl+Shift+M)
        logger.info("Setting up mute toggle hotkey: Ctrl+Shift+M")
        
        # Start keyboard listener
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        
        logger.info("=== Voice Control Ready ===")
        logger.info("ALWAYS LISTENING with ROLLING BUFFER")
        logger.info("THREE TRIGGER WORDS:")
        logger.info(f"1. COMMAND TRIGGER: Say '{COMMAND_TRIGGER}' to activate command mode")
        logger.info(f"2. DICTATION TRIGGER: Say '{DICTATION_TRIGGER}' to activate dictation mode")
        logger.info(f"3. ASSISTANT TRIGGER: Say 'hey Jarvis' to activate conversational assistant")
        logger.info(f"MUTE TOGGLE: Press Ctrl+Shift+M to mute/unmute voice control")
        logger.info("")
        logger.info("HOW IT WORKS:")
        logger.info("- System continuously listens with a 5-second rolling buffer")
        logger.info("- When you speak, we analyze the buffer to detect trigger words")
        logger.info("- No need to wait for a recording to start - just speak naturally")
        logger.info("")
        logger.info("COMMAND MODE: System listens for commands to control your computer")
        logger.info(f"   Say '{COMMAND_TRIGGER}' to activate, then speak your command when you hear the tone")
        logger.info("   Examples: 'open Safari', 'maximize window', 'focus chrome'")
        logger.info("")
        logger.info("DICTATION MODE: System types what you say at the cursor position")
        logger.info(f"   Simply say '{DICTATION_TRIGGER}' to start dictation immediately")
        logger.info("   Everything you say after will be typed at the cursor position")
        logger.info("   To exit dictation mode, stop speaking for 4 seconds")
        logger.info("")
        logger.info("JARVIS ASSISTANT MODE: Talk to a conversational assistant")
        logger.info("   Say 'hey Jarvis' to activate the conversational assistant")
        logger.info("   Ask questions like 'what time is it' or 'tell me a joke'")
        logger.info("   Say 'go to sleep' to exit assistant mode")
        logger.info("")
        logger.info("Press Ctrl+C or ESC to exit")
        
        # Wait longer before starting continuous listening to make sure everything is initialized
        logger.info("Waiting 5 seconds before starting continuous listening mode...")
        print(f"DEBUG: System will begin listening for trigger words '{COMMAND_TRIGGER}', '{DICTATION_TRIGGER}', or 'hey Jarvis' in 5 seconds")
        
        def delayed_start():
            # Wait 5 seconds for all subsystems to initialize
            time.sleep(5)
            
            # Make sure model is loaded before starting
            if WHISPER_MODEL is None:
                logger.info("Waiting for Whisper model to finish loading...")
                print("DEBUG: Waiting for Whisper model to finish loading...")
                # Wait up to 15 more seconds for model to load
                for _ in range(15):
                    if WHISPER_MODEL is not None:
                        break
                    time.sleep(1)
            
            logger.info("Now starting continuous listening mode...")
            print("DEBUG: Now starting trigger word detection")
            print(f"DEBUG: Say '{COMMAND_TRIGGER}' for command mode or '{DICTATION_TRIGGER}' for dictation mode")
            
            if CONTINUOUS_LISTENING and not MUTED:
                # Send a clear notification that we're listening for the trigger word
                try:
                    from toast_notifications import send_notification
                    send_notification(
                        "Voice Control Ready",
                        f"Say '{COMMAND_TRIGGER}' for commands | Say '{DICTATION_TRIGGER}' for dictation",
                        "whisper-trigger-listening",
                        10,
                        False
                    )
                except Exception as e:
                    print(f"DEBUG: Failed to show trigger notification: {e}")
                
                # Start continuous listening with rolling buffer
                # This replaces the old trigger detection approach
                start_continuous_listening()
                
        threading.Thread(target=delayed_start, daemon=True).start()
        
        try:
            # Send a notification that we're ready
            from toast_notifications import send_notification
            send_notification(
                "Voice Control Ready with Rolling Buffer", 
                f"Just speak: '{COMMAND_TRIGGER}' for commands | '{DICTATION_TRIGGER}' for dictation | Mute: Ctrl+Shift+M",
                "whisper-voice-ready",
                10,
                True
            )
        except Exception as e:
            logger.error(f"Failed to show startup notification: {e}")
            # Not critical, can continue without notification
        
        # Keep the main thread alive to listen for keyboard events
        # Also check if listener is still alive
        while True:
            if not listener.running:
                logger.info("Keyboard listener stopped. Exiting...")
                break
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Unhandled exception in main thread: {e}")
        import traceback
        logger.error(traceback.format_exc())
        os._exit(1)