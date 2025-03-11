import os
import sys
import time
import tempfile
import logging
import subprocess
import unittest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def is_ci_environment():
    """Check if we're running in a CI environment"""
    return os.environ.get("MOCK_TEST_MODE", "false").lower() == "true"


def should_skip_audio_recording():
    """Check if audio recording should be skipped"""
    return os.environ.get("SKIP_AUDIO_RECORDING", "false").lower() == "true"


def should_skip_audio_playback():
    """Check if audio playback should be skipped"""
    return os.environ.get("SKIP_AUDIO_PLAYBACK", "false").lower() == "true"


def should_use_mock_speech():
    """Check if mock speech should be used"""
    return os.environ.get("USE_MOCK_SPEECH", "false").lower() == "true"


def setup_mock_environment():
    """Setup mock environment for testing"""
    logger.info("Setting up mock test environment")

    # Set environment variables for mocks
    if is_ci_environment():
        os.environ["MOCK_TEST_MODE"] = "true"
        os.environ["SKIP_AUDIO_RECORDING"] = "true"
        os.environ["SKIP_AUDIO_PLAYBACK"] = "true"
        os.environ["USE_MOCK_SPEECH"] = "true"

    # Return True if we're in a mock environment
    return is_ci_environment()


def get_mock_audio_data():
    """Get mock audio data for testing"""
    # Just return some empty bytes that can be used as fake audio data
    return bytes([0] * 16000)


def mock_speech_synthesis():
    """Get a mock speech synthesis function that matches our new server-based API"""

    def mock_speak(
        text,
        voice=None,  # Will use config value
        rate=1.0,
        use_high_quality=True,
        enhance_audio=True,
        block=False,
        **kwargs,
    ):
        # Default to config value if None
        if voice is None:
            voice = config.get("NEURAL_VOICE_ID", "p230")
        # Just log the text, don't actually make API calls
        logger.info(f"MOCK SPEECH (server API): {text}")
        logger.info(
            f"MOCK SPEECH PARAMS: voice={voice}, rate={rate}, "
            f"use_high_quality={use_high_quality}, enhance_audio={enhance_audio}"
        )
        return True

    return mock_speak


def mock_whisper_transcription():
    """Get a mock whisper transcription function"""

    def mock_transcribe(audio_data, **kwargs):
        logger.info(f"MOCK TRANSCRIPTION: Using {len(audio_data)} bytes of audio data")
        # Return a mock transcription result
        return {"text": "this is a mock transcription"}

    return mock_transcribe


def mock_audio_recorder():
    """Get a mock audio recorder object"""
    mock_recorder = MagicMock()
    mock_recorder.record.return_value = get_mock_audio_data()
    return mock_recorder


def patch_module(module_name, mock_obj):
    """Patch a module with a mock object for testing"""
    if module_name in sys.modules:
        original_module = sys.modules[module_name]
        sys.modules[module_name] = mock_obj
        return original_module
    else:
        sys.modules[module_name] = mock_obj
        return None


def restore_module(module_name, original_module):
    """Restore the original module after testing"""
    if original_module is not None:
        sys.modules[module_name] = original_module
    else:
        del sys.modules[module_name]


# Speech synthesis utilities
def synthesize_speech(text, voice_id=None):
    """Generate speech audio file from text using neural TTS API.

    Args:
        text (str): Text to convert to speech
        voice_id (str, optional): Voice ID to use for synthesis (defaults to NEURAL_VOICE_ID from config)

    Returns:
        str: Path to generated audio file
    """
    from audio import speech_synthesis as tts

    # Get default voice ID from config if not specified
    if voice_id is None:
        voice_id = config.get("NEURAL_VOICE_ID", "p230")

    logger.info(f"Synthesizing '{text}' using neural voice '{voice_id}'")

    # Generate the audio file using our neural speech synthesis
    audio_file = tts._call_speech_api(
        text,
        voice_id=voice_id,
        speed=1.0,
        use_high_quality=True,
        enhance_audio=True
    )

    if not audio_file:
        logger.error("Failed to synthesize speech")
        return None

    logger.info(f"Generated speech for '{text}' at {audio_file}")
    return audio_file


