#!/usr/bin/env python3
"""
Audio processing module for voice control system.
Handles transcription of audio files using Whisper.
"""

import os
import time
import logging
import threading
import whisper
import torch

from src.state_manager import state
from src.dictation import dictation
from src.llm_interpreter import CommandInterpreter

# Import for command processing
from src.command_processor import commands

logger = logging.getLogger('audio-processor')

class AudioProcessor:
    """Processes audio files in the queue and converts to text."""
    
    def __init__(self):
        """Initialize the audio processor."""
        self.running = False
        self.thread = None
        self.whisper_model = None
        
        # Load LLM interpreter if available
        model_path = os.getenv('LLM_MODEL_PATH')
        self.llm_interpreter = CommandInterpreter(model_path)
        self.use_llm = os.getenv('USE_LLM', 'true').lower() == 'true'
        
        # Set minimum confidence threshold for command processing
        self.min_confidence = float(os.getenv('MIN_CONFIDENCE', '0.5'))
    
    def start(self):
        """Start processing audio in a background thread."""
        if self.running:
            logger.debug("Audio processor already running")
            return
            
        logger.info("Starting audio processing thread...")
        self.running = True
        self.thread = threading.Thread(target=self._processing_thread)
        self.thread.daemon = True
        self.thread.start()
        
        logger.debug(f"Audio processing thread started: {self.thread.name}")
    
    def stop(self):
        """Stop audio processing."""
        if not self.running:
            return
            
        logger.info("Stopping audio processing...")
        self.running = False
        
        # Add None to the queue to signal the processor to exit
        state.enqueue_audio(None)
        
        if self.thread:
            self.thread.join(2.0)  # Wait up to 2 seconds for thread to end
    
    def load_model(self):
        """Load the Whisper model."""
        if self.whisper_model is not None:
            return
            
        try:
            logger.info(f"Loading Whisper model: {state.model_size}")
            start_time = time.time()
            self.whisper_model = whisper.load_model(state.model_size)
            load_time = time.time() - start_time
            logger.info(f"Whisper model loaded in {load_time:.2f} seconds")
            
            # Update global state
            state.whisper_model = self.whisper_model
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def _processing_thread(self):
        """Main processing thread function."""
        logger.debug("Audio processing thread starting...")
        
        # Load the Whisper model
        try:
            self.load_model()
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.running = False
            return
        
        if self.use_llm:
            logger.info("LLM command interpretation enabled")
        else:
            logger.info("Using simple command parsing (LLM disabled)")
        
        logger.debug("Audio processing thread ready and listening for queue items...")
        
        # Main processing loop
        while self.running:
            audio_file = None
            
            try:
                # Get the next audio file from the queue
                logger.debug("Waiting for item in audio queue...")
                audio_item = state.get_next_audio()
                
                if audio_item is None:
                    logger.debug("Found None in queue, exiting thread")
                    break
                
                # Process audio item - determine mode and extract file path
                is_dictation_mode = False
                is_trigger_mode = False
                
                if isinstance(audio_item, tuple):
                    if len(audio_item) == 3:
                        # Format: (file_path, is_dictation, is_trigger)
                        audio_file = audio_item[0]
                        is_dictation_mode = bool(audio_item[1])
                        is_trigger_mode = bool(audio_item[2])
                        
                        if is_trigger_mode:
                            logger.debug(f"Processing audio for trigger word detection")
                        else:
                            logger.debug(f"Processing audio in {'dictation' if is_dictation_mode else 'command'} mode")
                            
                    elif len(audio_item) == 2:
                        # Old format: (file_path, is_dictation)
                        audio_file = audio_item[0]
                        is_dictation_mode = bool(audio_item[1])
                        logger.debug(f"Processing audio in {'dictation' if is_dictation_mode else 'command'} mode")
                elif isinstance(audio_item, str):
                    # Simple file path - command mode
                    audio_file = audio_item
                    logger.debug("Processing audio in command mode")
                else:
                    logger.error(f"Unknown audio queue item format: {type(audio_item)}")
                    continue
                    
                if not os.path.exists(audio_file):
                    logger.error(f"Audio file not found: {audio_file}")
                    continue
                    
                logger.info(f"Processing audio file: {audio_file}")
                
                # Import here to avoid circular imports
                from toast_notifications import notify_processing
                notify_processing()
                
                # Skip trigger mode files - they're processed by the trigger detector
                if is_trigger_mode:
                    logger.debug("Skipping trigger mode file - already processed by trigger detector")
                    # Clean up the audio file
                    try:
                        os.unlink(audio_file)
                    except Exception as unlink_err:
                        logger.debug(f"Failed to delete temp file: {unlink_err}")
                    continue
                
                # Normal transcription for command/dictation modes with context clearing
                try:
                    # Create fresh transcription context each time
                    result = self.whisper_model.transcribe(
                        audio_file,
                        initial_prompt=None  # Explicitly clear prompt context
                    )
                    # Force memory cleanup to prevent context accumulation
                    torch.cuda.empty_cache() if hasattr(torch, 'cuda') and torch is not None else None
                    
                    transcription = result["text"].strip()
                    confidence = result.get("confidence", 1.0)
                    logger.debug(f"Transcription: '{transcription}', confidence: {confidence:.2f}")
                except Exception as e:
                    logger.error(f"Error during audio transcription: {e}")
                    # Try to reload the model if transcription failed
                    try:
                        logger.debug("Attempting to reload Whisper model due to error")
                        self.whisper_model = whisper.load_model(state.model_size)
                        state.whisper_model = self.whisper_model
                        # Retry transcription with fresh model
                        result = self.whisper_model.transcribe(audio_file)
                        transcription = result["text"].strip()
                        confidence = result.get("confidence", 1.0)
                        logger.debug(f"Transcription (after reload): '{transcription}', confidence: {confidence:.2f}")
                    except Exception as reload_err:
                        logger.error(f"Failed to reload model: {reload_err}")
                        
                        # Import here to avoid circular imports
                        from toast_notifications import notify_error
                        notify_error("Speech recognition failed. Please try again.")
                        
                        # Clean up if error occurred
                        if audio_file and os.path.exists(audio_file):
                            try:
                                os.unlink(audio_file)
                            except:
                                pass
                        continue
                
                # Clean up the audio file
                try:
                    os.unlink(audio_file)
                except Exception as unlink_err:
                    logger.debug(f"Failed to delete temp file: {unlink_err}")
                
                # Skip empty or noise transcriptions
                if not transcription or len(transcription) < 3 or all(c.isspace() or c in ".,;!?" for c in transcription):
                    logger.warning(f"Empty or noise transcription: '{transcription}'")
                    
                    # Import here to avoid circular imports
                    from toast_notifications import notify_error
                    notify_error("No clear speech detected")
                    continue
                
                # Process based on mode
                if is_dictation_mode:
                    logger.debug(f"Processing as dictation text: '{transcription}'")
                    dictation.process(transcription)
                    logger.debug("Dictation processing completed")
                elif confidence >= self.min_confidence:
                    logger.debug("========== PROCESSING COMMAND ==========")
                    logger.debug(f"Processing as command: '{transcription}'")
                    
                    # Try executing the command
                    try:
                        self._process_command(transcription)
                        logger.debug("Command processing completed successfully")
                        
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
                            logger.error(f"Failed to show command notification: {e}")
                            
                    except Exception as e:
                        logger.error(f"Error executing command: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        
                    logger.debug("Command processing flow completed")
                else:
                    logger.warning(f"Low confidence command: {confidence:.2f} < {self.min_confidence}")
                    
                    # Import here to avoid circular imports
                    from toast_notifications import notify_error
                    notify_error(f"Low confidence: {transcription}")
                
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                
                # Import here to avoid circular imports
                from toast_notifications import notify_error
                notify_error(f"Failed to transcribe audio: {str(e)}")
                
                # Clean up if error occurred
                if audio_file and os.path.exists(audio_file):
                    try:
                        os.unlink(audio_file)
                    except:
                        pass
    
    def _process_command(self, transcription):
        """Process a command transcription.
        
        Args:
            transcription: Transcribed text to process as a command
            
        Returns:
            bool: True if command was processed successfully
        """
        # First, try LLM interpretation if enabled
        if self.use_llm and self.llm_interpreter.llm is not None:
            # Interpret the command using the LLM
            command, args = self.llm_interpreter.interpret_command(transcription.lower())
            
            # If we got a recognized command, execute it
            if command and command != "none" and commands.has_command(command):
                logger.info(f"LLM interpreted command: {command} with args: {args}")
                return commands.execute(command, args)
            elif command == "none":
                logger.info("LLM determined input was not a command")
                return False
            
            # If no command was recognized, try to get a dynamic response
            logger.info("No direct command match, trying dynamic interpretation")
            dynamic_response = self.llm_interpreter.generate_dynamic_response(transcription.lower())
            
            if dynamic_response.get('is_command', False):
                action = dynamic_response.get('action', '')
                app = dynamic_response.get('application', '')
                params = dynamic_response.get('parameters', [])
                
                logger.info(f"Dynamic interpretation: {action} {app} {params}")
                
                # Map dynamic response to executable commands
                if action == "open" and app:
                    return commands.open_application([app])
                elif action == "focus" and app:
                    return commands.focus_application([app])
                elif action == "maximize":
                    return commands.maximize_window([])
                elif action == "move" and params:
                    return commands.move_window(params)
                elif action == "resize" and params:
                    return commands.resize_window(params)
                elif action == "close":
                    return commands.close_window([])
                elif action == "type" and params:
                    return commands.type_text(params)
                elif action in ["dictate", "dictation", "type", "write", "text"]:
                    logger.info(f"LLM interpreter triggered dictation mode with action: '{action}'")
                    return self._start_dictation_mode()
        
        # Fall back to simple command parsing
        logger.info("Falling back to simple command parsing")
        return commands.parse_and_execute(transcription.lower())
    
    def _start_dictation_mode(self):
        """Start dictation mode.
        
        Returns:
            bool: True if dictation mode was started successfully
        """
        try:
            # Visual notification of mode switch
            from toast_notifications import send_notification
            send_notification(
                "Starting Dictation Mode", 
                "LLM detected dictation request - will type what you say",
                "whisper-dictation-llm",
                3,
                True
            )
            
            # Import here to avoid circular imports
            from trigger_detection import TriggerDetector
            detector = TriggerDetector()
            detector._start_recording_thread('dictation', force=True)
            return True
        except Exception as e:
            logger.error(f"Failed to start dictation mode: {e}")
            return False

# Create a singleton instance
processor = AudioProcessor()