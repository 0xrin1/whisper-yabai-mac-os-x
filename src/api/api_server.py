"""API server for cloud code integration with speech recognition.

Note on Architecture:
This API server coordinates cloud code integration, while speech recognition is
handled by a separate Speech Recognition API (speech_recognition_api.py), which can
be run on a different machine for better resource allocation.

The Cloud Code API focuses on:
- Providing interfaces for external applications to interact with the voice control system
- Handling WebSocket connections for real-time transcription streaming
- Processing cloud code requests
- Managing speech synthesis requests

The Speech Recognition API handles:
- Running the Whisper model for transcription
- Processing audio data
- Managing model loading and unloading
- Providing RESTful and WebSocket interfaces for speech recognition

This separation allows for distributed processing, better resource allocation,
and more flexibility in deployment.
"""
import asyncio
import json
import logging
import threading
import time
from typing import Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.audio.speech_synthesis import speak
from src.config.config import Config
from src.core.state_manager import StateManager
from src.utils.assistant import AssistantResponse

# Configure logging
logger = logging.getLogger(__name__)

# Models for API requests and responses
class TranscriptionResponse(BaseModel):
    text: str
    confidence: float
    is_command: bool

class CloudCodeRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

class CloudCodeResponse(BaseModel):
    response: str
    conversation_id: str

class APIServer:
    """API server for cloud code integration with speech processing."""

    def __init__(self, state: StateManager, config: Config):
        """Initialize the API server.

        Args:
            state: The shared state manager
            config: The configuration object
        """
        self.state = state
        self.config = config
        self.app = FastAPI(title="Whisper Voice Control API")

        # Set up CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, restrict this to specific domains
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Storage for active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}

        # Storage for transcriptions to be sent over WebSockets
        self.transcription_queue: List[Dict] = []

        # Flag to track if the server is running
        self.running = False

        # Set up API routes
        self.setup_routes()

    def setup_routes(self):
        """Set up API routes."""

        @self.app.get("/")
        async def root():
            return {"message": "Whisper Voice Control API"}

        @self.app.get("/status")
        async def status():
            return {
                "status": "running" if self.running else "stopped",
                "mode": self.state.mode,
                "muted": self.state.muted,
                "recording": self.state.recording,
            }

        @self.app.post("/speak")
        async def synthesize_speech(text: str, voice_id: Optional[str] = None):
            """Synthesize speech from text.

            Args:
                text: The text to synthesize
                voice_id: Optional voice ID to use

            Returns:
                Success message
            """
            try:
                speak(text, voice_id=voice_id)
                return {"message": "Speech synthesized successfully"}
            except Exception as e:
                logger.error(f"Error synthesizing speech: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/cloud-code")
        async def cloud_code(request: CloudCodeRequest):
            """Process a cloud code request.

            Args:
                request: The cloud code request

            Returns:
                The cloud code response
            """
            try:
                # Send the request to the state's prompt queue
                session_id = request.session_id or f"session_{int(time.time())}"

                # Create a mock assistant response
                response = AssistantResponse(
                    text=f"Processing your request: {request.prompt}",
                    commands=[],
                    context={},
                )

                # For now, just echo the request
                return CloudCodeResponse(
                    response=response.text,
                    conversation_id=session_id,
                )
            except Exception as e:
                logger.error(f"Error processing cloud code request: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.websocket("/ws/transcription")
        async def websocket_transcription(websocket: WebSocket):
            """WebSocket endpoint for real-time transcription.

            Args:
                websocket: The WebSocket connection
            """
            await websocket.accept()

            # Generate a unique connection ID
            connection_id = f"conn_{int(time.time())}"
            self.active_connections[connection_id] = websocket

            try:
                # Register for transcriptions
                self.state.register_transcription_callback(self._on_transcription)

                # Keep the connection alive
                while True:
                    # Receive any messages (not used currently)
                    data = await websocket.receive_text()

                    # Echo received data back (for testing)
                    await websocket.send_text(f"Echo: {data}")
            except WebSocketDisconnect:
                # Unregister and remove the connection
                self.state.unregister_transcription_callback(self._on_transcription)
                del self.active_connections[connection_id]

    def _on_transcription(self, text: str, is_command: bool = False, confidence: float = 0.0):
        """Callback for new transcriptions.

        Args:
            text: The transcribed text
            is_command: Whether the transcription is a command
            confidence: The confidence level of the transcription
        """
        # Add to queue to be sent over WebSockets
        transcription = {
            "text": text,
            "is_command": is_command,
            "confidence": confidence,
            "timestamp": time.time()
        }

        self.transcription_queue.append(transcription)

        # Process the queue asynchronously
        threading.Thread(target=self._process_transcription_queue, daemon=True).start()

    def _process_transcription_queue(self):
        """Process the transcription queue and send to WebSocket clients."""
        while self.transcription_queue:
            transcription = self.transcription_queue.pop(0)

            # Convert to JSON
            json_data = json.dumps(transcription)

            # Send to all active connections
            for connection_id, websocket in list(self.active_connections.items()):
                try:
                    # Use run_until_complete to run the coroutine synchronously
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(websocket.send_text(json_data))
                except Exception as e:
                    logger.error(f"Error sending to WebSocket {connection_id}: {e}")
                    # Connection may be dead, remove it
                    self.active_connections.pop(connection_id, None)

    def start(self, host: str = "127.0.0.1", port: int = 8000):
        """Start the API server.

        Args:
            host: The host to bind to
            port: The port to bind to
        """
        # Start the server in a separate thread
        self.server_thread = threading.Thread(
            target=self._run_server,
            args=(host, port),
            daemon=True,
        )
        self.server_thread.start()
        logger.info(f"API server started at http://{host}:{port}")

        # Mark as running
        self.running = True

    def _run_server(self, host: str, port: int):
        """Run the API server.

        Args:
            host: The host to bind to
            port: The port to bind to
        """
        uvicorn.run(self.app, host=host, port=port)

    def stop(self):
        """Stop the API server."""
        # Can't easily stop uvicorn, but we can mark as not running
        self.running = False
        logger.info("API server marked for shutdown")
