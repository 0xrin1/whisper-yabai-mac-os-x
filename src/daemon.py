#!/usr/bin/env python3
"""
Voice command daemon using Speech Recognition API and Yabai for Mac OS X control.
Unified version combining features of original and refactored implementations.
"""

import os
import time
import threading
import signal
import logging
import argparse
from dotenv import load_dotenv

# Import our modules
# Add import paths
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.state_manager import state
from src.audio.audio_recorder import AudioRecorder
from src.audio.audio_processor import processor
from src.audio.continuous_recorder import ContinuousRecorder
from src.utils.hotkey_manager import hotkeys
import src.audio.speech_synthesis as tts
import src.utils.assistant as assistant
from src.ui.toast_notifications import send_notification

# Import code agent components
try:
    from src.api.api_server import APIServer
    from src.utils.code_agent import CodeAgentHandler
    api_available = True
except ImportError:
    api_available = False
    logging.getLogger("voice-control").warning("API server components not available. Code agent features will be disabled.")

logger = logging.getLogger("voice-control")


class VoiceControlDaemon:
    """Main daemon class for voice control system."""

    def __init__(self, force_onboarding=False, api_enabled=True):
        """Initialize the daemon.

        Args:
            force_onboarding (bool, optional): Force the onboarding conversation even if not first run.
            api_enabled (bool, optional): Enable the API server for cloud code integration.
        """
        # Configure logging
        self._setup_logging()

        # Load environment variables
        load_dotenv()

        # Override global state
        state.model_size = os.getenv("WHISPER_MODEL_SIZE", "tiny")
        state.command_trigger = "jarvis"
        state.dictation_trigger = "type"  # Kept for backward compatibility, but not required anymore

        # Store CLI arguments
        self.force_onboarding = force_onboarding
        self.api_enabled = api_enabled and api_available

        # Initialize components
        self.recorder = AudioRecorder()
        self.continuous_recorder = ContinuousRecorder()
        self.running = False

        # API and code agent components
        self.api_server = None
        self.code_agent_handler = None

    def _setup_logging(self):
        """Set up logging configuration."""
        # Only set up logging if not already configured
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[logging.StreamHandler()],
            )

    def start(self):
        """Start the daemon."""
        logger.info("Starting voice control daemon...")
        self.running = True

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Initialize components
        self._initialize_components()

        # Show startup banner
        self._show_startup_banner()

        # Show onboarding conversation if this is first run
        self._show_onboarding_conversation()

        # Start continuous recording with delay
        self._delayed_start()

        # Keep the main thread alive
        while self.running:
            # Check if hotkey listener is still alive
            if not hotkeys.listener.running:
                logger.info("Keyboard listener stopped. Exiting...")
                break
            time.sleep(1)

    def stop(self):
        """Stop the daemon."""
        logger.info("Shutting down voice control daemon...")
        self.running = False

        # Stop components
        processor.stop()
        self.continuous_recorder.stop()
        hotkeys.stop()

        # Stop API and code agent components if they exist
        if self.api_server:
            logger.info("Stopping API server...")
            self.api_server.stop()

        if self.code_agent_handler:
            logger.info("Stopping Code Agent handler...")
            self.code_agent_handler.stop()

        # Clean up resources
        self.recorder.cleanup()

        logger.info("Voice control daemon stopped.")

    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {sig}")
        self.stop()

        # Exit
        os._exit(0)

    def _initialize_components(self):
        """Initialize all system components."""
        try:
            # Initialize audio recorder
            logger.info("Initializing audio recorder...")

            # Initialize JARVIS assistant
            logger.info("Initializing JARVIS assistant...")
            try:
                assistant.init_assistant()
                logger.info("JARVIS assistant initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing JARVIS assistant: {e}")
                # Continue without JARVIS if it fails to initialize

            # Test the speech synthesis system with Jarvis startup greeting
            logger.info("Testing speech synthesis with dynamic Jarvis startup greeting...")
            try:
                # Import the Ollama API-based greeting generator
                try:
                    from src.utils.ollama_greeting_generator import generate_greeting
                    logger.info("Using direct Ollama API-based greeting generator")
                except ImportError:
                    try:
                        # Try OpenAI SDK-based generator as second option
                        from src.utils.openai_greeting_generator import generate_greeting
                        logger.info("Using OpenAI SDK-based greeting generator")
                    except ImportError:
                        # Fall back to the original greeting generator if neither is available
                        from src.utils.llm_greeting_generator import generate_greeting
                        logger.info("Using fallback greeting generator")
                
                # Try to generate a dynamic greeting using the LLM
                try:
                    # Try to get a dynamic greeting, but with a short timeout to not delay startup
                    import threading
                    import time
                    
                    # Flag to track if generation was successful
                    generated = [False]
                    greeting = [None]
                    
                    def generate_with_timeout():
                        try:
                            result = generate_greeting()
                            if result:
                                greeting[0] = result
                                generated[0] = True
                        except Exception as e:
                            logger.warning(f"Error in greeting generation thread: {e}")
                    
                    # Start generation in a separate thread
                    gen_thread = threading.Thread(target=generate_with_timeout)
                    gen_thread.daemon = True
                    gen_thread.start()
                    
                    # Wait for up to 5 seconds for generation to complete
                    start_time = time.time()
                    while time.time() - start_time < 5 and not generated[0]:
                        time.sleep(0.2)
                    
                    if generated[0] and greeting[0]:
                        # Successfully generated a greeting
                        dynamic_greeting = greeting[0]
                        # Verify the greeting is not a thinking or debugging message
                        # Check for various thinking patterns or unusually long responses
                        if ("<think>" in dynamic_greeting or 
                            dynamic_greeting.startswith("<") or 
                            dynamic_greeting.startswith("I should") or 
                            dynamic_greeting.startswith("Let me") or 
                            dynamic_greeting.startswith("Okay") or
                            "user wants" in dynamic_greeting or
                            len(dynamic_greeting) > 100):
                            logger.warning(f"Invalid greeting format: '{dynamic_greeting[:50]}...' - falling back to predefined")
                            tts.speak_random("jarvis_startup", block=True)
                        else:
                            logger.info(f"Using dynamically generated greeting: '{dynamic_greeting}'")
                            # Speak the dynamic greeting
                            tts.speak(dynamic_greeting, block=True)
                            logger.info("Dynamic greeting generated and spoken successfully")
                    else:
                        # Generation failed or timed out
                        logger.warning("Falling back to predefined greeting due to timeout or generation failure")
                        # Fall back to predefined greeting
                        tts.speak_random("jarvis_startup", block=True)
                        
                except Exception as e:
                    logger.warning(f"Falling back to predefined greeting due to error: {e}")
                    # Fall back to predefined greeting if generation fails
                    tts.speak_random("jarvis_startup", block=True)
                
                logger.info("Speech synthesis working correctly")
            except Exception as e:
                logger.error(f"Error testing speech synthesis: {e}")
                # Continue without speech if it fails

            # Check if Speech API is available - only in non-testing mode
            if os.getenv("TESTING", "false").lower() != "true":
                logger.info("Testing Speech Recognition API connection...")
                try:
                    # Import here to avoid circular imports
                    from src.api.speech_recognition_client import SpeechRecognitionClient
                    import asyncio

                    speech_api_url = os.getenv("SPEECH_API_URL", "http://localhost:8080")
                    client = SpeechRecognitionClient(api_url=speech_api_url)
                    loop = asyncio.new_event_loop()

                    if not loop.run_until_complete(client.check_connection()):
                        error_msg = f"Speech Recognition API not available at {speech_api_url}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)

                    logger.info("Speech Recognition API connection successful")

                    # Get available models
                    models = loop.run_until_complete(client.list_models())
                    logger.info(f"Available models on API: {models}")

                    # Clean up
                    loop.close()
                except Exception as e:
                    logger.error(f"Error connecting to Speech Recognition API: {e}")
                    raise
            else:
                logger.info("TESTING mode: Skipping Speech Recognition API check")

            # Start audio processor
            logger.info("Starting audio processor...")
            processor.start()

            # Start hotkey listener
            logger.info("Starting hotkey listener...")
            hotkeys.start()

            # Always initialize Cloud Code components for "jarvis" commands
            # (API server is only started if specifically enabled)
            self._initialize_cloud_components()

        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            import traceback

            logger.error(traceback.format_exc())
            self.stop()
            os._exit(1)

    def _initialize_cloud_components(self):
        """Initialize API server and Code Agent handler."""
        try:
            # Initialize Code Agent handler (always initialize for voice commands)
            logger.info("Initializing Code Agent handler...")
            from src.config.config import config
            self.code_agent_handler = CodeAgentHandler(state)
            self.code_agent_handler.start()
            logger.info("Code Agent handler initialized successfully")

            # Initialize API server (only if API is explicitly enabled)
            if self.api_enabled:
                logger.info("Initializing API server...")
                self.api_server = APIServer(state, config)

                # Get API port and host from environment or default
                api_port = int(os.getenv("API_PORT", "8000"))
                api_host = os.getenv("API_HOST", "127.0.0.1")

                # Start the API server
                self.api_server.start(host=api_host, port=api_port)
                logger.info(f"API server started on {api_host}:{api_port}")

                # Notify user
                send_notification(
                    "Cloud Code API Ready",
                    f"API server running at http://{api_host}:{api_port}",
                    "whisper-cloud-api",
                    5,
                    True,
                )

                # Announce via speech synthesis
                tts.speak("Cloud Code API is now ready for integration", block=False)
            else:
                logger.info("API server not enabled, but Code Agent handler is ready for 'jarvis' commands")

        except Exception as e:
            logger.error(f"Error initializing cloud components: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue without cloud components if they fail to initialize

    def _show_startup_banner(self):
        """Show startup banner with system information."""
        logger.info("=== Voice Control Ready ===")
        logger.info("ALWAYS LISTENING with ROLLING BUFFER")
        logger.info("DEFAULT MODE: DICTATION")
        logger.info(
            f"CLOUD CODE TRIGGER: Say '{state.command_trigger}' to talk to Claude Code"
        )
        logger.info(f"MUTE TOGGLE: Press Ctrl+Shift+M to mute/unmute voice control")
        logger.info("")
        logger.info("HOW IT WORKS:")
        logger.info("- System continuously listens with a 5-second rolling buffer")
        logger.info("- When you speak, it automatically transcribes to text (dictation mode)")
        logger.info("- Say 'jarvis' followed by your question to talk to Claude Code")
        logger.info("- No need to wait for a recording to start - just speak naturally")
        logger.info("")
        logger.info(
            "CLOUD CODE MODE: Talk to Claude Code AI assistant"
        )
        logger.info(
            f"   Say '{state.command_trigger}' followed by your question"
        )
        logger.info("   Examples: 'jarvis what's the weather today', 'jarvis tell me a joke'")
        logger.info("")
        logger.info("DICTATION MODE: System types what you say at the cursor position")

        # Show cloud code status if enabled
        if self.api_enabled:
            api_port = int(os.getenv("API_PORT", "8000"))
            api_host = os.getenv("API_HOST", "127.0.0.1")
            logger.info("")
            logger.info("CLOUD CODE API:")
            logger.info(f"- API server enabled on http://{api_host}:{api_port}")
            logger.info("- Speech transcriptions available via WebSocket")
            logger.info("- Cloud Code integration ready for use")
            logger.info(f"- Access API documentation at http://{api_host}:{api_port}/docs")
        logger.info(
            "   DEFAULT MODE - just speak naturally and your words will be typed"
        )
        logger.info("   Everything you say will be typed at the cursor position")
        logger.info("   To exit dictation mode, stop speaking for 4 seconds")
        logger.info("")
        logger.info("Press Ctrl+C or ESC to exit")

    def _delayed_start(self):
        """Start continuous listening after a delay."""

        def start_after_delay():
            # Wait 5 seconds for all subsystems to initialize
            logger.info(
                "Waiting 5 seconds before starting continuous listening mode..."
            )
            time.sleep(5)

            # Short delay to ensure all subsystems are ready
            logger.info("Finalizing initialization...")
            time.sleep(2)

            logger.info("Now starting continuous listening mode...")

            if not state.is_muted():
                # Send a clear notification that we're listening for the trigger word
                try:
                    send_notification(
                        "Voice Control Ready",
                        f"Just speak for dictation | Say '{state.command_trigger}' for commands",
                        "whisper-trigger-listening",
                        10,
                        False,
                    )
                except Exception as e:
                    logger.error(f"Failed to show trigger notification: {e}")

                # Initial startup greeting - only on app launch, not regular dictation
                try:
                    # Only speak on app startup, not when entering dictation mode during use
                    if self.force_onboarding or self._is_first_run():
                        # Use dynamic Jarvis greeting for welcome on first start
                        try:
                            # Import the Ollama API-based greeting generator
                            try:
                                from src.utils.ollama_greeting_generator import generate_greeting
                                logger.info("Using direct Ollama API-based greeting generator for onboarding")
                            except ImportError:
                                try:
                                    # Try OpenAI SDK-based generator as second option
                                    from src.utils.openai_greeting_generator import generate_greeting
                                    logger.info("Using OpenAI SDK-based greeting generator for onboarding")
                                except ImportError:
                                    # Fall back to the original greeting generator if neither is available
                                    from src.utils.llm_greeting_generator import generate_greeting
                                    logger.info("Using fallback greeting generator for onboarding")
                                
                            from src.audio.speech_synthesis import speak, speak_random
                            import threading
                            import time
                            
                            # Try to generate with a short timeout
                            generated = [False]
                            greeting = [None]
                            
                            def generate_with_timeout():
                                try:
                                    result = generate_greeting()
                                    if result:
                                        greeting[0] = result
                                        generated[0] = True
                                except Exception as e:
                                    logger.warning(f"Error in greeting generation thread: {e}")
                            
                            # Start generation in a separate thread
                            gen_thread = threading.Thread(target=generate_with_timeout)
                            gen_thread.daemon = True
                            gen_thread.start()
                            
                            # Wait for up to 5 seconds for generation to complete
                            start_time = time.time()
                            while time.time() - start_time < 5 and not generated[0]:
                                time.sleep(0.2)
                            
                            if generated[0] and greeting[0]:
                                # Successfully generated a greeting
                                dynamic_greeting = greeting[0]
                                # Verify the greeting is not a thinking or debugging message
                                # Check for various thinking patterns or unusually long responses
                                if ("<think>" in dynamic_greeting or 
                                    dynamic_greeting.startswith("<") or 
                                    dynamic_greeting.startswith("I should") or 
                                    dynamic_greeting.startswith("Let me") or 
                                    dynamic_greeting.startswith("Okay") or
                                    "user wants" in dynamic_greeting or
                                    len(dynamic_greeting) > 100):
                                    logger.warning(f"Invalid greeting format: '{dynamic_greeting[:50]}...' - falling back to predefined")
                                    speak_random("jarvis_startup", block=True)
                                else:
                                    speak(dynamic_greeting, block=True)
                                    logger.info(f"Played dynamic startup greeting on first run: '{dynamic_greeting}'")
                            else:
                                # Generation failed or timed out
                                logger.warning("Falling back to predefined greeting due to timeout")
                                speak_random("jarvis_startup")
                                logger.info("Played predefined startup greeting on first run")
                                
                        except Exception as e:
                            # Fall back to predefined greeting
                            logger.warning(f"Falling back to predefined greeting: {e}")
                            from src.audio.speech_synthesis import speak_random
                            speak_random("jarvis_startup")
                            logger.info("Played predefined startup greeting on first run")
                    else:
                        logger.info("Skipping startup greeting for returning user")
                except Exception as e:
                    logger.error(f"Failed to handle Jarvis startup message: {e}")

                # Start continuous listening with rolling buffer
                self.continuous_recorder.start()

                # Automatically start dictation mode right away
                try:
                    # Import here to avoid circular imports
                    from src.audio.trigger_detection import TriggerDetector
                    detector = TriggerDetector()

                    # Create a detection result that defaults to dictation mode
                    dictation_result = {
                        "detected": True,
                        "trigger_type": "dictation",
                        "transcription": ""
                    }

                    # Handle the detection (starts dictation mode)
                    detector.handle_detection(dictation_result)
                    logger.info("Automatically started dictation mode on startup")
                except Exception as e:
                    logger.error(f"Failed to automatically start dictation mode: {e}")

        threading.Thread(target=start_after_delay, daemon=True).start()

        try:
            # Send a notification that we're ready
            send_notification(
                "Voice Control Ready with Rolling Buffer",
                f"Just speak for dictation | Say '{state.command_trigger}' for commands | Mute: Ctrl+Shift+M",
                "whisper-voice-ready",
                10,
                True,
            )
        except Exception as e:
            logger.error(f"Failed to show startup notification: {e}")

    def _show_onboarding_conversation(self):
        """Show interactive onboarding conversation for first-time users."""
        # Check if this is first run or if onboarding is forced
        if not self._is_first_run() and not self.force_onboarding:
            logger.debug("Skipping onboarding conversation for returning user")
            return

        logger.info("Starting onboarding conversation for user")

        try:
            # Onboarding welcome
            tts.speak("Welcome to Voice Control! I'm your voice assistant.", block=True)
            time.sleep(0.5)

            # Send a notification with welcome message
            send_notification(
                "Voice Control Welcome",
                "Let's get you started with a brief orientation",
                "whisper-welcome",
                15,
                True,
            )

            # Introduction to how it works
            tts.speak(
                "I'll listen for trigger phrases and respond to your voice commands.",
                block=True,
            )
            time.sleep(0.5)

            # Explain the modes
            tts.speak(
                "By default, I'll type whatever you say as dictation.",
                block=True,
            )
            time.sleep(0.5)

            tts.speak(
                f"If you want to talk to Claude Code, just say '{state.command_trigger}' followed by your question.",
                block=True,
            )
            time.sleep(0.5)

            # Tips for best experience
            tts.speak(
                "For best results, speak clearly and use natural commands.", block=True
            )
            time.sleep(0.5)

            # Completion message
            tts.speak(
                "That's all! You're ready to start using voice control. Just speak naturally.",
                block=True,
            )

            # Mark as introduced so we don't show this again
            self._mark_as_introduced()

        except Exception as e:
            logger.error(f"Error during onboarding: {e}")

    def _is_first_run(self):
        """Check if this is the first run of the application.

        Returns:
            bool: True if this is the first run, False otherwise
        """
        # We use a marker file to determine if the user has been introduced
        user_home = os.path.expanduser("~")
        marker_dir = os.path.join(user_home, ".config", "voice-control")
        marker_file = os.path.join(marker_dir, "introduced.txt")

        return not os.path.exists(marker_file)

    def _mark_as_introduced(self):
        """Mark that the user has been introduced to the system."""
        # Create the marker file
        user_home = os.path.expanduser("~")
        marker_dir = os.path.join(user_home, ".config", "voice-control")
        marker_file = os.path.join(marker_dir, "introduced.txt")

        # Create directory if it doesn't exist
        os.makedirs(marker_dir, exist_ok=True)

        # Write the marker file with timestamp
        with open(marker_file, "w") as f:
            f.write(f"Introduced at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        logger.info(f"Marked user as introduced in {marker_file}")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Voice Control Daemon")
    parser.add_argument(
        "--onboard", action="store_true", help="Force the onboarding conversation"
    )
    parser.add_argument(
        "--api", action="store_true", help="Enable the Cloud Code API server"
    )
    parser.add_argument(
        "--api-port", type=int, default=8000, help="Port for the API server"
    )
    parser.add_argument(
        "--api-host", type=str, default="127.0.0.1", help="Host for the API server"
    )
    args = parser.parse_args()

    # Set environment variables for API if provided
    if args.api:
        os.environ["API_PORT"] = str(args.api_port)
        os.environ["API_HOST"] = args.api_host

    # Create and start the daemon
    daemon = VoiceControlDaemon(force_onboarding=args.onboard, api_enabled=args.api)
    daemon.start()
