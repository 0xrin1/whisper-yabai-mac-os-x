#!/usr/bin/env python3
"""
Conversational assistant module for the voice control system.
Provides JARVIS-like conversational interface with speech synthesis and recognition.
"""

import os
import sys
import time
import json
import threading
import random
import datetime
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple, Any

# Import our own modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.audio import speech_synthesis as tts
from src.ui.toast_notifications import send_notification

# Status display constants
STATUS_LINE = 0
STATUS_PREFIX = "JARVIS STATUS: "
last_status = ""

# Constants for assistant behavior
ASSISTANT_NAME = "JARVIS"
USER_NAME = "Sir"  # Can be changed through configuration
WAKE_WORD = "hey"  # Same as trigger word in main system

# Conversational memory - store recent interactions
MAX_MEMORY_ITEMS = 10
conversation_memory = []
memory_lock = threading.Lock()

# Assistant state
assistant_state = {
    "active": False,
    "conversational_mode": False,
    "last_interaction_time": 0,
    "voice": "daniel",  # Default to Daniel (British male voice)
}

# Predefined responses for various scenarios
RESPONSES = {
    "greeting": [
        f"Hello, {USER_NAME}. How may I assist you today?",
        f"Good to see you, {USER_NAME}. What can I do for you?",
        f"At your service, {USER_NAME}. How can I help?",
        f"Hello. I'm listening.",
    ],
    "farewell": [
        f"Goodbye, {USER_NAME}. Call if you need me.",
        "Signing off now. I'll be here when you need me.",
        "Entering standby mode.",
        "I'll be here if you need anything else."
    ],
    "acknowledgment": [
        "Right away, sir.",
        "Consider it done.",
        "On it.",
        "I'm on it.",
        "Working on that now."
    ],
    "uncertain": [
        "I'm not sure I understand. Could you rephrase that?",
        "I didn't quite catch that. Could you try again?",
        "I'm afraid I don't know how to help with that.",
        "I'm still learning and don't know how to do that yet."
    ],
    "time": [
        "It's currently {time}.",
        "The time is {time}.",
        "Right now it's {time}.",
    ],
    "date": [
        "Today is {date}.",
        "It's {date} today.",
        "The date is {date}.",
    ],
    "status": [
        "All systems operational.",
        "Everything is running smoothly.",
        "Systems are functioning normally.",
        "All processes running within normal parameters."
    ],
    "weather_placeholder": [
        "I'm afraid I don't have access to current weather data.",
        "I can't check the weather at the moment.",
        "Weather information is not available right now."
    ],
    "joke": [
        "Why don't scientists trust atoms? Because they make up everything.",
        "I'm reading a book about anti-gravity. It's impossible to put down.",
        "Did you hear about the mathematician who's afraid of negative numbers? He'll stop at nothing to avoid them.",
        "Why was the computer cold? It left its Windows open.",
        "What do you call a fake noodle? An impasta."
    ]
}

# Command patterns for natural language understanding
COMMAND_PATTERNS = [
    # Time and date
    (r"\b(?:what(?:'s| is) the|tell me the|current) time\b", "get_time"),
    (r"\b(?:what(?:'s| is) the|tell me the|current) date\b", "get_date"),
    
    # Weather
    (r"\b(?:what(?:'s| is) the|how(?:'s| is) the|tell me the) weather\b", "get_weather"),
    
    # System status
    (r"\b(?:system|status) (?:status|report)\b", "get_status"),
    (r"\bhow are you\b", "get_status_personal"),
    
    # Jokes and entertainment
    (r"\btell me a joke\b", "tell_joke"),
    
    # Wake/sleep
    (r"\bgo to sleep\b", "go_to_sleep"),
    (r"\bwake up\b", "wake_up"),
    
    # Identity
    (r"\bwho are you\b", "identify_self"),
    (r"\bwhat(?:'s| is) your name\b", "identify_self"),
    
    # Help
    (r"\bwhat can you do\b", "list_abilities"),
    (r"\bhelp\b", "list_abilities"),
    
    # Casual conversation
    (r"\b(?:hello|hi|hey|greetings)\b", "greeting"),
    (r"\b(?:goodbye|bye|see you|later)\b", "farewell"),
    (r"\bthanks?\b", "acknowledge_thanks"),
]

