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
from typing import Dict, List, Optional, Tuple, Any

# Import our own modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import speech_synthesis as tts
from src.toast_notifications import send_notification

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
    
    # Speak a greeting immediately to provide feedback
    tts.speak(
        random.choice(RESPONSES["greeting"]), 
        voice=assistant_state["voice"],
        block=True  # Block until speech is complete
    )
    
    # Play a distinct sound to indicate active listening
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Blow.aiff"], check=False)
    except Exception:
        pass
    
    # Show notification
    send_notification(
        f"{ASSISTANT_NAME} Active",
        "Voice assistant is now listening",
        timeout=3
    )
    
    # Announce that we're listening
    print(f"DEBUG: {ASSISTANT_NAME} activated and listening for commands")

def deactivate_assistant() -> None:
    """Deactivate the assistant with a farewell message."""
    if not assistant_state["active"]:
        return
        
    # Speak a farewell message
    tts.speak(
        random.choice(RESPONSES["farewell"]),
        voice=assistant_state["voice"]
    )
    
    # Update state
    assistant_state["active"] = False
    assistant_state["conversational_mode"] = False
    
    # Show notification
    send_notification(
        f"{ASSISTANT_NAME} Deactivated",
        "Voice assistant is now in standby mode",
        timeout=3
    )

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
        
        # Schedule deactivation after speaking the response
        threading.Timer(2.0, deactivate_assistant).start()
        return response
        
    if re.search(r"\bwake up\b", clean_text) and not assistant_state["active"]:
        response = random.choice(RESPONSES["greeting"])
        add_to_memory("assistant", response)
        
        # Activate after response
        threading.Timer(1.0, activate_assistant).start()
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

def process_voice_command(transcription: str) -> None:
    """Process a voice command from the main voice control system.
    
    Args:
        transcription: The transcribed user speech
    """
    print(f"DEBUG: JARVIS processing: '{transcription}'")
    
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
                print(f"DEBUG: Processing command after wake word: '{clean_text}'")
                # Add small delay to ensure wake sound completes
                time.sleep(0.3)
                # Process the command
                response = handle_user_input(clean_text)
                tts.speak(response, voice=assistant_state["voice"], block=True)
                
                # Play a sound to indicate we're done and listening again
                try:
                    subprocess.run(["afplay", "/System/Library/Sounds/Blow.aiff"], check=False)
                except Exception:
                    pass
        return
    
    # Process transcription and respond with clear audio feedback
    print(f"DEBUG: Processing command in active mode: '{transcription}'")
    
    # First play an acknowledgment sound so user knows we heard them
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Pop.aiff"], check=False)
    except Exception:
        pass
    
    # Small delay to let sound finish
    time.sleep(0.2)
    
    # Generate response
    response = handle_user_input(transcription)
    
    # Speak response and block until complete
    print(f"DEBUG: JARVIS response: '{response}'")
    tts.speak(response, voice=assistant_state["voice"], block=True)
    
    # Play a sound to indicate we're listening again
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Blow.aiff"], check=False)
    except Exception:
        pass
    
    # Update last interaction time
    assistant_state["last_interaction_time"] = time.time()

def should_timeout() -> bool:
    """Check if the assistant should timeout due to inactivity.
    
    Returns:
        True if the assistant should timeout, False otherwise
    """
    if not assistant_state["active"]:
        return False
        
    # Check if it's been too long since the last interaction
    timeout_seconds = 60  # 1 minute without interaction (reduced from 2 minutes)
    time_since_last = time.time() - assistant_state["last_interaction_time"]
    
    # Log timeout status for debugging
    if time_since_last > 30:  # If we're halfway to timeout, log it
        print(f"DEBUG: JARVIS timeout in {timeout_seconds - time_since_last:.1f} seconds if no interaction")
    
    return time_since_last > timeout_seconds

def check_timeout_thread() -> None:
    """Thread to check for assistant timeouts."""
    while True:
        if should_timeout():
            print("Assistant timed out due to inactivity")
            deactivate_assistant()
        
        # Check every 30 seconds
        time.sleep(30)

def init_assistant() -> None:
    """Initialize the assistant module."""
    # Start timeout checking thread
    timeout_thread = threading.Thread(target=check_timeout_thread, daemon=True)
    timeout_thread.start()
    
    print(f"{ASSISTANT_NAME} initialized and ready")

def test_assistant() -> None:
    """Test the assistant functionality."""
    print("Testing assistant module...")
    
    # Activate
    activate_assistant()
    time.sleep(1)
    
    # Test a few commands
    test_commands = [
        "What time is it?",
        "Tell me a joke",
        "What can you do?",
        "How are you today?",
        "Go to sleep"
    ]
    
    for cmd in test_commands:
        print(f"\nTesting: '{cmd}'")
        response = handle_user_input(cmd)
        print(f"Assistant: {response}")
        tts.speak(response, voice=assistant_state["voice"], block=True)
        time.sleep(0.5)
    
    print("\nAssistant test complete")

if __name__ == "__main__":
    # Test the assistant if run directly
    test_assistant()