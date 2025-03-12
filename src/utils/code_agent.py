"""Code Agent integration to process requests for AI assistance."""
import json
import logging
import threading
import time
from typing import Dict, List, Optional

from src.audio.speech_synthesis import speak
from src.core.state_manager import StateManager
from src.utils.assistant import get_assistant_response

# Configure logging
logger = logging.getLogger(__name__)

class CodeAgentHandler:
    """Handler for AI Code Agent requests and integration with speech processing."""

    def __init__(self, state: StateManager):
        """Initialize the Code Agent handler.

        Args:
            state: The shared state manager
        """
        self.state = state
        self.active_sessions: Dict[str, Dict] = {}
        self.running = False

        # Queue for requests
        self.request_queue: List[Dict] = []

        # Thread for processing requests
        self.processing_thread = None

    def start(self):
        """Start the Code Agent handler."""
        if self.running:
            return

        self.running = True
        self.processing_thread = threading.Thread(
            target=self._process_requests_loop,
            daemon=True,
        )
        self.processing_thread.start()
        logger.info("Code Agent handler started")

    def stop(self):
        """Stop the Code Agent handler."""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
        logger.info("Code Agent handler stopped")

    def submit_request(self, prompt: str, session_id: str) -> str:
        """Submit a Code Agent request.

        Args:
            prompt: The prompt to process
            session_id: The session ID for context

        Returns:
            Request ID for tracking
        """
        request_id = f"req_{int(time.time())}_{session_id}"

        # Create or update session
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "history": [],
                "created_at": time.time(),
                "last_activity": time.time(),
            }
        else:
            self.active_sessions[session_id]["last_activity"] = time.time()

        # Add to session history
        self.active_sessions[session_id]["history"].append({
            "role": "user",
            "content": prompt,
            "timestamp": time.time(),
        })

        # Add to request queue
        self.request_queue.append({
            "id": request_id,
            "prompt": prompt,
            "session_id": session_id,
            "submitted_at": time.time(),
        })

        logger.info(f"Request {request_id} submitted for session {session_id}")
        return request_id

    def _process_requests_loop(self):
        """Process requests in the queue."""
        while self.running:
            if not self.request_queue:
                # Sleep if queue is empty
                time.sleep(0.1)
                continue

            # Get the next request
            request = self.request_queue.pop(0)

            try:
                # Process the request
                response = self._process_request(request)

                # Update session history
                session_id = request["session_id"]
                if session_id in self.active_sessions:
                    self.active_sessions[session_id]["history"].append({
                        "role": "assistant",
                        "content": response,
                        "timestamp": time.time(),
                    })
                    self.active_sessions[session_id]["last_activity"] = time.time()

                logger.info(f"Request {request['id']} processed successfully")
            except Exception as e:
                logger.error(f"Error processing request {request['id']}: {e}")

    def _process_request(self, request: Dict) -> str:
        """Process a single Code Agent request.

        Args:
            request: The request to process

        Returns:
            The response text
        """
        prompt = request["prompt"]
        session_id = request["session_id"]

        # Get session history for context
        history = []
        if session_id in self.active_sessions:
            history = self.active_sessions[session_id]["history"]

        # Use the assistant module to process the request
        response = get_assistant_response(
            prompt,
            context={"session_id": session_id, "history": history},
        )

        # Always use speech synthesis to speak the response
        try:
            speak(response.text)
        except Exception as e:
            logger.error(f"Error speaking Code Agent response: {e}")

        return response.text

    def clean_old_sessions(self, max_age_seconds: int = 3600):
        """Clean up old sessions.

        Args:
            max_age_seconds: Maximum age in seconds for inactive sessions
        """
        now = time.time()
        to_remove = []

        for session_id, session in self.active_sessions.items():
            if now - session["last_activity"] > max_age_seconds:
                to_remove.append(session_id)

        for session_id in to_remove:
            del self.active_sessions[session_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive sessions")
