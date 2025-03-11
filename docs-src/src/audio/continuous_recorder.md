# continuous_recorder

Continuous recording module for voice control system.
Manages a rolling buffer of audio to detect trigger words.

Source: `audio/continuous_recorder.py`

## Class: ContinuousRecorder

Records continuously in the background with a rolling buffer.

## Function: `__init__(self, buffer_seconds=5)`

Initialize continuous recorder.

        Args:
            buffer_seconds: Number of seconds to keep in the rolling buffer

## Function: `start(self)`

Start continuous recording in a background thread.

## Function: `stop(self)`

Stop continuous recording.

## Function: `_recording_thread(self)`

Main recording thread function.

## Function: `_process_buffer(self)`

Process the audio buffer to detect trigger words.
