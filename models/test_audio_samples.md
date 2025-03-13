# Test Audio Samples

This directory is used for storing test audio samples used by the test suite.

Audio files placed here should be:
1. Small in size (preferably under 1MB)
2. Short in duration (1-5 seconds)
3. Clear examples of specific speech patterns or commands

## Sample Types

The test suite expects these standard samples:
- `silence.wav` - A short audio file containing silence
- `trigger_word.wav` - Audio containing the trigger word "hey"
- `command.wav` - Audio containing a simple command

You can generate test samples using the `scripts/generate_test_samples.py` script or add your own recordings.