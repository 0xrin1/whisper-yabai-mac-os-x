#!/usr/bin/env python3
"""
Voice command daemon using Whisper and Yabai for Mac OS X control.
This is the refactored version with modular architecture.
"""

import os
import time
import threading
import signal
import logging
import whisper
from dotenv import load_dotenv

# Import our modules
from src.state_manager import state
from src.audio_recorder import AudioRecorder
from src.audio_processor import processor
from src.continuous_recorder import ContinuousRecorder
from src.hotkey_manager import hotkeys
import src.speech_synthesis as tts
import src.assistant as assistant

logger = logging.getLogger('voice-control')

class VoiceControlDaemon:
    """Main daemon class for voice control system."""
    
    def __init__(self):
        """Initialize the daemon."""
        # Configure logging
        self._setup_logging()
        
        # Load environment variables
        load_dotenv()
        
        # Override global state
        state.model_size = os.getenv('WHISPER_MODEL_SIZE', 'tiny')
        state.command_trigger = "hey"
        state.dictation_trigger = "type"
        
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
                    from toast_notifications import send_notification
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
            from toast_notifications import send_notification
            send_notification(
                "Voice Control Ready with Rolling Buffer", 
                f"Just speak: '{state.command_trigger}' for commands | '{state.dictation_trigger}' for dictation | Mute: Ctrl+Shift+M",
                "whisper-voice-ready",
                10,
                True
            )
        except Exception as e:
            logger.error(f"Failed to show startup notification: {e}")

if __name__ == "__main__":
    daemon = VoiceControlDaemon()
    daemon.start()