def add_to_memory(role: str, content: str) -> None:
    """Add an interaction to the conversation memory.
    
    Args:
        role: Either 'user' or 'assistant'
        content: The message content
    """
    with memory_lock:
        timestamp = time.time()
        conversation_memory.append({
            "role": role,
            "content": content,
            "timestamp": timestamp
        })
        
        # Trim memory if it gets too long
        if len(conversation_memory) > MAX_MEMORY_ITEMS:
            conversation_memory.pop(0)
        
        # Update last interaction time
        if role == 'user':
            assistant_state["last_interaction_time"] = timestamp

def get_memory_as_string() -> str:
    """Get the conversation memory as a formatted string.
    
    Returns:
        A string with the recent conversation history
    """
    with memory_lock:
        result = ""
        for item in conversation_memory:
            role_display = "You" if item["role"] == "user" else ASSISTANT_NAME
            result += f"{role_display}: {item['content']}\n"
        return result

def activate_assistant(voice: str = None) -> None:
    """Activate the assistant and announce its presence.
    
    Args:
        voice: Optional voice to use (if None, uses current voice)
    """
    if voice:
        assistant_state["voice"] = voice
    
    assistant_state["active"] = True
    assistant_state["conversational_mode"] = True
    assistant_state["last_interaction_time"] = time.time()
    
    # Update the console status (instead of printing a new line)
    update_status(f"{ASSISTANT_NAME} activated")
    
    # Play a distinct sound to indicate activation
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Submarine.aiff"], check=False)
    except Exception:
        pass
        
    # Small pause to make sure sound is heard
    time.sleep(0.3)
    
    # Proactively ask what the user wants (starting the conversation)
    question = random.choice([
        f"How can I assist you today, {USER_NAME}?",
        f"What can I help you with, {USER_NAME}?",
        f"I'm at your service. What do you need?",
        f"Ready and listening. What would you like me to do?"
    ])
    
    # Speak the question
    update_status(f"{ASSISTANT_NAME} speaking: '{question}'")
    tts.speak(question, voice=assistant_state["voice"], block=True)
    
    # Add to conversation memory
    add_to_memory("assistant", question)
    
    # Indicate we're now listening
    update_status(f"{ASSISTANT_NAME} listening for command")
    
    # No notification needed here - the voice is feedback enough

def deactivate_assistant() -> None:
    """Deactivate the assistant with a farewell message."""
    if not assistant_state["active"]:
        return
    
    # Update status display    
    update_status("Deactivating assistant")
    
    # Speak a farewell message
    farewell = random.choice(RESPONSES["farewell"])
    update_status(f"Speaking farewell: '{farewell}'")
    tts.speak(
        farewell,
        voice=assistant_state["voice"],
        block=True  # Wait for farewell to complete
    )
    
    # Update state
    assistant_state["active"] = False
    assistant_state["conversational_mode"] = False
    
    # Clear status line but don't send a notification
    update_status("Assistant deactivated - standby mode")
    
    # Play a sound to indicate deactivation
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Submarine.aiff"], check=False)
    except Exception:
        pass

