# assistant

Conversational assistant module for the voice control system.
Provides JARVIS-like conversational interface with speech synthesis and recognition.

Source: `utils/assistant.py`

## Function: `add_to_memory(role: str, content: str)`

Add an interaction to the conversation memory.

    Args:
        role: Either 'user' or 'assistant'
        content: The message content

## Function: `get_memory_as_string()`

Get the conversation memory as a formatted string.

    Returns:
        A string with the recent conversation history

## Function: `activate_assistant(voice: str = None)`

Activate the assistant and announce its presence.

    Args:
        voice: Optional voice to use (if None, uses current voice)

## Function: `deactivate_assistant()`

Deactivate the assistant with a farewell message.

## Function: `handle_user_input(text: str)`

Process user input and generate appropriate response.

    Args:
        text: The user's transcribed speech

    Returns:
        Assistant's response text

## Function: `execute_command(command_name: str, full_text: str)`

Execute a named command based on the user's input.

    Args:
        command_name: The function name to call
        full_text: The user's full input text

    Returns:
        The assistant's response

## Function: `get_time()`

Get the current time as a human-readable string.

## Function: `get_date()`

Get the current date as a human-readable string.

## Function: `get_weather()`

Get the current weather (placeholder for now).

## Function: `get_status()`

Get the system status.

## Function: `get_status_personal()`

Respond to 'how are you' type questions.

## Function: `tell_joke()`

Tell a random joke.

## Function: `identify_self()`

Identify the assistant.

## Function: `list_abilities()`

List what the assistant can do.

## Function: `update_status(status: str)`

Update the status display in the terminal.

    Args:
        status: The status message to display

## Function: `process_voice_command(transcription: str)`

Process a voice command from the main voice control system.

    Args:
        transcription: The transcribed user speech

## Function: `should_timeout()`

Check if the assistant should timeout due to inactivity.

    Returns:
        True if the assistant should timeout, False otherwise

    Note:
        Timeout occurs exactly at TIMEOUT_SECONDS after last interaction.
        This function is designed to be testable with mock time.time() patches.

## Function: `check_timeout_thread()`

Thread to check for assistant timeouts.

## Function: `init_assistant()`

Initialize the assistant module.

## Function: `test_assistant()`

Run comprehensive tests for the assistant functionality.

    This implements a TDD approach to verify all functionality works.

## Function: `run_test(name, func)`

Run a single test and report results
