# audio_recorder

Audio recording module for voice control system.
Handles recording from microphone with smart silence detection.

Source: `audio/audio_recorder.py`

## Class: AudioRecorder

Records audio from microphone with configurable parameters.

## Function: `play_sound(self, sound_type: str)`

Play a sound to indicate recording status.

        Args:
            sound_type: Type of sound to play ('start', 'stop', 'dictation', 'command')

## Function: `stop_recording(self)`

Stop the current recording.

## Function: `cleanup(self)`

Clean up PyAudio resources.
