#!/usr/bin/env python3
"""
Resource management utilities for the voice control system.
Provides consistent resource handling patterns across modules.
"""

import os
import tempfile
import logging
import pyaudio
import wave
from typing import Optional, List, Any, Generator
from contextlib import contextmanager

from src.error_handler import handle_error
from src.config import config

logger = logging.getLogger('resource-manager')

@contextmanager
def audio_device() -> Generator[pyaudio.PyAudio, None, None]:
    """
    Context manager for PyAudio resources.
    Ensures proper cleanup of PyAudio resources.
    
    Yields:
        PyAudio instance
    """
    p = pyaudio.PyAudio()
    try:
        yield p
    finally:
        p.terminate()
        logger.debug("PyAudio resources cleaned up")

@contextmanager
def audio_stream(p: pyaudio.PyAudio, **kwargs) -> Generator[pyaudio.Stream, None, None]:
    """
    Context manager for PyAudio stream.
    
    Args:
        p: PyAudio instance
        **kwargs: Parameters for opening the stream
        
    Yields:
        PyAudio stream
    """
    # Use configuration for default parameters if not provided
    if 'format' not in kwargs:
        kwargs['format'] = getattr(pyaudio, config.get('FORMAT', 'paInt16'))
    if 'channels' not in kwargs:
        kwargs['channels'] = config.get('CHANNELS', 1)
    if 'rate' not in kwargs:
        kwargs['rate'] = config.get('RATE', 16000)
    if 'frames_per_buffer' not in kwargs and 'input' in kwargs and kwargs['input']:
        kwargs['frames_per_buffer'] = config.get('CHUNK_SIZE', 1024)
    
    stream = p.open(**kwargs)
    try:
        yield stream
    finally:
        stream.stop_stream()
        stream.close()
        logger.debug("Audio stream closed")

class TempAudioFile:
    """
    Manages temporary audio files with automatic cleanup.
    """
    
    def __init__(self, suffix: str = '.wav', delete: bool = True):
        """
        Create a temporary audio file.
        
        Args:
            suffix: File suffix (default: .wav)
            delete: Whether to delete file on cleanup (default: True)
        """
        self.temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        self.filename = self.temp_file.name
        self.temp_file.close()
        self._delete = delete
        logger.debug(f"Created temporary audio file: {self.filename}")
    
    def __enter__(self) -> str:
        """Context manager entry point."""
        return self.filename
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up temporary file on context exit."""
        if self._delete and os.path.exists(self.filename):
            try:
                os.remove(self.filename)
                logger.debug(f"Removed temporary audio file: {self.filename}")
            except Exception as e:
                handle_error(e, logger, "Failed to remove temporary audio file")
    
    def keep(self) -> None:
        """Prevent the file from being deleted on cleanup."""
        self._delete = False
        logger.debug(f"Marked temporary file to keep: {self.filename}")

def save_audio_frames(
    frames: List[bytes],
    filename: str,
    channels: Optional[int] = None,
    sample_width: Optional[int] = None,
    rate: Optional[int] = None,
    p: Optional[pyaudio.PyAudio] = None
) -> bool:
    """
    Save audio frames to a WAV file.
    
    Args:
        frames: List of audio frames
        filename: Output filename
        channels: Number of channels (default from config)
        sample_width: Sample width in bytes (default from PyAudio)
        rate: Sample rate (default from config)
        p: PyAudio instance (if None, creates temporary instance)
        
    Returns:
        True if successful, False otherwise
    """
    # Use configuration for default parameters
    if channels is None:
        channels = config.get('CHANNELS', 1)
    if rate is None:
        rate = config.get('RATE', 16000)
    
    # Handle PyAudio instance
    close_p = False
    if p is None:
        p = pyaudio.PyAudio()
        close_p = True
    
    # Use format from config for sample width if not provided
    if sample_width is None:
        format_name = config.get('FORMAT', 'paInt16')
        format_value = getattr(pyaudio, format_name)
        sample_width = p.get_sample_size(format_value)
    
    try:
        # Save audio data to WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(b''.join(frames))
            
        logger.debug(f"Saved audio to {filename}")
        return True
        
    except Exception as e:
        handle_error(e, logger, f"Failed to save audio to {filename}")
        return False
        
    finally:
        # Clean up PyAudio if we created it
        if close_p:
            p.terminate()

def play_system_sound(sound_name: str = "Pop") -> bool:
    """
    Play a system sound.
    
    Args:
        sound_name: Name of system sound (without path or extension)
        
    Returns:
        True if successful, False otherwise
    """
    sound_file = f"/System/Library/Sounds/{sound_name}.aiff"
    
    if not os.path.exists(sound_file):
        logger.warning(f"System sound not found: {sound_file}")
        return False
        
    try:
        import subprocess
        subprocess.run(["afplay", sound_file], check=False)
        return True
    except Exception as e:
        handle_error(e, logger, f"Failed to play system sound: {sound_name}")
        return False