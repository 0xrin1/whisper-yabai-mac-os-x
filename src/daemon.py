#!/usr/bin/env python3
"""
Voice command daemon using Whisper and Yabai for Mac OS X control.
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
        
    def start_recording(self, duration=None, dictation_mode=False):
        """
        Start recording audio for specified duration.
        
        Args:
            duration (int, optional): Recording duration in seconds
            dictation_mode (bool): If True, recorded audio will be transcribed directly to text
                                  rather than interpreted as a command
        """
        global RECORDING
        
        if RECORDING:
            print("DEBUG: Already recording, ignoring request")
            return
            
        # Use environment variable if duration not specified
        if duration is None:
            duration = int(os.getenv('RECORDING_DURATION', '5'))
            
        print(f"DEBUG: Recording duration set to {duration} seconds")
        
        RECORDING = True
        print("DEBUG: RECORDING flag set to True")
        
        # Play a sound to indicate recording has started
        self._play_start_sound()
        
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
            
    def start_recording(self, duration=None, dictation_mode=False):
        """
        Start recording audio for specified duration.
        
        Args:
            duration (int, optional): Recording duration in seconds
            dictation_mode (bool): If True, recorded audio will be transcribed directly to text
                                  rather than interpreted as a command
        """
        global RECORDING
        
        if RECORDING:
            print("DEBUG: Already recording, ignoring request")
            return
            
        # Use environment variable if duration not specified
        if duration is None:
            # Use longer duration for dictation mode
            if dictation_mode:
                duration = int(os.getenv('DICTATION_DURATION', '10'))
            else:
                duration = int(os.getenv('RECORDING_DURATION', '5'))
            
        print(f"DEBUG: Recording duration set to {duration} seconds")
        
        RECORDING = True
        print("DEBUG: RECORDING flag set to True")
        
        # Play a sound to indicate recording has started
        self._play_start_sound()
        
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
        
        # For silence detection
        SILENCE_THRESHOLD = 500  # Adjust based on testing
        silence_frames = 0
        max_silence_frames = int(frames_per_second * 3)  # 3 seconds of silence
        
        # Set maximum recording duration
        max_duration = 60 if dictation_mode else 15  # 60 seconds for dictation, 15 for commands
        total_frames = int(frames_per_second * max_duration)
        
        # Minimum recording duration 
        min_duration = 2  # At least 2 seconds of audio
        min_frames = int(frames_per_second * min_duration)
        
        print(f"DEBUG: Beginning smart recording (max: {max_duration}s, silence timeout: 3s)")
        
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
                        # end the recording automatically
                        if has_speech and frames_recorded > min_frames and silence_frames >= max_silence_frames:
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
        
        # Add to processing queue with mode flag
        if dictation_mode:
            print(f"DEBUG: Adding to queue as dictation: {temp_filename}")
            AUDIO_QUEUE.put((temp_filename, True))
            print("DEBUG: Item added to queue with dictation flag")
        else:
            print(f"DEBUG: Adding to queue as command: {temp_filename}")
            AUDIO_QUEUE.put(temp_filename)
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
            
        # Check for dictation mode command first
        if clean_text.startswith("dictate") or "start dictation" in clean_text:
            logger.info("Detected dictation command")
            print("DEBUG: Voice command triggered dictation mode")
            
            # Start dictation mode through the same path the hotkey would use
            # Use threading to avoid blocking this function
            threading.Thread(target=start_recording_thread, args=('dictation',), daemon=True).start()
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
                elif action == "dictate" or action == "dictation":
                    threading.Thread(target=start_recording_thread, args=('dictation',), daemon=True).start()
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
            
            if isinstance(audio_item, tuple) and len(audio_item) == 2:
                # Format: (file_path, is_dictation)
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
                result = WHISPER_MODEL.transcribe(audio_file)
                transcription = result["text"].strip()
                confidence = result.get("confidence", 1.0)
                print(f"DEBUG: Transcription: '{transcription}', confidence: {confidence:.2f}")
                
                # Clean up the audio file
                try:
                    os.unlink(audio_file)
                except Exception as unlink_err:
                    print(f"DEBUG: Failed to delete temp file: {unlink_err}")
                
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
                    print(f"DEBUG: Processing as command: '{transcription}'")
                    command_processor.execute_command(transcription)
                    print("DEBUG: Command processing completed")
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
            
            # AppleScript to keystroke the text
            script = '''
            set the_text to (do shell script "cat /tmp/dictation_text.txt")
            tell application "System Events"
                delay 0.5
                keystroke the_text
            end tell
            '''
            
            print("DEBUG: Running AppleScript")
            subprocess.run(["osascript", "-e", script], check=True)
            success = True
            print("DEBUG: AppleScript succeeded")
            
            # Clean up temp file
            os.remove(tmp_file)
        except Exception as e1:
            logger.error(f"AppleScript method failed: {e1}")
            print(f"DEBUG: AppleScript method failed: {e1}")
            
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
                raise Exception("All typing methods failed")
        
        # Save to log file
        try:
            with open('dictation_log.txt', 'a') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {transcription}\n")
        except Exception as log_err:
            logger.error(f"Failed to write to log: {log_err}")
        
        # Play completion sound
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Pop.aiff"], check=False)
        except Exception:
            pass
            
        # Show success notification
        notify_command_executed(f"Transcribed: {transcription}")
        logger.info("Dictation completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to process dictation: {e}")
        notify_error(f"Failed to process dictation: {str(e)}")


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

# Mute state
MUTED = False

def start_recording_thread(mode):
    """Start a recording thread with specified mode.
    
    Args:
        mode (str): Either 'command' or 'dictation'
    """
    global MUTED
    
    # Check if muted
    if MUTED:
        print(f"DEBUG: Microphone is muted, ignoring {mode} request")
        
        # Show muted notification
        from toast_notifications import send_notification
        send_notification(
            "Microphone Muted", 
            "Press Ctrl+Alt+M to unmute",
            "whisper-voice-muted",
            3,
            True
        )
        return
        
    # Check if already recording
    if RECORDING:
        print(f"DEBUG: Already recording, ignoring {mode} request")
        return
        
    is_dictation = (mode == 'dictation')
    mode_name = "Dictation" if is_dictation else "Command"
    
    print(f"DEBUG: {mode_name} hotkey triggered")
    logger.info(f"{mode_name} hotkey triggered - starting voice recording...")
    
    def recording_thread_func():
        print(f"DEBUG: Starting {mode_name.lower()} recording")
        # Ensure recording completes before this function returns
        result = recorder.start_recording(dictation_mode=is_dictation)
        print(f"DEBUG: {mode_name} recording completed, audio file: {result}")
        
        # Verify the file was created and has content before continuing
        if result and os.path.exists(result):
            size = os.path.getsize(result)
            print(f"DEBUG: Audio file size: {size} bytes")
            if size < 1000:
                print("WARNING: Audio file suspiciously small, may not contain speech")
    
    # Create a thread that will block until recording is complete
    thread = threading.Thread(target=recording_thread_func)
    thread.daemon = True
    thread.start()
    
    print(f"DEBUG: {mode_name} recording thread started: {thread.name}")
    
    # IMPORTANT: Add a small delay to ensure thread starts properly
    # This prevents immediate return of the function
    time.sleep(0.2)

def hotkey_command_callback():
    """Callback for command mode hotkey."""
    start_recording_thread('command')

def hotkey_dictation_callback():
    """Callback for dictation mode hotkey."""
    start_recording_thread('dictation')

def toggle_mute_callback():
    """Toggle mute state."""
    global MUTED
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
            
        # If muted, don't process other hotkeys
        if MUTED:
            return
            
        # Check for command hotkey (Ctrl+Shift+Space)
        if CTRL_PRESSED and SHIFT_PRESSED and SPACE_PRESSED:
            print("DEBUG: Command hotkey detected: Ctrl+Shift+Space")
            logger.info("Command hotkey detected: Ctrl+Shift+Space")
            hotkey_command_callback()
            
        # Check for dictation hotkey: Ctrl+Shift+D
        if CTRL_PRESSED and SHIFT_PRESSED and D_PRESSED:
            print("DEBUG: Dictation hotkey detected: Ctrl+Shift+D")
            logger.info("Dictation hotkey detected: Ctrl+Shift+D")
            hotkey_dictation_callback()
            
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

        # Set up hotkey listeners
        command_hotkey_str = os.getenv('VOICE_CONTROL_HOTKEY', 'ctrl+shift+space')
        dictation_hotkey_str = os.getenv('VOICE_DICTATION_HOTKEY', 'ctrl+shift+d')
        
        logger.info(f"Setting up command hotkey: {command_hotkey_str}")
        logger.info(f"Setting up dictation hotkey: {dictation_hotkey_str}")
        logger.info("Also adding alternative dictation hotkey: Alt+Shift+V")
        
        # Start keyboard listener
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        
        logger.info("=== Voice Control Ready ===")
        logger.info(f"COMMAND MODE: Press {command_hotkey_str} to start recording voice commands")
        logger.info(f"MUTE TOGGLE: Press Ctrl+Shift+M to mute/unmute voice control")
        logger.info("")
        logger.info("Example commands:")
        logger.info("  'open Safari'")
        logger.info("  'maximize window'")
        logger.info("  'open terminal'")
        logger.info("  'focus chrome'")
        logger.info("  'dictate' (switches to dictation mode)")
        logger.info("")
        logger.info("Press Ctrl+C or ESC to exit")
        
        try:
            # Send a notification that we're ready
            from toast_notifications import send_notification
            send_notification(
                "Voice Control Ready", 
                f"Commands: {command_hotkey_str} | Say 'dictate' for dictation | Mute: Ctrl+Shift+M",
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