#!/usr/bin/env python3
"""
Cloud Code API Client Example

This example demonstrates how to create a simple assistant that:
1. Listens for transcriptions via WebSocket
2. Processes the transcriptions
3. Responds via speech synthesis
"""

import asyncio
import json
import logging
import time
import websockets
import requests
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cloud-code-client')

class CloudCodeClient:
    """Simple client for the Cloud Code API."""

    def __init__(self, host='127.0.0.1', port=8000):
        """Initialize the client.

        Args:
            host: API host
            port: API port
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws/transcription"
        self.session_id = f"python-client-{int(time.time())}"
        self.connected = False

    async def connect(self):
        """Connect to the API."""
        logger.info(f"Connecting to API at {self.base_url}")

        # Check if the API is running
        try:
            response = requests.get(f"{self.base_url}/status")
            if response.status_code == 200:
                status = response.json()
                logger.info(f"API status: {status}")
                self.connected = True
            else:
                logger.error(f"Failed to connect to API: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to API: {e}")
            return False

        # Speak a welcome message
        try:
            await self.speak("Cloud Code client connected. I'm listening for your voice commands.")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

        return True

    async def listen_for_transcriptions(self):
        """Listen for transcriptions from the WebSocket."""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                logger.info("Connected to WebSocket")

                # Send a test message
                await websocket.send("Hello from Python client")

                # Listen for transcriptions
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        await self.process_transcription(data)
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("WebSocket connection closed")
                        break
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")

    async def process_transcription(self, data):
        """Process a transcription from the WebSocket.

        Args:
            data: Transcription data
        """
        text = data.get('text', '')
        is_command = data.get('is_command', False)
        confidence = data.get('confidence', 0.0)

        # Format and log the transcription
        timestamp = time.strftime('%H:%M:%S')
        mode = "COMMAND" if is_command else "DICTATION"
        confidence_str = f"{confidence * 100:.1f}%"

        logger.info(f"[{timestamp}] [{mode}] ({confidence_str}) {text}")

        # Process based on the content (very simple example)
        if "hello" in text.lower() or "hi" in text.lower():
            await self.speak("Hello there! How can I help you today?")

        if "goodbye" in text.lower() or "bye" in text.lower():
            await self.speak("Goodbye! Have a great day!")

        if "weather" in text.lower():
            await self.speak("I don't have access to weather data, but I can tell you that it's always sunny in the cloud!")

        if "thank you" in text.lower() or "thanks" in text.lower():
            await self.speak("You're welcome! I'm happy to help.")

    async def speak(self, text):
        """Synthesize speech.

        Args:
            text: Text to synthesize
        """
        logger.info(f"Speaking: {text}")

        try:
            response = requests.post(
                f"{self.base_url}/speak",
                params={"text": text}
            )

            if response.status_code != 200:
                logger.error(f"Failed to speak: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending speak request: {e}")

    async def process_prompt(self, prompt):
        """Process a prompt using the Cloud Code API.

        Args:
            prompt: Prompt to process
        """
        logger.info(f"Processing prompt: {prompt}")

        try:
            response = requests.post(
                f"{self.base_url}/cloud-code",
                json={
                    "prompt": prompt,
                    "session_id": self.session_id
                }
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Response: {result.get('response', '')}")
                logger.info(f"Conversation ID: {result.get('conversation_id', '')}")
                return result
            else:
                logger.error(f"Failed to process prompt: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error sending prompt: {e}")
            return None

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Cloud Code API Client")
    parser.add_argument("--host", default="127.0.0.1", help="API host")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    args = parser.parse_args()

    client = CloudCodeClient(host=args.host, port=args.port)

    # Connect to the API
    if not await client.connect():
        logger.error("Failed to connect to API")
        return

    logger.info("Starting transcription listener")

    # Main loop - listen for transcriptions
    try:
        await client.listen_for_transcriptions()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")

    logger.info("Client stopped")

if __name__ == "__main__":
    asyncio.run(main())
