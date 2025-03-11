# dictation

Dictation processing module for voice control system.
Converts speech to text and types it at the cursor position.

Source: `utils/dictation.py`

## Class: DictationProcessor

Process dictation by typing text at cursor.
    Extends core dictation with additional functionality.

## Function: `__init__(self)`

Initialize dictation processor.

## Function: `process(self, transcription: str)`

Process dictation by typing text at cursor.

        Args:
            transcription: The text to type

        Returns:
            bool: True if dictation was processed successfully

## Function: `_preprocess_text(self, text: str)`

Pre-process text before typing.
        Handles capitalization, formatting, and other text transformations.

        Args:
            text: Raw transcription text

        Returns:
            Processed text ready for typing
