#!/usr/bin/env python3
"""
Trigger word detection module for voice control system.
Detects command and dictation trigger words in audio.
"""

import os
import time
import threading
import subprocess
import tempfile
import wave
import logging
import numpy as np
import asyncio

from src.core.state_manager import state
from src.audio.audio_recorder import AudioRecorder
from src.api.speech_recognition_client import SpeechRecognitionClient

logger = logging.getLogger("trigger-detection")


class TriggerDetector:
    """Detects trigger words in audio to activate command or dictation modes."""

    def __init__(self):
        """Initialize the trigger detector."""
        self.recorder = AudioRecorder()

        # Initialize speech recognition client
        self.speech_api_url = os.getenv("SPEECH_API_URL", "http://localhost:8080")
        self.speech_client = SpeechRecognitionClient(api_url=self.speech_api_url)
        self.loop = asyncio.new_event_loop()

        # Trigger word variations for more robust detection
        # Command mode is now triggered by Jarvis
        self.command_variations = [
            "jarvis",
            "hey jarvis",
            "hi jarvis",
            "hello jarvis",
            "ok jarvis",
            "hey jarvis",
            "jarvis please",
        ]

        # Keep dictation variations for explicit dictation trigger
        # (though dictation is now the default mode)
        self.dictation_variations = [
            state.dictation_trigger.lower(),
            "typing",
            "write",
            "note",
            "text",
            "speech to text",
            "tight",
            "tipe",
            "types",
            "typed",
            "typ",
            "tape",
            "time",
            "tip",
            "tie",
            "type please",
            "please type",
            "start typing",
            "begin typing",
            "activate typing",
            "time please",
            "time this",
            "type this",
            "dictate",
            "dictation",
            "take dictation",
            "start dictation",
            "dictate this",
            "write this",
            "take notes",
            "ti",
            "ty",
            "tai",
        ]

        # Jarvis variations are now the same as command variations
        self.jarvis_variations = self.command_variations

    def check_api_connection(self):
        """Check API connection and verify it's available."""
        try:
            if not self.loop.run_until_complete(self.speech_client.check_connection()):
                error_msg = f"Speech Recognition API not available at {self.speech_api_url}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            logger.info("Successfully connected to Speech Recognition API")
        except Exception as e:
            logger.error(f"Failed to connect to Speech API: {e}")
            raise

    def process_audio_buffer(self, audio_buffer):
        """Process audio buffer to detect trigger words.

        Args:
            audio_buffer: List of audio frames to process

        Returns:
            dict: Detection results with trigger type and transcription
        """
        if not audio_buffer or len(audio_buffer) < 10:
            logger.debug("Buffer too small to process")
            return {"detected": False}

        # Check API connection
        try:
            self.check_api_connection()
        except Exception as e:
            logger.error(f"Speech API unavailable: {e}")
            return {"detected": False}

        logger.debug(f"Processing audio buffer with {len(audio_buffer)} frames")

        # Save buffer to a temporary WAV file
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_filename = temp_file.name
            temp_file.close()

            wf = wave.open(temp_filename, "wb")
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)  # 16kHz

            # Join frames and write to file
            joined_frames = b"".join(audio_buffer)
            wf.writeframes(joined_frames)
            wf.close()

            logger.debug(f"Audio buffer saved to {temp_filename}")

            # Use Speech API to transcribe the buffer
            try:
                # Read the audio file
                with open(temp_filename, "rb") as f:
                    audio_data = f.read()

                # Call the API
                result = self.loop.run_until_complete(
                    self.speech_client.transcribe_audio_data(
                        audio_data,
                        model_size=state.model_size,
                        language="en"
                    )
                )

                if "error" in result:
                    raise Exception(f"API error: {result['error']}")

                transcription = result.get("text", "").strip().lower()
            except Exception as e:
                logger.error(f"Error during API transcription: {e}")
                return {"detected": False}

            logger.debug(f"Buffer transcription: '{transcription}'")

            # Check for trigger words
            detection_result = self.detect_triggers(transcription)

            # Clean up the temporary file
            try:
                os.unlink(temp_filename)
            except Exception as e:
                logger.debug(f"Failed to delete temp file: {e}")

            return detection_result

        except Exception as e:
            logger.error(f"Error processing audio buffer: {e}")
            return {"detected": False}

    def detect_triggers(self, transcription):
        """Detect trigger words in transcription.

        Args:
            transcription: Transcribed text to check for trigger words

        Returns:
            dict: Detection results with trigger type and transcription
        """
        result = {
            "detected": True,  # Default to detected as we'll use dictation by default
            "transcription": transcription,
            "trigger_type": "dictation",  # Default to dictation mode
        }

        # Check for Jarvis trigger - this will now activate Cloud Code
        contains_jarvis_trigger = any(
            variation in transcription.lower() for variation in self.command_variations
        )

        # Process Jarvis trigger to activate Code Agent
        if contains_jarvis_trigger:
            logger.info(f"Jarvis trigger detected for Code Agent: '{transcription}'")
            # Extract the query part (remove jarvis trigger)
            for trigger in self.command_variations:
                if trigger in transcription.lower():
                    # Get everything after the trigger word
                    trigger_pos = transcription.lower().find(trigger) + len(trigger)
                    query = transcription[trigger_pos:].strip()
                    # If there's a query, use it, otherwise use the whole text
                    if query:
                        result["transcription"] = query
                    # Set to code_agent type
                    result["trigger_type"] = "code_agent"
                    break
        # Otherwise use dictation as the default
        else:
            logger.info(f"No Jarvis trigger detected, defaulting to dictation mode: '{transcription}'")
            result["trigger_type"] = "dictation"

        return result

    def handle_detection(self, detection_result):
        """Handle a detected trigger by starting appropriate mode.

        Args:
            detection_result: Dict with detection results

        Returns:
            bool: True if trigger was handled, False otherwise
        """
        if not detection_result["detected"]:
            return False

        trigger_type = detection_result["trigger_type"]
        transcription = detection_result["transcription"]

        # Handle Code Agent request (triggered by "jarvis")
        if trigger_type == "code_agent":
            # Play a notification sound
            self.recorder.play_sound("command")

            # Add conversational response when Jarvis is triggered
            from src.audio.speech_synthesis import speak_random

            # Respond with a Jarvis-style greeting
            speak_random("jarvis_greeting")

            # Only if there's an actual query after "jarvis", process it with Code Agent
            if transcription.strip():
                # Add a notification to show we're processing with Code Agent
                try:
                    from src.ui.toast_notifications import send_notification

                    send_notification(
                        "Code Agent Activated",
                        f"Processing: {transcription[:30]}{'...' if len(transcription) > 30 else ''}",
                        "whisper-code-agent",
                        3,
                        False,
                    )
                except Exception as e:
                    logger.error(f"Failed to show Code Agent notification: {e}")

                # Send the query to Code Agent
                try:
                    # Import here to avoid circular imports
                    from src.utils.code_agent import CodeAgentHandler
                    from src.core.state_manager import state

                    # Create a temporary instance if we don't have one
                    handler = CodeAgentHandler(state)

                    # Generate a unique session ID
                    session_id = f"voice_{int(time.time())}"

                    # Submit the request
                    request_id = handler.submit_request(transcription, session_id)

                    logger.info(f"Submitted Code Agent request: {request_id} with query: '{transcription}'")

                    # Process the request synchronously for immediate response
                    try:
                        response = handler._process_request({
                            "id": request_id,
                            "prompt": transcription,
                            "session_id": session_id,
                            "submitted_at": time.time(),
                        })

                        # Speak the response
                        from src.audio.speech_synthesis import speak
                        speak(response)

                        logger.info(f"Code Agent response: {response[:100]}{'...' if len(response) > 100 else ''}")
                    except Exception as e:
                        logger.error(f"Error processing Code Agent response: {e}")

                        # Notify of the error
                        from src.ui.toast_notifications import notify_error
                        notify_error("Failed to process request")
                except Exception as e:
                    logger.error(f"Failed to submit Code Agent request: {e}")

            return True

        # Default to dictation mode
        else:
            # Play the dictation sound - only use audio cues for dictation, no spoken responses
            self.recorder.play_sound("dictation")

            # Add a notification to clearly show we're entering dictation mode
            try:
                from src.ui.toast_notifications import send_notification

                send_notification(
                    "Dictation Mode Activated",
                    "Everything you say will be typed as text",
                    "whisper-dictation-direct",
                    3,
                    True,
                )
            except Exception as e:
                logger.error(f"Failed to show dictation notification: {e}")

            # Start dictation mode - no voice feedback needed for dictation, just sound cues
            self._start_recording_thread("dictation", force=True)
            return True

    def _start_recording_thread(self, mode, force=False):
        """Start a recording thread with specified mode.

        Args:
            mode: Either 'command' or 'dictation'
            force: If True, will force start recording even if already recording
        """
        # Normalize the mode parameter
        if mode.lower() in ["dictate", "dictation", "typing"]:
            mode = "dictation"
        else:
            mode = "command"

        # Check if muted
        if state.is_muted():
            logger.debug(f"Microphone is muted, ignoring {mode} request")
            return

        is_dictation = mode == "dictation"
        mode_name = "Dictation" if is_dictation else "Command"

        logger.info(f"{mode_name} mode triggered - starting voice recording...")

        def recording_thread_func():
            logger.debug(f"Starting {mode_name.lower()} recording")

            try:
                # Ensure recording completes before this function returns
                result = self.recorder.start_recording(
                    dictation_mode=is_dictation, force=force
                )
                logger.debug(f"{mode_name} recording completed, audio file: {result}")
            except Exception as e:
                logger.error(f"Error in recording thread: {e}")
                import traceback

                logger.error(traceback.format_exc())

        # Create a thread that will block until recording is complete
        thread = threading.Thread(target=recording_thread_func)
        thread.daemon = True
        thread.start()

        logger.debug(f"{mode_name} recording thread started: {thread.name}")

        # Add a small delay to ensure thread starts properly
        time.sleep(0.7)
