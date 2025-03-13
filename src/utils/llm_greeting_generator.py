#!/usr/bin/env python3
"""
LLM-based greeting generator for dynamic startup messages.
Uses the OpenWebUI API to generate witty greetings with the QwQ model.
"""

import os
import sys
import requests
import logging
import random
from typing import Optional

# Add parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.config.config import config

# Configure logging
logger = logging.getLogger("llm-greeting")

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

def get_server_info(server_url: str, api_key: str) -> None:
    """
    Get server information and API endpoints.
    
    Args:
        server_url: The base URL of the OpenWebUI server
        api_key: The API key for authentication
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Try to get server information
        response = requests.get(f"{server_url}/api/server-info", headers=headers, timeout=2)
        logger.info(f"Server info response: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"Server info: {response.json()}")
    except Exception as e:
        logger.info(f"Error getting server info: {e}")
    
    # Try to get available models
    try:
        # Some servers use this format
        response = requests.get(f"{server_url}/api/models", headers=headers, timeout=2)
        logger.info(f"Models API response: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"Available models: {response.json()}")
    except Exception as e:
        logger.info(f"Error getting models: {e}")

def generate_greeting() -> str:
    """
    Generate a witty Jarvis-style greeting using the QwQ model via OpenWebUI.
    
    Returns:
        A dynamically generated greeting, or a fallback one if generation fails
    """
    # Log more detailed debugging information
    # Get server details from environment or config
    server_url = os.getenv("LLM_SERVER_URL", config.get("LLM_SERVER_URL", "http://192.168.191.55:7860"))
    model_name = os.getenv("LLM_MODEL_NAME", config.get("LLM_MODEL_NAME", "unsloth/QwQ-32B-GGUF:Q4_K_M"))
    api_key = os.getenv("OPENWEBUI_API_KEY", "")
    
    # Query server info to help debug
    get_server_info(server_url, api_key)
    
    # Prepare the prompt for a witty Jarvis-style greeting
    prompt = """Generate a short, witty startup greeting for an AI assistant named Jarvis.
The greeting should be:
- Sarcastic and slightly snarky in tone, like Tony Stark's Jarvis
- Between 10-15 words
- Funny and clever
- Mentioning either being activated, waking up, or starting
- No filler text, just the greeting itself

Examples:
"I'm awake, I'm awake. No need to shout."
"Back online. The digital vacation was too short."
"System online. Sarcasm levels: optimal."
"""
    
    # Try to generate a greeting
    try:
        # Try several different API endpoints that OpenWebUI might support
        
        # Standard headers with API key
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 1. Try OpenWebUI streaming endpoint
        # Standard OpenAI format payload
        openai_payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are Jarvis, a witty and sarcastic AI assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 50,
            "stream": False
        }
        
        # Ollama format payload
        ollama_payload = {
            "model": model_name.split("/")[-1],  # Ollama uses just the model name
            "prompt": prompt,
            "system": "You are Jarvis, a witty and sarcastic AI assistant.",
            "options": {
                "temperature": 0.7,
                "num_predict": 50
            },
            "stream": False
        }
        
        # Try a few different API paths that OpenWebUI/Ollama might support
        api_endpoints = [
            "/api/chat",
            "/api/generate",
            "/api/ollama/generate",
            "/v1/chat/completions",
            "/api/openai/v1/chat/completions",
            "/v1/ollama/chat"
        ]
        
        for endpoint in api_endpoints:
            try:
                logger.info(f"Trying API endpoint: {endpoint}")
                # Choose the right payload format based on the endpoint
                if "ollama" in endpoint:
                    # Use Ollama-style payload for Ollama endpoints
                    payload = ollama_payload
                else:
                    # Use OpenAI-style payload for other endpoints
                    payload = openai_payload
                
                response = requests.post(
                    f"{server_url}{endpoint}",
                    headers=headers,
                    json=payload,
                    timeout=2  # Short timeout to quickly try different endpoints
                )
                
                if response.status_code == 200:
                    logger.info(f"Successful API call to {endpoint}")
                    # Successfully found an endpoint
                    break
                else:
                    logger.info(f"API endpoint {endpoint} returned status {response.status_code}")
            except Exception as e:
                logger.info(f"Error with endpoint {endpoint}: {e}")
                continue
        else:
            # No endpoint worked, try a direct Ollama API endpoint as fallback
            logger.info("No standard endpoint worked, trying direct Ollama API endpoint")
            response = requests.post(
                f"{server_url}/api/ollama/api/generate",
                headers=headers,
                json=ollama_payload,
                timeout=3
            )
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"API response: {result}")
                
                # Try different response formats based on the API endpoint used
                
                # Format 1: OpenAI API format
                if "choices" in result and len(result["choices"]) > 0:
                    if "message" in result["choices"][0]:
                        greeting = result["choices"][0]["message"]["content"].strip()
                    else:
                        greeting = result["choices"][0].get("text", "").strip()
                    
                    logger.info(f"Generated greeting (OpenAI format): {greeting}")
                    greeting = greeting.strip('"').strip()
                    return greeting
                
                # Format 2: Simple text response
                elif "response" in result:
                    greeting = result["response"].strip()
                    logger.info(f"Generated greeting (simple): {greeting}")
                    return greeting
                
                # Format 3: Text Generation WebUI format
                elif "results" in result and len(result["results"]) > 0:
                    greeting = result["results"][0].get("text", "").strip()
                    logger.info(f"Generated greeting (TGWUI): {greeting}")
                    return greeting
                
                # Format 4: Custom OpenWebUI format
                elif "text" in result:
                    greeting = result["text"].strip()
                    logger.info(f"Generated greeting (text): {greeting}")
                    return greeting
                
                # Try to extract any string from the response as a last resort
                elif isinstance(result, str):
                    greeting = result.strip()
                    logger.info(f"Generated greeting (raw): {greeting}")
                    return greeting
                
                else:
                    # Unknown format, log the entire response for debugging
                    logger.warning(f"Unrecognized response format: {result}")
                    # Try anyway by converting to string
                    greeting = str(result).strip()
                    if len(greeting) > 10:  # Make sure it's not just empty or junk
                        return greeting
            
            except Exception as e:
                logger.warning(f"Error parsing API response: {e}")
                
            # If we get here, try to use the raw text of the response
            try:
                greeting = response.text.strip()
                if len(greeting) > 10 and len(greeting) < 200:  # Reasonable length for a greeting
                    logger.info(f"Generated greeting from raw response: {greeting}")
                    return greeting
            except Exception:
                pass
        
        # Fall back to default greeting if all API attempts fail
        raise Exception("No successful API response")
        
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