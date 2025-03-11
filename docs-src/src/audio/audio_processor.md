# audio_processor

Audio processing module for voice control system.
Handles transcription of audio files using Whisper.

Source: `audio/audio_processor.py`

## Class: AudioProcessor

Processes audio files in the queue and converts to text.

## Function: `__init__(self)`

Initialize the audio processor.

## Function: `start(self)`

Start processing audio in a background thread.

## Function: `stop(self)`

Stop audio processing.

## Function: `load_model(self)`

Load the Whisper model.

## Function: `_processing_thread(self)`

Main processing thread function.

## Function: `_process_command(self, transcription)`

Process a command transcription.

        Args:
            transcription: Transcribed text to process as a command

        Returns:
            bool: True if command was processed successfully

## Function: `_start_dictation_mode(self)`

Start dictation mode.

        Returns:
            bool: True if dictation mode was started successfully
