# simple_dictation

Simplified standalone dictation daemon.
Uses core dictation functionality with simplified interface.

Source: `utils/simple_dictation.py`

## Class: SimpleAudioRecorder

Records audio from microphone with simplified interface.

## Function: `transcribe_and_type(audio_file: str)`

Transcribe audio file using Whisper and type it.

    Args:
        audio_file: Path to audio file to transcribe

## Function: `on_press(key)`

Handle key press events.

    Args:
        key: The key that was pressed

    Returns:
        False to stop listener, None to continue

## Function: `on_release(key)`

Handle key release events.

    Args:
        key: The key that was released

    Returns:
        False to stop listener, None to continue

## Function: `show_banner()`

Show application banner and instructions.
