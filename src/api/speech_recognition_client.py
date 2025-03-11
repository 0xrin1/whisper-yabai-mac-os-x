#!/usr/bin/env python3
"""
Speech Recognition API Client

Client for the standalone Speech Recognition API service.
"""

import asyncio
import base64
import json
import logging
import os
import time
from typing import Dict, List, Optional, Union, Callable

import aiohttp
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("speech-recognition-client")

class SpeechRecognitionClient:
    """Client for the Speech Recognition API."""

    def __init__(self, api_url: str = None):
        """Initialize the client.

        Args:
            api_url: The URL of the Speech Recognition API
        """
        self.api_url = api_url or os.getenv("SPEECH_RECOGNITION_API_URL", "http://localhost:8000")
        self.ws_url = self.api_url.replace("http://", "ws://").replace("https://", "wss://")

        # WebSocket connection
        self.websocket = None
        self.ws_connected = False
        self.ws_task = None

        # Transcription callbacks
        self.transcription_callbacks = []

    async def check_connection(self) -> bool:
        """Check if the API is available.

        Returns:
            True if the API is available, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/") as response:
                    if response.status == 200:
                        logger.info("Speech Recognition API is available")
                        return True
                    else:
                        logger.error(f"Speech Recognition API returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error connecting to Speech Recognition API: {e}")
            return False

    async def list_models(self) -> Dict:
        """List available models.

        Returns:
            Dict with available models information
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/models") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Error listing models: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return {}

    async def transcribe(
        self,
        audio_file_path: str,
        model_size: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Dict:
        """Transcribe an audio file.

        Args:
            audio_file_path: Path to the audio file
            model_size: Model size to use
            language: Language of the audio
            prompt: Initial prompt for the model

        Returns:
            Transcription result
        """
        try:
            # Read the audio file
            with open(audio_file_path, "rb") as f:
                audio_data = f.read()

            # Encode as base64
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            # Prepare the request
            data = {
                "audio_data": audio_base64,
            }

            if model_size:
                data["model_size"] = model_size

            if language:
                data["language"] = language

            if prompt:
                data["prompt"] = prompt

            # Send the request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/transcribe",
                    json=data,
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Transcription successful: {result.get('text', '')}")
                        return result
                    else:
                        error = await response.text()
                        logger.error(f"Error transcribing: {response.status} - {error}")
                        return {"error": error}
        except Exception as e:
            logger.error(f"Error transcribing: {e}")
            return {"error": str(e)}

    async def transcribe_audio_data(
        self,
        audio_data: bytes,
        model_size: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Dict:
        """Transcribe raw audio data.

        Args:
            audio_data: Raw audio data bytes
            model_size: Model size to use
            language: Language of the audio
            prompt: Initial prompt for the model

        Returns:
            Transcription result
        """
        try:
            # Encode as base64
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            # Prepare the request
            data = {
                "audio_data": audio_base64,
            }

            if model_size:
                data["model_size"] = model_size

            if language:
                data["language"] = language

            if prompt:
                data["prompt"] = prompt

            # Send the request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/transcribe",
                    json=data,
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Transcription successful: {result.get('text', '')}")
                        return result
                    else:
                        error = await response.text()
                        logger.error(f"Error transcribing: {response.status} - {error}")
                        return {"error": error}
        except Exception as e:
            logger.error(f"Error transcribing: {e}")
            return {"error": str(e)}

    async def upload_and_transcribe(
        self,
        audio_file_path: str,
        model_size: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Dict:
        """Upload and transcribe an audio file.

        Args:
            audio_file_path: Path to the audio file
            model_size: Model size to use
            language: Language of the audio
            prompt: Initial prompt for the model

        Returns:
            Transcription result
        """
        try:
            # Prepare the request
            data = aiohttp.FormData()
            data.add_field("file", open(audio_file_path, "rb"))

            if model_size:
                data.add_field("model_size", model_size)

            if language:
                data.add_field("language", language)

            if prompt:
                data.add_field("prompt", prompt)

            # Send the request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/transcribe_file",
                    data=data,
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Transcription successful: {result.get('text', '')}")
                        return result
                    else:
                        error = await response.text()
                        logger.error(f"Error transcribing: {response.status} - {error}")
                        return {"error": error}
        except Exception as e:
            logger.error(f"Error transcribing: {e}")
            return {"error": str(e)}

    def register_transcription_callback(self, callback: Callable[[Dict], None]):
        """Register a callback for transcription events.

        Args:
            callback: Function to call with the transcription result
        """
        if callback not in self.transcription_callbacks:
            self.transcription_callbacks.append(callback)
            logger.debug(f"Registered transcription callback: {callback}")

    def unregister_transcription_callback(self, callback: Callable[[Dict], None]):
        """Unregister a callback for transcription events.

        Args:
            callback: Previously registered callback function
        """
        if callback in self.transcription_callbacks:
            self.transcription_callbacks.remove(callback)
            logger.debug(f"Unregistered transcription callback: {callback}")

    async def connect_websocket(
        self,
        model_size: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ):
        """Connect to the WebSocket for real-time transcription.

        Args:
            model_size: Model size to use
            language: Language of the audio
            prompt: Initial prompt for the model
        """
        if self.ws_connected:
            logger.warning("WebSocket already connected")
            return

        try:
            logger.info(f"Connecting to WebSocket: {self.ws_url}/ws/transcribe")
            self.websocket = await websockets.connect(f"{self.ws_url}/ws/transcribe")

            # Send configuration
            config = {
                "model_size": model_size,
                "language": language,
                "prompt": prompt,
            }

            await self.websocket.send(json.dumps(config))
            logger.info(f"Sent WebSocket configuration: {config}")

            # Start background task for receiving
            self.ws_connected = True
            self.ws_task = asyncio.create_task(self._websocket_listen())

            logger.info("WebSocket connected")
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {e}")
            self.ws_connected = False

    async def disconnect_websocket(self):
        """Disconnect from the WebSocket."""
        if not self.ws_connected:
            return

        try:
            if self.ws_task:
                self.ws_task.cancel()
                self.ws_task = None

            if self.websocket:
                await self.websocket.close()
                self.websocket = None

            self.ws_connected = False
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting from WebSocket: {e}")

    async def _websocket_listen(self):
        """Listen for messages from the WebSocket."""
        try:
            while self.ws_connected:
                # Send heartbeat every 30 seconds
                heartbeat_task = asyncio.create_task(self._send_heartbeat())

                # Wait for message
                message = await self.websocket.recv()

                # Process message
                try:
                    if message == "heartbeat":
                        continue

                    data = json.loads(message)

                    # Call callbacks
                    for callback in self.transcription_callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"Error in transcription callback: {e}")
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from WebSocket: {message}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
        except asyncio.CancelledError:
            logger.info("WebSocket listen task cancelled")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.ws_connected = False
        except Exception as e:
            logger.error(f"Error in WebSocket listen task: {e}")
            self.ws_connected = False

    async def _send_heartbeat(self):
        """Send heartbeat message to keep the connection alive."""
        try:
            await asyncio.sleep(30)
            if self.ws_connected and self.websocket:
                await self.websocket.send("heartbeat")
                logger.debug("Sent heartbeat")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")

    async def send_audio_for_transcription(self, audio_data: bytes):
        """Send audio data for transcription via WebSocket.

        Args:
            audio_data: Raw audio data bytes
        """
        if not self.ws_connected or not self.websocket:
            logger.error("WebSocket not connected")
            return

        try:
            # Encode as base64
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            # Send the audio data
            message = {
                "audio_data": audio_base64,
            }

            await self.websocket.send(json.dumps(message))
            logger.debug("Sent audio data via WebSocket")
        except Exception as e:
            logger.error(f"Error sending audio data via WebSocket: {e}")


async def main():
    """Example usage of the client."""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Speech Recognition API Client Example")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--file", help="Audio file to transcribe")
    parser.add_argument("--model", default="large-v3", help="Model size")
    parser.add_argument("--language", help="Language code")
    parser.add_argument("--prompt", help="Initial prompt")
    parser.add_argument("--ws", action="store_true", help="Use WebSocket")
    args = parser.parse_args()

    # Create the client
    client = SpeechRecognitionClient(api_url=args.api_url)

    # Check connection
    if not await client.check_connection():
        logger.error("Speech Recognition API not available")
        return

    # List models
    models = await client.list_models()
    logger.info(f"Available models: {models}")

    # Transcribe a file if provided
    if args.file:
        if args.ws:
            # Register callback
            def transcription_callback(result):
                logger.info(f"WebSocket transcription: {result.get('text', '')}")
                logger.info(f"Confidence: {result.get('confidence', 0)}")
                logger.info(f"Processing time: {result.get('processing_time', 0):.2f} seconds")

            client.register_transcription_callback(transcription_callback)

            # Connect to WebSocket
            await client.connect_websocket(
                model_size=args.model,
                language=args.language,
                prompt=args.prompt,
            )

            # Read the file
            with open(args.file, "rb") as f:
                audio_data = f.read()

            # Send audio data
            await client.send_audio_for_transcription(audio_data)

            # Wait a bit for the response
            await asyncio.sleep(10)

            # Disconnect
            await client.disconnect_websocket()
        else:
            # Use REST API
            result = await client.upload_and_transcribe(
                args.file,
                model_size=args.model,
                language=args.language,
                prompt=args.prompt,
            )

            logger.info(f"Transcription: {result.get('text', '')}")
            logger.info(f"Confidence: {result.get('confidence', 0)}")
            logger.info(f"Processing time: {result.get('processing_time', 0):.2f} seconds")

    logger.info("Done")

if __name__ == "__main__":
    asyncio.run(main())
