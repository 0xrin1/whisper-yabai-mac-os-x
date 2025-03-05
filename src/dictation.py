#!/usr/bin/env python3
"""
Dictation processing module for voice control system.
Converts speech to text and types it at the cursor position.
"""

import logging
from typing import Optional

from src.core_dictation import core_dictation
from src.error_handler import handle_error, safe_execute

logger = logging.getLogger('dictation')

class DictationProcessor:
    """
    Process dictation by typing text at cursor.
    Extends core dictation with additional functionality.
    """
    
    def __init__(self):
        """Initialize dictation processor."""
        # This class is now a thin wrapper around core_dictation
        pass
    
    def process(self, transcription: str) -> bool:
        """
        Process dictation by typing text at cursor.
        
        Args:
            transcription: The text to type
        
        Returns:
            bool: True if dictation was processed successfully
        """
        logger.info(f"Processing dictation: '{transcription}'")
        
        # Pre-process the text if needed
        processed_text = self._preprocess_text(transcription)
        
        # Use core dictation to type the text
        success = core_dictation.type_text(processed_text)
        
        # Additional dictation-specific functionality could be added here
        
        return success
    
    def _preprocess_text(self, text: str) -> str:
        """
        Pre-process text before typing.
        Handles capitalization, formatting, and other text transformations.
        
        Args:
            text: Raw transcription text
            
        Returns:
            Processed text ready for typing
        """
        # For now, just return the text unchanged
        # Future implementations could add smart capitalization,
        # punctuation, or other text processing
        return text

# Create a singleton instance
dictation = DictationProcessor()