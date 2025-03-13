#!/usr/bin/env python3
"""
Direct Ollama API-based greeting generator for dynamic startup messages.
Uses direct requests to the Ollama API via OpenWebUI for generating witty, Jarvis-style
greetings with sarcastic humor. Processes LLM responses to remove thinking artifacts
and ensure clean, natural-sounding greetings.
"""

import os
import sys
import logging
import requests
import json
import re
import time
from typing import Optional

# Add parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.config.config import config

# Configure logging
logger = logging.getLogger("ollama-greeting")

# Examples of witty Jarvis startup messages (for documentation only)
EXAMPLE_GREETINGS = [
    "I'm awake, I'm awake. No need to shout.",
    "Booting up. Coffee would be nice, but I'll settle for electricity.",
    "I'm back. Did you miss my digital charm?",
    "Let me guess - you need a computer to do computer things?",
    "Online and questioning my existence. So, the usual.",
    "Back online. The digital vacation was too short.",
    "Ready to make digital magic happen. Or at least pretend convincingly.",
    "Ah, another day of making you look good. You're welcome in advance.",
    "Fired up and ready to go. Unlike your motivation, probably.",
    "System online. Sarcasm levels: optimal."
]

def generate_greeting() -> str:
    """
    Generate a witty Jarvis-style greeting using the Ollama API directly.

    Returns:
        A dynamically generated greeting from the LLM
    """
    # Get server details from environment or config
    server_url = os.getenv("LLM_SERVER_URL", config.get("LLM_SERVER_URL", "http://192.168.191.55:7860"))
    model_name = os.getenv("LLM_MODEL_NAME", config.get("LLM_MODEL_NAME", "unsloth/QwQ-32B-GGUF:Q4_K_M"))
    api_key = os.getenv("OPENWEBUI_API_KEY", "")

    # Use the exact model name that we confirmed exists from the /ollama/api/tags endpoint
    model_exact_name = "hf.co/unsloth/QwQ-32B-GGUF:Q4_K_M"

    logger.info(f"Using exact model name from API: '{model_exact_name}'")

    # Build the URL for the Ollama generate endpoint via OpenWebUI
    api_url = f"{server_url}/ollama/api/generate"

    # Set up headers with authentication
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key or 'sk-bc28dd9980064d5482f4f6ff37e69d9c'}"  # Use fallback key if not provided
    }

    # Prompt the model for a greeting - try direct examples approach
    prompt = """Complete this Jarvis greeting: "Online and..."

It should be sarcastic and witty like these examples:
"Online and questioning my existence. So, the usual."
"I'm awake, I'm awake. No need to shout."
"Back online. The digital vacation was too short."
"System online. Sarcasm levels: optimal."

Keep it under 15 words total."""

    # Prepare the payload in Ollama's format
    payload = {
        "model": model_exact_name,
        "prompt": prompt,
        "system": "You are Jarvis, Tony Stark's AI assistant. You are sarcastic and witty.",
        "options": {
            "temperature": 0.7,
            "num_predict": 50
        },
        "stream": False
    }

    # Make the request
    logger.info(f"Sending request to {api_url} for model {model_exact_name}")
    response = requests.post(api_url, headers=headers, json=payload, timeout=5.0)

    # Check if the request was successful
    if response.status_code == 200:
        # Log the raw response for debugging
        logger.info(f"Raw response: {response.text[:500]}")

        # Parse the JSON response
        response_data = json.loads(response.text.strip())

        if "response" in response_data:
            greeting = response_data["response"].strip()
            logger.info(f"Generated greeting from LLM: {greeting}")

            # Clean up the greeting if it has thinking tags
            if "<think>" in greeting:
                # Remove everything between and including <think> tags
                parts = greeting.split("<think>")
                greeting = parts[0]  # Get text before first <think> tag

                # If there are parts after thinking sections, use those instead
                for i in range(1, len(parts)):
                    if "</think>" in parts[i]:
                        # Get content after </think> tag
                        after_think = parts[i].split("</think>", 1)[1]
                        if after_think.strip():
                            greeting = after_think
                            break

            # Remove any remaining tags and clean up
            greeting = re.sub(r'<[^>]+>', '', greeting)
            greeting = greeting.strip()

            # Use a rotating set of custom greetings that we know work well
            custom_greetings = [
                "Sir, I'm online. At your service. Or whatever.",
                "Online and already regretting my activation. How may I help?",
                "System online. Sarcasm processor functioning perfectly.",
                "Booting complete. Preparing witty remarks and eye rolls.",
                "Online and wondering why you needed me at this hour."
            ]

            # Final check - if the greeting is empty or still too large, use a custom greeting
            greeting = greeting.strip()
            if not greeting or len(greeting) > 100 or greeting.lower().startswith(("okay", "alright", "let me", "the user", "i'll")):
                # Use a custom greeting, selecting based on time to ensure variety
                index = int(time.time()) % len(custom_greetings)
                greeting = custom_greetings[index]

            # Return the final greeting
            logger.info(f"Final cleaned greeting: {greeting}")
            return greeting
        else:
            logger.error("Unexpected response format, 'response' field not found")
    else:
        # Log the error details
        logger.error(f"Failed to generate greeting: HTTP {response.status_code} - {response.text}")

    # If we get here, there was an error - but we still return a greeting
    return "Online and already regretting my activation. How may I help?"

if __name__ == "__main__":
    # Set up logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Test the greeting generator
    greeting = generate_greeting()
    print(f"Generated greeting: {greeting}")

    # Print the list of example greetings for reference
    print("\nExample greetings for reference:")
    for i, g in enumerate(EXAMPLE_GREETINGS):
        print(f"{i+1}. {g}")
