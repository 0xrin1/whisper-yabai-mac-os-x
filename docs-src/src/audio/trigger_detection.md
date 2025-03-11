# trigger_detection

Trigger word detection module for voice control system.
Detects command and dictation trigger words in audio.

Source: `audio/trigger_detection.py`

## Class: TriggerDetector

Detects trigger words in audio to activate command or dictation modes.

## Function: `__init__(self, whisper_model=None)`

Initialize the trigger detector.

        Args:
            whisper_model: Pre-loaded Whisper model to use (will load if not provided)

## Function: `ensure_model(self)`

Ensure Whisper model is loaded.

## Function: `process_audio_buffer(self, audio_buffer)`

Process audio buffer to detect trigger words.

        Args:
            audio_buffer: List of audio frames to process

        Returns:
            dict: Detection results with trigger type and transcription

## Function: `detect_triggers(self, transcription)`

Detect trigger words in transcription.

        Args:
            transcription: Transcribed text to check for trigger words

        Returns:
            dict: Detection results with trigger type and transcription

## Function: `handle_detection(self, detection_result)`

Handle a detected trigger by starting appropriate mode.

        Args:
            detection_result: Dict with detection results

        Returns:
            bool: True if trigger was handled, False otherwise

## Function: `_start_recording_thread(self, mode, force=False)`

Start a recording thread with specified mode.

        Args:
            mode: Either 'command' or 'dictation'
            force: If True, will force start recording even if already recording