def handle_user_input(text: str) -> str:
    """Process user input and generate appropriate response.
    
    Args:
        text: The user's transcribed speech
        
    Returns:
        Assistant's response text
    """
    # Add to conversation memory
    add_to_memory("user", text)
    
    # Clean the text for processing
    clean_text = text.strip().lower()
    
    # Check for explicit wake/sleep commands first
    if re.search(r"\bgo to sleep\b", clean_text):
        response = random.choice(RESPONSES["farewell"])
        add_to_memory("assistant", response)
        
        # For tests, deactivate immediately instead of using a timer
        # This ensures test cases can verify state changes right away
        deactivate_assistant()
        return response
        
    if re.search(r"\bwake up\b", clean_text) and not assistant_state["active"]:
        response = random.choice(RESPONSES["greeting"])
        add_to_memory("assistant", response)
        
        # For tests, activate immediately instead of using a timer
        activate_assistant()
        return response
    
    # Try to match a command pattern
    for pattern, command_name in COMMAND_PATTERNS:
        if re.search(pattern, clean_text):
            # Found a matching command
            response = execute_command(command_name, clean_text)
            add_to_memory("assistant", response)
            return response
    
    # If no pattern matches, use a fallback response
    response = random.choice(RESPONSES["uncertain"])
    add_to_memory("assistant", response)
    return response

def execute_command(command_name: str, full_text: str) -> str:
    """Execute a named command based on the user's input.
    
    Args:
        command_name: The function name to call
        full_text: The user's full input text
        
    Returns:
        The assistant's response
    """
    # Execute the appropriate function based on command name
    if command_name == "get_time":
        return get_time()
    elif command_name == "get_date":
        return get_date()
    elif command_name == "get_weather":
        return get_weather()
    elif command_name == "get_status":
        return get_status()
    elif command_name == "get_status_personal":
        return get_status_personal()
    elif command_name == "tell_joke":
        return tell_joke()
    elif command_name == "go_to_sleep":
        return random.choice(RESPONSES["farewell"])
    elif command_name == "wake_up":
        return random.choice(RESPONSES["greeting"])
    elif command_name == "identify_self":
        return identify_self()
    elif command_name == "list_abilities":
        return list_abilities()
    elif command_name == "greeting":
        return random.choice(RESPONSES["greeting"])
    elif command_name == "farewell":
        return random.choice(RESPONSES["farewell"])
    elif command_name == "acknowledge_thanks":
        return "You're welcome."
    else:
        # Unknown command
        return random.choice(RESPONSES["uncertain"])

# Command implementation functions
def get_time() -> str:
    """Get the current time as a human-readable string."""
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    return random.choice(RESPONSES["time"]).format(time=current_time)

def get_date() -> str:
    """Get the current date as a human-readable string."""
    current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
    return random.choice(RESPONSES["date"]).format(date=current_date)

def get_weather() -> str:
    """Get the current weather (placeholder for now)."""
    return random.choice(RESPONSES["weather_placeholder"])

def get_status() -> str:
    """Get the system status."""
    return random.choice(RESPONSES["status"])

def get_status_personal() -> str:
    """Respond to 'how are you' type questions."""
    return f"I'm functioning normally, thank you for asking, {USER_NAME}."

def tell_joke() -> str:
    """Tell a random joke."""
    return random.choice(RESPONSES["joke"])

def identify_self() -> str:
    """Identify the assistant."""
    return f"I am {ASSISTANT_NAME}, your personal voice assistant. How can I help you today?"

def list_abilities() -> str:
    """List what the assistant can do."""
    capabilities = [
        "I can tell you the time and date",
        "I can respond to basic queries",
        "I can tell jokes",
        "I can process voice commands for your computer",
        "I can have simple conversations"
    ]
    
    return f"Here's what I can do: {'. '.join(capabilities)}."

def update_status(status: str) -> None:
    """Update the status display in the terminal.
    
    Args:
        status: The status message to display
    """
    global last_status
    
    # Only update if status changed
    if status == last_status:
        return
        
    last_status = status
    
    # Get terminal size
    terminal_width = shutil.get_terminal_size().columns
    
    # Create full status line with padding
    full_status = f"{STATUS_PREFIX}{status}"
    padding = " " * (terminal_width - len(full_status))
    padded_status = full_status + padding
    
    # Move cursor to status line, print status, and return cursor
    sys.stdout.write(f"\033[s")  # Save cursor position
    sys.stdout.write(f"\033[{STATUS_LINE};0H")  # Move to status line
    sys.stdout.write(f"\033[K")  # Clear line
    sys.stdout.write(f"\033[1;32m{padded_status}\033[0m")  # Print green status
    sys.stdout.write(f"\033[u")  # Restore cursor position
    sys.stdout.flush()

