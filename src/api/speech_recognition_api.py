#!/usr/bin/env python3
"""
Speech Recognition API Service

A standalone API that provides speech-to-text functionality using Whisper.
This can be run on a separate machine from the main voice control system.
"""

import asyncio
import base64
import json
import logging
import os
import tempfile
import time
import uuid
from typing import Dict, List, Optional, Union

import torch
import uvicorn
import whisper
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("speech-recognition-api")

# Models for API
class TranscriptionRequest(BaseModel):
    """Request model for transcription."""
    audio_data: str  # Base64 encoded audio data
    model_size: Optional[str] = "large-v3"
    language: Optional[str] = None
    prompt: Optional[str] = None


class TranscriptionResponse(BaseModel):
    """Response model for transcription."""
    text: str
    confidence: float
    language: Optional[str] = None
    segments: Optional[List[Dict]] = None
    processing_time: float


class SpeechRecognitionAPI:
    """API server for speech recognition using Whisper."""

    def __init__(self):
        """Initialize the API server."""
        self.app = FastAPI(title="Speech Recognition API")

        # Available Whisper models
        self.models: Dict[str, whisper.Whisper] = {}
        self.default_model_size = os.getenv("DEFAULT_MODEL_SIZE", "large-v3")

        # Set up CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, restrict this to specific domains
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Set up API routes
        self.setup_routes()

    def setup_routes(self):
        """Set up API routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "Speech Recognition API",
                "version": "1.0.0",
                "status": "running",
            }

        @self.app.get("/models")
        async def list_models():
            """List available models."""
            return {
                "loaded_models": list(self.models.keys()),
                "available_models": [
                    "tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"
                ],
                "default_model": self.default_model_size,
            }

        @self.app.post("/transcribe")
        async def transcribe(request: TranscriptionRequest):
            """Transcribe audio using Whisper.

            Args:
                request: The transcription request

            Returns:
                The transcription response
            """
            try:
                # Get the model to use
                model_size = request.model_size or self.default_model_size
                model = await self.get_model(model_size)

                # Decode the audio data
                audio_data = base64.b64decode(request.audio_data)

                # Save to a temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_file.write(audio_data)
                temp_file.close()

                try:
                    # Time the transcription
                    start_time = time.time()

                    # Transcribe the audio
                    result = model.transcribe(
                        temp_file.name,
                        language=request.language,
                        initial_prompt=request.prompt,
                    )

                    # Calculate processing time
                    processing_time = time.time() - start_time

                    # Extract the results
                    text = result["text"].strip()
                    confidence = result.get("confidence", 1.0)
                    language = result.get("language")
                    segments = result.get("segments")

                    # Clean up the temporary file
                    os.unlink(temp_file.name)

                    # Force memory cleanup
                    torch.cuda.empty_cache() if hasattr(
                        torch, "cuda"
                    ) and torch is not None else None

                    return TranscriptionResponse(
                        text=text,
                        confidence=confidence,
                        language=language,
                        segments=segments,
                        processing_time=processing_time,
                    )
                except Exception as e:
                    # Clean up the temporary file
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                    raise e
            except Exception as e:
                logger.error(f"Error transcribing audio: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/transcribe_file")
        async def transcribe_file(
            file: UploadFile = File(...),
            model_size: Optional[str] = None,
            language: Optional[str] = None,
            prompt: Optional[str] = None,
        ):
            """Transcribe an uploaded audio file.

            Args:
                file: The audio file to transcribe
                model_size: The model size to use
                language: The language of the audio
                prompt: Initial prompt for the model

            Returns:
                The transcription response
            """
            try:
                # Get the model to use
                model_size = model_size or self.default_model_size
                model = await self.get_model(model_size)

                # Save to a temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_file.write(await file.read())
                temp_file.close()

                try:
                    # Time the transcription
                    start_time = time.time()

                    # Transcribe the audio
                    result = model.transcribe(
                        temp_file.name,
                        language=language,
                        initial_prompt=prompt,
                    )

                    # Calculate processing time
                    processing_time = time.time() - start_time

                    # Extract the results
                    text = result["text"].strip()
                    confidence = result.get("confidence", 1.0)
                    language = result.get("language")
                    segments = result.get("segments")

                    # Clean up the temporary file
                    os.unlink(temp_file.name)

                    # Force memory cleanup
                    torch.cuda.empty_cache() if hasattr(
                        torch, "cuda"
                    ) and torch is not None else None

                    return TranscriptionResponse(
                        text=text,
                        confidence=confidence,
                        language=language,
                        segments=segments,
                        processing_time=processing_time,
                    )
                except Exception as e:
                    # Clean up the temporary file
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                    raise e
            except Exception as e:
                logger.error(f"Error transcribing audio file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.websocket("/ws/transcribe")
        async def websocket_transcribe(websocket: WebSocket):
            """WebSocket endpoint for real-time transcription.

            Args:
                websocket: The WebSocket connection
            """
            await websocket.accept()
            logger.info("WebSocket client connected")

            try:
                # First message should contain configuration
                config = await websocket.receive_json()
                logger.info(f"Received configuration: {config}")

                # Extract configuration
                model_size = config.get("model_size", self.default_model_size)
                language = config.get("language")
                prompt = config.get("prompt")

                # Get the model
                model = await self.get_model(model_size)
                logger.info(f"Using model: {model_size}")

                # Process audio chunks
                while True:
                    # Receive audio data
                    data = await websocket.receive_text()

                    # Skip heartbeat messages
                    if data == "heartbeat":
                        await websocket.send_text("heartbeat")
                        continue

                    try:
                        # Parse JSON message
                        message = json.loads(data)
                        audio_data = message.get("audio_data")

                        if not audio_data:
                            await websocket.send_json({"error": "No audio data provided"})
                            continue

                        # Decode the audio data
                        audio_bytes = base64.b64decode(audio_data)

                        # Save to a temporary file
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                        temp_file.write(audio_bytes)
                        temp_file.close()

                        try:
                            # Time the transcription
                            start_time = time.time()

                            # Transcribe the audio
                            result = model.transcribe(
                                temp_file.name,
                                language=language,
                                initial_prompt=prompt,
                            )

                            # Calculate processing time
                            processing_time = time.time() - start_time

                            # Extract the results
                            text = result["text"].strip()
                            confidence = result.get("confidence", 1.0)
                            detected_language = result.get("language")
                            segments = result.get("segments")

                            # Clean up the temporary file
                            os.unlink(temp_file.name)

                            # Force memory cleanup
                            torch.cuda.empty_cache() if hasattr(
                                torch, "cuda"
                            ) and torch is not None else None

                            # Send the response
                            await websocket.send_json({
                                "text": text,
                                "confidence": confidence,
                                "language": detected_language,
                                "segments": segments,
                                "processing_time": processing_time,
                            })
                        except Exception as e:
                            # Clean up the temporary file
                            if os.path.exists(temp_file.name):
                                os.unlink(temp_file.name)

                            # Send error
                            await websocket.send_json({"error": str(e)})
                    except json.JSONDecodeError:
                        await websocket.send_json({"error": "Invalid JSON"})
                    except Exception as e:
                        await websocket.send_json({"error": str(e)})
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")

    async def get_model(self, model_size: str) -> whisper.Whisper:
        """Get a Whisper model, loading it if necessary.

        Args:
            model_size: The model size to use

        Returns:
            The Whisper model
        """
        # Check if model is already loaded
        if model_size in self.models:
            return self.models[model_size]

        # Load the model
        logger.info(f"Loading Whisper model: {model_size}")
        model = whisper.load_model(model_size)
        self.models[model_size] = model
        logger.info(f"Whisper model {model_size} loaded successfully")

        return model

    def start(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the API server.

        Args:
            host: The host to bind to
            port: The port to bind to
        """
        # Preload the default model
        asyncio.run(self.get_model(self.default_model_size))

        # Start the server
        uvicorn.run(self.app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Speech Recognition API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--model", default="large-v3", help="Default model size")
    args = parser.parse_args()

    # Set environment variables
    os.environ["DEFAULT_MODEL_SIZE"] = args.model

    # Start the API server
    api = SpeechRecognitionAPI()
    api.start(host=args.host, port=args.port)
