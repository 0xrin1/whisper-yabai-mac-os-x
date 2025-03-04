#!/usr/bin/env python3
"""
Voice command daemon using Whisper and Yabai for Mac OS X control.
Unified version combining features of original and refactored implementations.
"""

import os
import time
import threading
import signal
import logging
import whisper
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

logger = logging.getLogger('voice-control')

class VoiceControlDaemon:
    """Main daemon class for voice control system."""
    
    def __init__(self, force_onboarding=False):
        """Initialize the daemon.
        
        Args:
            force_onboarding (bool, optional): Force the onboarding conversation even if not first run.
        """
        # Configure logging
        self._setup_logging()
        
        # Load environment variables
        load_dotenv()
        
        # Override global state
        state.model_size = os.getenv('WHISPER_MODEL_SIZE', 'tiny')
        state.command_trigger = "hey"
        state.dictation_trigger = "type"
        
        # Store CLI arguments
        self.force_onboarding = force_onboarding
        
        # Initialize components
        self.recorder = AudioRecorder()
        self.continuous_recorder = ContinuousRecorder()
        self.running = False
    
    def _setup_logging(self):
        """Set up logging configuration."""
        # Only set up logging if not already configured
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler()]
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
            
            # Test the speech synthesis system
            logger.info("Testing speech synthesis...")
            try:
                # Quick test of speech synthesis with minimal output
                tts.speak("Voice assistant initialized", block=True)
                logger.info("Speech synthesis working correctly")
            except Exception as e:
                logger.error(f"Error testing speech synthesis: {e}")
                # Continue without speech if it fails
            
            # Check if whisper model can be loaded
            logger.info(f"Testing Whisper model load: {state.model_size}")
            try:
                test_model = whisper.load_model(state.model_size)
                logger.info("Whisper model loaded successfully")
                # Update state with model
                state.whisper_model = test_model
            except Exception as e:
                logger.error(f"Error loading Whisper model: {e}")
                raise
            
            # Start audio processor
            logger.info("Starting audio processor...")
            processor.start()
            
            # Start hotkey listener
            logger.info("Starting hotkey listener...")
            hotkeys.start()
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.stop()
            os._exit(1)
    
    def _show_startup_banner(self):
        """Show startup banner with system information."""
        logger.info("=== Voice Control Ready ===")
        logger.info("ALWAYS LISTENING with ROLLING BUFFER")
        logger.info("THREE TRIGGER WORDS:")
        logger.info(f"1. COMMAND TRIGGER: Say '{state.command_trigger}' to activate command mode")
        logger.info(f"2. DICTATION TRIGGER: Say '{state.dictation_trigger}' to activate dictation mode")
        logger.info(f"3. ASSISTANT TRIGGER: Say 'hey Jarvis' to activate conversational assistant")
        logger.info(f"MUTE TOGGLE: Press Ctrl+Shift+M to mute/unmute voice control")
        logger.info("")
        logger.info("HOW IT WORKS:")
        logger.info("- System continuously listens with a 5-second rolling buffer")
        logger.info("- When you speak, we analyze the buffer to detect trigger words")
        logger.info("- No need to wait for a recording to start - just speak naturally")
        logger.info("")
        logger.info("COMMAND MODE: System listens for commands to control your computer")
        logger.info(f"   Say '{state.command_trigger}' to activate, then speak your command when you hear the tone")
        logger.info("   Examples: 'open Safari', 'maximize window', 'focus chrome'")
        logger.info("")
        logger.info("DICTATION MODE: System types what you say at the cursor position")
        logger.info(f"   Simply say '{state.dictation_trigger}' to start dictation immediately")
        logger.info("   Everything you say after will be typed at the cursor position")
        logger.info("   To exit dictation mode, stop speaking for 4 seconds")
        logger.info("")
        logger.info("JARVIS ASSISTANT MODE: Talk to a conversational assistant")
        logger.info("   Say 'hey Jarvis' to activate the conversational assistant")
        logger.info("   Ask questions like 'what time is it' or 'tell me a joke'")
        logger.info("   Say 'go to sleep' to exit assistant mode")
        logger.info("")
        logger.info("Press Ctrl+C or ESC to exit")
    
    def _delayed_start(self):
        """Start continuous listening after a delay."""
        def start_after_delay():
            # Wait 5 seconds for all subsystems to initialize
            logger.info("Waiting 5 seconds before starting continuous listening mode...")
            time.sleep(5)
            
            # Make sure model is loaded before starting
            if state.whisper_model is None:
                logger.info("Waiting for Whisper model to finish loading...")
                # Wait up to 15 more seconds for model to load
                for _ in range(15):
                    if state.whisper_model is not None:
                        break
                    time.sleep(1)
            
            logger.info("Now starting continuous listening mode...")
            
            if not state.is_muted():
                # Send a clear notification that we're listening for the trigger word
                try:
                    send_notification(
                        "Voice Control Ready",
                        f"Say '{state.command_trigger}' for commands | Say '{state.dictation_trigger}' for dictation",
                        "whisper-trigger-listening",
                        10,
                        False
                    )
                except Exception as e:
                    logger.error(f"Failed to show trigger notification: {e}")
                
                # Start continuous listening with rolling buffer
                self.continuous_recorder.start()
                
        threading.Thread(target=start_after_delay, daemon=True).start()
        
        try:
            # Send a notification that we're ready
            send_notification(
                "Voice Control Ready with Rolling Buffer", 
                f"Just speak: '{state.command_trigger}' for commands | '{state.dictation_trigger}' for dictation | Mute: Ctrl+Shift+M",
                "whisper-voice-ready",
                10,
                True
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
                True
            )
            
            # Introduction to how it works
            tts.speak("I'll listen for trigger phrases and respond to your voice commands.", block=True)
            time.sleep(0.5)
            
            # Explain the trigger words
            tts.speak(f"You can say '{state.command_trigger}' to activate command mode for system control.", block=True)
            time.sleep(0.5)
            
            tts.speak(f"Say '{state.dictation_trigger}' to start typing what you say.", block=True)
            time.sleep(0.5)
            
            tts.speak("Or say 'hey Jarvis' to have a conversation with me.", block=True)
            time.sleep(0.5)
            
            # Tips for best experience
            tts.speak("For best results, speak clearly and use natural commands.", block=True)
            time.sleep(0.5)
            
            # Completion message
            tts.speak("That's all! You're ready to start using voice control. Just speak naturally.", block=True)
            
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
    parser = argparse.ArgumentParser(description='Voice Control Daemon')
    parser.add_argument('--onboard', action='store_true', help='Force the onboarding conversation')
    args = parser.parse_args()
    
    # Create and start the daemon
    daemon = VoiceControlDaemon(force_onboarding=args.onboard)
    daemon.start()