def process_voice_command(transcription: str) -> None:
    """Process a voice command from the main voice control system.
    
    Args:
        transcription: The transcribed user speech
    """
    update_status(f"Processing: '{transcription}'")
    
    # Only process in active conversational mode
    if not assistant_state["active"] or not assistant_state["conversational_mode"]:
        # Check if this is a wake command
        if transcription.lower().startswith(WAKE_WORD) or "jarvis" in transcription.lower():
            # Play sound to indicate we heard the wake word
            try:
                subprocess.run(["afplay", "/System/Library/Sounds/Pop.aiff"], check=False)
            except Exception:
                pass
                
            # Activate assistant
            activate_assistant()
            
            # Remove wake word before processing
            clean_text = re.sub(r'^hey\s+|jarvis\s+', '', transcription.lower()).strip()
            if clean_text:  # If there's remaining text
                update_status(f"Processing command: '{clean_text}'")
                # Process the command
                response = handle_user_input(clean_text)
                update_status(f"Speaking: '{response}'")
                tts.speak(response, voice=assistant_state["voice"], block=True)
                update_status("Listening for next command")
        return
    
    # Process transcription and respond with clear audio feedback
    update_status(f"Processing command: '{transcription}'")
    
    # First play an acknowledgment sound so user knows we heard them
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Pop.aiff"], check=False)
    except Exception:
        pass
    
    # Generate response
    response = handle_user_input(transcription)
    
    # Speak response and block until complete
    update_status(f"Speaking: '{response}'")
    tts.speak(response, voice=assistant_state["voice"], block=True)
    update_status("Listening for next command")
    
    # Update last interaction time
    assistant_state["last_interaction_time"] = time.time()

def should_timeout() -> bool:
    """Check if the assistant should timeout due to inactivity.
    
    Returns:
        True if the assistant should timeout, False otherwise
        
    Note:
        Timeout occurs exactly at TIMEOUT_SECONDS after last interaction.
        This function is designed to be testable with mock time.time() patches.
    """
    if not assistant_state["active"]:
        return False
    
    # Defined at function level for better testability
    TIMEOUT_SECONDS = 60  # 1 minute without interaction
    
    # Get current time and last interaction time
    current_time = time.time()
    last_time = assistant_state["last_interaction_time"]
    
    # Calculate time difference
    time_since_last = current_time - last_time
    
    # Log timeout status for debugging (only at specific intervals)
    if 30 <= time_since_last < 31:  # Only log once when we cross 30 seconds
        update_status(f"Timeout in {TIMEOUT_SECONDS - time_since_last:.1f} seconds if no interaction")
    elif 45 <= time_since_last < 46:  # Only log once when we cross 45 seconds
        update_status(f"Timeout imminent in {TIMEOUT_SECONDS - time_since_last:.1f} seconds")
    
    # Return true exactly when time elapsed exceeds timeout threshold
    return time_since_last >= TIMEOUT_SECONDS

def check_timeout_thread() -> None:
    """Thread to check for assistant timeouts."""
    while True:
        try:
            if should_timeout():
                update_status("Timing out due to inactivity")
                deactivate_assistant()
            
            # Check more frequently for more responsive timeout messages
            time.sleep(1)
        except Exception as e:
            # Don't let exceptions in the timeout thread crash the program
            update_status(f"Error in timeout thread: {e}")
            time.sleep(5)  # Longer sleep on error

