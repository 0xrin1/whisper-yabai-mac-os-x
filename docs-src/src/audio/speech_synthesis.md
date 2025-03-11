# speech_synthesis

Speech synthesis module for the voice control system.
Provides natural-sounding TTS capabilities using macOS's native voices or custom voice models.
Supports custom voice models created from your own voice samples.
Now with support for neural voice models trained with GlowTTS.

Source: `audio/speech_synthesis.py`

## Function: `get_random_response(category: str)`

Get a random response from a specific category.

    Args:
        category: The category of response to get

    Returns:
        A random response string

## Function: `speak(text: str, voice: str = DEFAULT_VOICE, rate: int = DEFAULT_RATE,
          block: bool = False, volume: float = 1.0)`

Speak the provided text using macOS TTS.

    Args:
        text: The text to speak
        voice: The voice to use
        rate: The speaking rate (words per minute)
        block: Whether to block until speech is complete
        volume: Volume level (0.0 to 1.0)

## Function: `_speak_with_custom_voice(text: str, rate: int = DEFAULT_RATE, volume: float = 1.0)`

Use custom voice model for speech.

    Args:
        text: The text to speak
        rate: The speaking rate
        volume: Volume level (0.0 to 1.0)

    Returns:
        Boolean indicating success

## Function: `_speak_now(text: str, voice: str = DEFAULT_VOICE, rate: int = DEFAULT_RATE,
               volume: float = 1.0)`

Actually execute the TTS command (internal use).

    Args:
        text: The text to speak
        voice: The voice to use
        rate: The speaking rate
        volume: Volume level (0.0 to 1.0)

## Function: `_process_speech_queue()`

Process the speech queue in a separate thread.

## Function: `_ensure_queue_processor_running()`

Ensure the queue processor thread is running.

## Function: `stop_speaking()`

Stop all speech immediately.

## Function: `get_voice_info(voice: str)`

Get information about a specific voice.

    Args:
        voice: The voice name

    Returns:
        Dictionary with voice characteristics or None if voice doesn't exist

## Function: `is_speaking()`

Check if the system is currently speaking.

    Returns:
        True if speaking, False otherwise

## Function: `greeting(name: Optional[str] = None)`

Speak a greeting.

    Args:
        name: Optional name to personalize the greeting

## Function: `acknowledge()`

Speak an acknowledgment phrase.

## Function: `confirm()`

Speak a confirmation phrase.

## Function: `thinking()`

Indicate that the system is thinking.

## Function: `farewell()`

Speak a farewell phrase.

## Function: `test_voices()`

Test all available voices with a sample phrase.

## Function: `test_neural_voice()`

Test the neural voice model specifically.

## Function: `reload_voice_model()`

Reload the active voice model (useful if a new model was just created).

## Function: `is_neural_voice_active()`

Check if a neural voice model is active.

    Returns:
        Boolean indicating if neural voice is active
