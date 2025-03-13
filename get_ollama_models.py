#!/usr/bin/env python3
"""
Script to get the list of available models from the Ollama API via OpenWebUI.
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()

    # Get server details from environment
    server_url = os.getenv("LLM_SERVER_URL", "http://192.168.191.55:7860")
    api_key = os.getenv("OPENWEBUI_API_KEY", "")

    # Print configuration
    print(f"Server URL: {server_url}")
    print(f"API Key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")

    # Try different endpoints to get models
    endpoints_to_try = [
        "/ollama/api/tags",  # Ollama API for listing models
        "/api/models",       # OpenWebUI API for models
        "/v1/models",        # OpenAI-compatible endpoint
        "/api/ollama/tags",  # Another possible Ollama endpoint
    ]

    for endpoint in endpoints_to_try:
        url = f"{server_url}{endpoint}"
        print(f"\nTrying endpoint: {url}")

        try:
            # Set up headers with authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}" if api_key else ""
            }

            # Make request
            response = requests.get(url, headers=headers, timeout=5)

            # Print status
            print(f"Status: {response.status_code}")

            # If successful, print models
            if response.status_code == 200:
                response_data = response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")

                # Try to extract model names based on different formats
                if "models" in response_data:
                    print("\nAvailable models:")
                    for model in response_data["models"]:
                        print(f"- {model.get('name', model)}")
                elif "data" in response_data:
                    print("\nAvailable models:")
                    for model in response_data["data"]:
                        print(f"- {model.get('id', model.get('name', model))}")
                else:
                    print("\nRaw response data:")
                    print(json.dumps(response_data, indent=2))
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error trying endpoint {endpoint}: {e}")

if __name__ == "__main__":
    main()