def play_audio_file(file_path, volume=2):
    """Play an audio file with specified volume.

    Args:
        file_path (str): Path to the audio file
        volume (int, optional): Volume level (1-2)
    """
    logger.info(f"Playing audio file: {file_path} at volume {volume}")

    if should_skip_audio_playback():
        logger.info("Audio playback skipped based on environment setting")
        return

    # Use afplay for more reliable playback
    subprocess.run(["afplay", "-v", str(volume), file_path], check=True)


def synthesize_and_play(text, voice_id=None, volume=2):
    """Synthesize speech using neural TTS and play it.

    Args:
        text (str): Text to convert to speech
        voice_id (str, optional): Voice ID to use for synthesis
        volume (int, optional): Volume level for playback

    Returns:
        str: Path to the generated audio file
    """
    audio_file = synthesize_speech(text, voice_id)
    if audio_file:
        play_audio_file(audio_file, volume)
    return audio_file


# Mock Speech Recognition API client
class MockSpeechRecognitionClient:
    """Mock SpeechRecognitionClient for testing."""

    def __init__(self, api_url=None):
        """Initialize with a mock that always succeeds."""
        self.api_url = api_url or "http://localhost:8080"
        self.connected = True

    async def check_connection(self):
        """Mock connection check that always succeeds by default."""
        return self.connected

    async def list_models(self):
        """Return dummy list of models."""
        return {
            "available_models": ["tiny", "base", "small", "medium", "large-v3"],
            "default_model": "large-v3",
            "loaded_models": ["large-v3"]
        }

    async def transcribe(self, audio_file, model_size="large-v3", language="en"):
        """Mock transcription that returns pre-defined text."""
        return {
            "text": "this is a mock transcription",
            "confidence": 0.95,
            "processing_time": 0.1
        }

    async def transcribe_audio_data(self, audio_data, model_size="large-v3", language="en"):
        """Mock transcription for raw audio data."""
        return {
            "text": "this is a mock transcription from audio data",
            "confidence": 0.95,
            "processing_time": 0.1
        }

    async def disconnect_websocket(self):
        """Mock websocket disconnection."""
        pass

def mock_speech_recognition_client():
    """Return a patch for the SpeechRecognitionClient."""
    return patch("src.api.speech_recognition_client.SpeechRecognitionClient",
                 return_value=MockSpeechRecognitionClient())

def mock_asyncio_new_event_loop():
    """Return a patch for asyncio.new_event_loop().

    This returns a mock event loop with run_until_complete method to handle coroutines.
    """
    loop = MagicMock()

    # Define a special run_until_complete method that can handle coroutines
    def mock_run_until_complete(coro):
        """Special run_until_complete that extracts values from coroutines.

        For regular coroutines from our mock classes, run it and get the result.
        For anything else, just return True as a default success value.
        """
        # If it's not awaitable, just return it
        if not hasattr(coro, '__await__'):
            return coro

        # We need to return a sensible default for all coroutines used in testing
        return True

    loop.run_until_complete = mock_run_until_complete

    # Create a patch that returns our pre-configured mock loop
    return patch("asyncio.new_event_loop", return_value=loop)