def init_assistant() -> None:
    """Initialize the assistant module."""
    # Clear terminal and set up status line
    sys.stdout.write("\033[2J")  # Clear screen
    sys.stdout.write("\033[H")   # Move cursor to home position
    
    # Print header for status display
    terminal_width = shutil.get_terminal_size().columns
    header = f"=== {ASSISTANT_NAME} VOICE ASSISTANT ==="
    padding = "=" * ((terminal_width - len(header)) // 2)
    sys.stdout.write(f"\033[1;34m{padding}{header}{padding}\033[0m\n\n")
    sys.stdout.flush()
    
    # Show initial status
    update_status("Initializing")
    
    # Start timeout checking thread
    timeout_thread = threading.Thread(target=check_timeout_thread, daemon=True)
    timeout_thread.start()
    
    update_status(f"Assistant initialized and ready - say 'Hey {ASSISTANT_NAME}' to begin")

def test_assistant() -> None:
    """Run comprehensive tests for the assistant functionality.
    
    This implements a TDD approach to verify all functionality works.
    """
    # Init screen for status display
    sys.stdout.write("\033[2J")  # Clear screen
    sys.stdout.write("\033[H")   # Move cursor to home position
    sys.stdout.write("\033[1;33m=== JARVIS ASSISTANT TEST SUITE ===\033[0m\n\n")
    
    def run_test(name, func):
        """Run a single test and report results"""
        update_status(f"Running test: {name}")
        try:
            func()
            sys.stdout.write(f"\033[1;32m✓ {name}\033[0m\n")
        except Exception as e:
            sys.stdout.write(f"\033[1;31m✗ {name}: {e}\033[0m\n")
            import traceback
            sys.stdout.write(f"{traceback.format_exc()}\n")
    
    # Test 1: Status display
    def test_status_display():
        for status in ["Test status 1", "Test status 2", "A longer test status that should be displayed properly"]:
            update_status(status)
            time.sleep(0.5)
        assert last_status == "A longer test status that should be displayed properly"
    
    # Test 2: Activation sequence
    def test_activation():
        # Reset assistant state
        assistant_state["active"] = False
        assistant_state["conversational_mode"] = False
        
        # Activate and check state
        activate_assistant()
        assert assistant_state["active"] == True
        assert assistant_state["conversational_mode"] == True
    
    # Test 3: Command processing
    def test_command_processing():
        test_commands = [
            "What time is it?",
            "Tell me a joke",
            "What can you do?",
            "How are you today?"
        ]
        
        for cmd in test_commands:
            update_status(f"Testing command: '{cmd}'")
            response = handle_user_input(cmd)
            update_status(f"Response: {response}")
            # Speak the response but don't block test execution
            tts.speak(response, voice=assistant_state["voice"], block=False)
            time.sleep(0.5)
            # Verify response isn't empty
            assert response and len(response) > 0
    
    # Test 4: Deactivation
    def test_deactivation():
        deactivate_assistant()
        assert assistant_state["active"] == False
        assert assistant_state["conversational_mode"] == False
    
    # Test 5: Timeout mechanism
    def test_timeout():
        # Activate, then force timeout
        activate_assistant()
        original_time = assistant_state["last_interaction_time"]
        # Directly modify last interaction time to simulate inactivity
        assistant_state["last_interaction_time"] = time.time() - 61
        assert should_timeout() == True
        # Reset for other tests
        assistant_state["last_interaction_time"] = original_time
    
    # Run all tests
    run_test("Status Display", test_status_display)
    run_test("Activation", test_activation)
    run_test("Command Processing", test_command_processing)  
    run_test("Deactivation", test_deactivation)
    run_test("Timeout Mechanism", test_timeout)
    
    update_status("All tests complete")
    sys.stdout.write("\n\033[1;33m=== TEST SUITE COMPLETE ===\033[0m\n")

if __name__ == "__main__":
    # Test the assistant if run directly
    test_assistant()