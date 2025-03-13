#!/usr/bin/env python3
"""
OpenAI SDK-based greeting generator for dynamic startup messages.
Uses the OpenAI SDK to connect to OpenWebUI for generating witty greetings.
"""

import os
import sys
import logging
import random
from typing import Optional
from openai import OpenAI

# Add parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.config.config import config

# Configure logging
logger = logging.getLogger("openai-greeting")

# Default witty Jarvis startup messages for fallback
DEFAULT_GREETINGS = [
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
    Generate a witty Jarvis-style greeting using the OpenAI API.
    
    Returns:
        A dynamically generated greeting, or a fallback one if generation fails
    """
    # Get server details from environment or config
    server_url = os.getenv("LLM_SERVER_URL", config.get("LLM_SERVER_URL", "http://192.168.191.55:7860"))
    model_name = os.getenv("LLM_MODEL_NAME", config.get("LLM_MODEL_NAME", "unsloth/QwQ-32B-GGUF:Q4_K_M"))
    api_key = os.getenv("OPENWEBUI_API_KEY", "")
    
    # Prepare a shorter prompt for a witty Jarvis-style greeting
    prompt = "Create a short, witty, sarcastic Jarvis greeting (10-15 words max)."
    
    # Try to generate a greeting
    try:
        # Initialize the OpenAI client with custom base URL and API key 
        # For Ollama models in OpenWebUI, we need to use the openai compatible API path
        client = OpenAI(
            base_url=f"{server_url}/v1",  # OpenAI compatible endpoint in OpenWebUI
            api_key=api_key or "sk-no-key-needed"  # Provide a fallback key if none is set
        )
        
        # Extract just the model name without the host/organization prefix
        model_short_name = model_name.split("/")[-1].split(":")[0]
        
        # Use OpenAI's chat completion format, which is more widely supported
        response = client.chat.completions.create(
            model=model_short_name,
            messages=[
                {"role": "system", "content": "You are Jarvis, a witty and sarcastic AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=30,
            timeout=0.8  # Very short timeout to avoid delaying startup
        )
        
        # Get the generated text from OpenAI's chat completion response format
        greeting = response.choices[0].message.content.strip()
        logger.info(f"Generated greeting: {greeting}")
        
        # Clean up the response if needed (remove quotes, etc.)
        greeting = greeting.strip('"').strip()
        return greeting
        
    except Exception as e:
        logger.warning(f"Failed to generate greeting: {e}. Using default.")
        return random.choice(DEFAULT_GREETINGS)

if __name__ == "__main__":
    # Set up logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Test the greeting generator
    greeting = generate_greeting()
    print(f"Generated greeting: {greeting}")