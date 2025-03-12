#!/usr/bin/env python3
"""
Audio processing module for voice control system.
Handles transcription of audio files using the Speech Recognition API.
"""

import os
import time
import logging
import threading
import asyncio

from src.core.state_manager import state
from src.core.core_dictation import core_dictation
from src.utils.llm_interpreter import CommandInterpreter

# Import for notifications
from src.ui.toast_notifications import notify_processing, notify_error, send_notification

# Import the speech recognition client
from src.api.speech_recognition_client import SpeechRecognitionClient

logger = logging.getLogger("audio-processor")


class AudioProcessor:
    """Processes audio files in the queue and converts to text."""

    def __init__(self):
        """Initialize the audio processor."""
        self.running = False
        self.thread = None

        # Load LLM interpreter if available
        model_path = os.getenv("LLM_MODEL_PATH")
        self.llm_interpreter = CommandInterpreter(model_path)
        self.use_llm = os.getenv("USE_LLM", "true").lower() == "true"

        # Set minimum confidence threshold for command processing
        self.min_confidence = float(os.getenv("MIN_CONFIDENCE", "0.5"))

        # Initialize speech recognition client
        self.speech_api_url = os.getenv("SPEECH_API_URL", "http://localhost:8080")

        logger.info(f"Using Speech Recognition API at {self.speech_api_url}")
        self.speech_client = SpeechRecognitionClient(api_url=self.speech_api_url)
        # Create event loop for asyncio
        self.loop = asyncio.new_event_loop()
        # Check if API is available
        if not self.loop.run_until_complete(self.speech_client.check_connection()):
            logger.error(f"Speech Recognition API not available at {self.speech_api_url}")
            raise RuntimeError(f"Speech Recognition API not available at {self.speech_api_url}. Cannot continue.")

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

        # Clean up API client
        if hasattr(self, 'speech_client'):
            # Close any websocket connections
            try:
                self.loop.run_until_complete(self.speech_client.disconnect_websocket())
            except Exception as e:
                logger.error(f"Error disconnecting from speech API websocket: {e}")

            # Close the loop
            try:
                self.loop.close()
            except Exception as e:
                logger.error(f"Error closing asyncio loop: {e}")

            logger.info("Speech Recognition API client cleaned up")

    def check_api_connection(self):
        """Check API connection and get available models."""
        if not self.loop.run_until_complete(self.speech_client.check_connection()):
            error_msg = f"Speech Recognition API not available at {self.speech_api_url}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info("Successfully connected to Speech Recognition API")
        # Get available models from the API
        models = self.loop.run_until_complete(self.speech_client.list_models())
        logger.info(f"Available models on API server: {models}")

    def _processing_thread(self):
        """Main processing thread function."""
        logger.debug("Audio processing thread starting...")

        # Check API connection and get models
        try:
            self.check_api_connection()
        except Exception as e:
            logger.error(f"Failed to connect to Speech API: {e}")
            self.running = False
            notify_error("Failed to connect to Speech API. Cannot continue.")
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
                            logger.debug(
                                f"Processing audio in {'dictation' if is_dictation_mode else 'command'} mode"
                            )

                    elif len(audio_item) == 2:
                        # Old format: (file_path, is_dictation)
                        audio_file = audio_item[0]
                        is_dictation_mode = bool(audio_item[1])
                        logger.debug(
                            f"Processing audio in {'dictation' if is_dictation_mode else 'command'} mode"
                        )
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
                from src.ui.toast_notifications import notify_processing

                notify_processing()

                # Skip trigger mode files - they're processed by the trigger detector
                if is_trigger_mode:
                    logger.debug(
                        "Skipping trigger mode file - already processed by trigger detector"
                    )
                    # Clean up the audio file
                    try:
                        os.unlink(audio_file)
                    except Exception as unlink_err:
                        logger.debug(f"Failed to delete temp file: {unlink_err}")
                    continue

                # Always use the Speech Recognition API
                try:
                    # Read the audio file
                    with open(audio_file, "rb") as f:
                        audio_data = f.read()

                    # Call the API
                    result = self.loop.run_until_complete(
                        self.speech_client.transcribe_audio_data(
                            audio_data,
                            model_size=state.model_size
                        )
                    )

                    if "error" in result:
                        raise Exception(f"API error: {result['error']}")

                    transcription = result.get("text", "").strip()
                    confidence = result.get("confidence", 1.0)
                    logger.debug(
                        f"API Transcription: '{transcription}', confidence: {confidence:.2f}"
                    )
                except Exception as e:
                    logger.error(f"Error using Speech Recognition API: {e}")

                    # Import here to avoid circular imports
                    from src.ui.toast_notifications import notify_error

                    notify_error("Speech recognition API failed. Please check API server.")

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
                if (
                    not transcription
                    or len(transcription) < 3
                    or all(c.isspace() or c in ".,;!?" for c in transcription)
                ):
                    logger.warning(f"Empty or noise transcription: '{transcription}'")

                    # Import here to avoid circular imports
                    from src.ui.toast_notifications import notify_error

                    notify_error("No clear speech detected")
                    continue

                # Notify transcription callbacks (for API and cloud code)
                state.notify_transcription(
                    transcription,
                    is_command=(not is_dictation_mode),
                    confidence=confidence
                )

                # Process based on mode
                if is_dictation_mode:
                    logger.debug(f"Processing as dictation text: '{transcription}'")
                    core_dictation.type_text(transcription)
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
                            from src.ui.toast_notifications import send_notification

                            send_notification(
                                "Command Recognized",
                                f"Processing: {transcription}",
                                "whisper-command-recognized",
                                3,
                                True,
                            )
                        except Exception as e:
                            logger.error(f"Failed to show command notification: {e}")

                    except Exception as e:
                        logger.error(f"Error executing command: {e}")
                        import traceback

                        logger.error(traceback.format_exc())

                    logger.debug("Command processing flow completed")
                else:
                    logger.warning(
                        f"Low confidence command: {confidence:.2f} < {self.min_confidence}"
                    )

                    # Import here to avoid circular imports
                    from src.ui.toast_notifications import notify_error

                    notify_error(f"Low confidence: {transcription}")

            except Exception as e:
                logger.error(f"Transcription error: {e}")

                # Import here to avoid circular imports
                from src.ui.toast_notifications import notify_error

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
            command, args = self.llm_interpreter.interpret_command(
                transcription.lower()
            )

            # For dictation commands, handle those
            if command in ["dictate", "dictation", "type", "write", "text"]:
                logger.info(f"LLM interpreted dictation command: {command}")
                return self._start_dictation_mode()
            elif command == "none":
                logger.info("LLM determined input was not a command")
                return False

            # Try dynamic response for other cases
            logger.info("Checking for dynamic response")
            dynamic_response = self.llm_interpreter.generate_dynamic_response(
                transcription.lower()
            )

            if dynamic_response.get("is_command", False):
                action = dynamic_response.get("action", "")
                logger.info(f"Dynamic interpretation: {action}")

                # In the simplified architecture, we only support dictation
                if action in ["dictate", "dictation", "type", "write", "text"]:
                    logger.info(
                        f"LLM interpreter triggered dictation mode with action: '{action}'"
                    )
                    return self._start_dictation_mode()
                else:
                    logger.info(f"Unsupported action in simplified architecture: {action}")
                    from src.ui.toast_notifications import notify_error
                    notify_error(f"Command '{action}' not supported in this mode")
                    return False

        # Check for dictation trigger words in transcription directly
        dictation_fragments = ["dictate", "dictation", "dict", "type", "write", "text", "note"]
        for fragment in dictation_fragments:
            if fragment in transcription.lower():
                logger.info(f"Detected dictation command: '{fragment}' in '{transcription}'")
                return self._start_dictation_mode()

        # No command was recognized, send notification
        logger.info(f"No recognized command in: '{transcription}'")
        from src.ui.toast_notifications import notify_error
        notify_error(f"Not recognized as a command")
        return False

    def _start_dictation_mode(self):
        """Start dictation mode.

        Returns:
            bool: True if dictation mode was started successfully
        """
        try:
            # Visual notification of mode switch
            from src.ui.toast_notifications import send_notification

            send_notification(
                "Starting Dictation Mode",
                "LLM detected dictation request - will type what you say",
                "whisper-dictation-llm",
                3,
                True,
            )

            # Import here to avoid circular imports
            from src.audio.trigger_detection import TriggerDetector

            detector = TriggerDetector()
            detector._start_recording_thread("dictation", force=True)
            return True
        except Exception as e:
            logger.error(f"Failed to start dictation mode: {e}")
            return False


# Create a singleton instance, but allow for testing mode
# If TESTING environment variable is set, don't initialize processor yet
if os.getenv("TESTING", "false").lower() != "true":
    processor = AudioProcessor()
else:
    # In testing mode, just create a placeholder that will be replaced in tests
    processor = None
