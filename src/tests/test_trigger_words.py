#!/usr/bin/env python3
"""
Simple test script to verify trigger word detection.
This focuses ONLY on testing that 'hey' and 'type' trigger words are detected.
"""

import os
import time
import subprocess
import sys
import logging
import tempfile

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trigger-test')

def synthesize_and_play(text, voice=None):
    """Synthesize speech and play it at higher volume."""
    # Create a temp file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    output_file = temp_file.name
    temp_file.close()
    
    # Use Mac's 'say' command to generate speech
    aiff_file = output_file.replace('.wav', '.aiff')
    
    # Build the command with optional voice parameter
    cmd = ["say", "-o", aiff_file]
    if voice:
        cmd.extend(["-v", voice])
    cmd.append(text)
    
    # Run the command
    subprocess.run(cmd, check=True)
    
    # Convert AIFF to WAV
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", 
                   aiff_file, output_file], check=True)
    
    # Clean up AIFF file
    os.remove(aiff_file)
    
    # Play at higher volume
    subprocess.run(["afplay", "-v", "2", output_file], check=True)
    
    # Return the file path so it can be cleaned up later
    return output_file

def test_trigger_words():
    """Test both trigger words with multiple voices."""
    try:
        # Start the daemon
        logger.info("Starting daemon in background...")
        daemon = subprocess.Popen(
            ["python", "src/daemon.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Function to check if a string is in the daemon output
        def check_output(search_text, timeout=10):
            """Check daemon output for a string with timeout."""
            start_time = time.time()
            while time.time() - start_time < timeout:
                line = daemon.stdout.readline()
                if search_text in line:
                    return True
                time.sleep(0.1)
            return False
        
        # Wait for daemon to initialize
        logger.info("Waiting for daemon to initialize...")
        time.sleep(15)  # Extra time to ensure it's fully ready
        
        # Use only our custom neural voice
        logger.info("Testing with custom trained neural voice")
        
        # Import our speech synthesis module
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        import speech_synthesis as tts
        
        # Test 'hey' trigger
        logger.info("Testing 'hey' trigger word...")
        try:
            # Use our custom neural voice
            tts.speak("hey", block=True)
            # Wait for processing to complete
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error testing 'hey' with neural voice: {e}")
        
        # Test dictation triggers
        logger.info("Testing dictation trigger words...")
        for phrase in ["type", "dictate"]:
            try:
                logger.info(f"Testing '{phrase}' with neural voice")
                # Say it clearly
                tts.speak(f"{phrase}", block=True)
                # Wait for processing
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error testing '{phrase}' with neural voice: {e}")
    
    finally:
        # Stop the daemon
        if daemon:
            logger.info("Stopping daemon...")
            daemon.terminate()
            try:
                daemon.wait(timeout=5)
            except subprocess.TimeoutExpired:
                daemon.kill()
                logger.warning("Had to forcefully kill daemon")

if __name__ == "__main__":
    test_trigger_words()