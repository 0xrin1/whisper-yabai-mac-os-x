# resource_manager

Resource management utilities for the voice control system.
Provides consistent resource handling patterns across modules.

Source: `audio/resource_manager.py`

## Class: TempAudioFile

Manages temporary audio files with automatic cleanup.

## Function: `__init__(self, suffix: str = '.wav', delete: bool = True)`

Create a temporary audio file.
        
        Args:
            suffix: File suffix (default: .wav)
            delete: Whether to delete file on cleanup (default: True)

## Function: `keep(self)`

Prevent the file from being deleted on cleanup.

## Function: `save_audio_frames(
    frames: List[bytes],
    filename: str,
    channels: Optional[int] = None,
    sample_width: Optional[int] = None,
    rate: Optional[int] = None,
    p: Optional[pyaudio.PyAudio] = None
)`

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

## Function: `play_system_sound(sound_name: str = "Pop")`

Play a system sound.
    
    Args:
        sound_name: Name of system sound (without path or extension)
        
    Returns:
        True if successful, False otherwise