# Daemon management utilities
class DaemonManager:
    """Manages a daemon process for testing"""

    def __init__(self, log_dir=None, capture_output=True):
        """Initialize the daemon manager

        Args:
            log_dir (str, optional): Directory for log files
            capture_output (bool): Whether to capture daemon output
        """
        self.daemon = None
        self.output_file = None
        self.log_dir = log_dir
        self.capture_output = capture_output

        if self.log_dir:
            self.daemon_output_file = os.path.join(self.log_dir, "daemon_output.log")
        else:
            self.daemon_output_file = os.path.join(
                tempfile.gettempdir(), f"daemon_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )

    def start(self, wait_time=8):
        """Start the daemon process

        Args:
            wait_time (int): Initial time to wait for initialization

        Returns:
            tuple: (subprocess.Popen, file_handle)
        """
        logger.info("Starting daemon in background...")

        if self.capture_output:
            # Open file for capturing output
            self.output_file = open(self.daemon_output_file, "w")

            # Start the daemon process
            self.daemon = subprocess.Popen(
                ["python", "src/daemon.py"],
                stdout=self.output_file,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
        else:
            # Start with pipe to read output in tests
            self.daemon = subprocess.Popen(
                ["python", "src/daemon.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

        # Initial wait for daemon to start loading models
        logger.info(f"Initial wait for {wait_time} seconds...")
        time.sleep(wait_time)

        # Now poll for readiness instead of just waiting
        logger.info("Checking if daemon is ready for input...")
        max_wait = 15  # Maximum additional wait time
        poll_interval = 1  # Check every second
        start_time = time.time()
        ready = False

        while time.time() - start_time < max_wait:
            # Check if the daemon output contains a listening indicator
            if self.capture_output:
                with open(self.daemon_output_file, "r") as f:
                    content = f.read()
                    if "speech recognition api connection successful" in content.lower() or "ready for input" in content.lower():
                        ready = True
                        break

            # Short sleep before checking again
            time.sleep(poll_interval)

        if ready:
            logger.info(f"Daemon ready after {time.time() - start_time + wait_time:.1f} seconds")
        else:
            logger.info("Proceeding with tests after waiting for daemon initialization")

        return self.daemon, self.output_file

    def stop(self):
        """Stop the daemon process"""
        if not self.daemon:
            return

        logger.info("Stopping daemon...")

        # Terminate the daemon
        self.daemon.terminate()
        try:
            self.daemon.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.daemon.kill()
            logger.warning("Had to forcefully kill daemon")

        # Close output file
        if self.output_file:
            try:
                if not self.output_file.closed:
                    self.output_file.close()
            except:
                pass

        self.daemon = None
        self.output_file = None

    def check_output(self, text, timeout=10):
        """Check if text appears in daemon output file.

        Args:
            text (str): Text to search for
            timeout (int, optional): Maximum time to wait

        Returns:
            bool: True if text found, False otherwise
        """
        start_time = time.time()

        if self.capture_output:
            # Read from output file
            while time.time() - start_time < timeout:
                with open(self.daemon_output_file, "r") as f:
                    content = f.read()

                if text in content:
                    logger.info(f"Found '{text}' in daemon output")
                    return True

                time.sleep(0.5)
        else:
            # Read from stdout pipe
            while time.time() - start_time < timeout:
                try:
                    line = self.daemon.stdout.readline()
                    if text in line:
                        return True
                except (IOError, AttributeError):
                    # Handle case where stdout might be closed
                    break
                time.sleep(0.1)

        logger.warning(f"Text '{text}' not found in daemon output after {timeout} seconds")
        return False

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


# Base test class
class BaseVoiceTest(unittest.TestCase):
    """Base class for voice control tests with common setup/teardown"""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment"""
        cls.temp_files = []

        # Create log directory structure
        logs_base_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "logs",
            "test_logs",
        )
        os.makedirs(logs_base_dir, exist_ok=True)

        cls.log_dir = os.path.join(
            logs_base_dir, f"test_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(cls.log_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        # Clean up temp files
        for temp_file in cls.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_file}: {e}")

    def synthesize_speech(self, text, voice_id=None):
        """Generate speech audio file from text and track for cleanup.

        Args:
            text (str): Text to convert to speech
            voice_id (str, optional): Voice ID to use for synthesis

        Returns:
            str: Path to the generated audio file
        """
        audio_file = synthesize_speech(text, voice_id)
        if audio_file:
            self.temp_files.append(audio_file)
        return audio_file

    def play_audio_file(self, file_path, volume=2):
        """Play an audio file with specified volume.

        Args:
            file_path (str): Path to the audio file
            volume (int, optional): Volume level (1-2)
        """
        play_audio_file(file_path, volume)

    def synthesize_and_play(self, text, voice_id=None, volume=2):
        """Synthesize speech and play it, tracking the file for cleanup.

        Args:
            text (str): Text to convert to speech
            voice_id (str, optional): Voice ID to use for synthesis
            volume (int, optional): Volume level for playback

        Returns:
            str: Path to the generated audio file
        """
        audio_file = self.synthesize_speech(text, voice_id)
        if audio_file:
            self.play_audio_file(audio_file, volume)
        return audio_file
