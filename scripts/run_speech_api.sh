#!/bin/bash
# Script to run the standalone Speech Recognition API

# Default values
API_PORT=8080
API_HOST="0.0.0.0"
MODEL="large-v3"

# Display banner
echo "========================================"
echo "  Speech Recognition API Server"
echo "========================================"
echo ""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      API_PORT="$2"
      shift 2
      ;;
    --host)
      API_HOST="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Print configuration
echo "Starting Speech Recognition API server:"
echo "  Host: $API_HOST"
echo "  Port: $API_PORT"
echo "  Model: $MODEL"
echo ""
echo "This server provides speech-to-text functionality using Whisper."
echo "It can be run on a separate machine from the main voice control system."
echo ""
echo "API endpoints:"
echo "  GET /                 - API information"
echo "  GET /models           - List available models"
echo "  POST /transcribe      - Transcribe audio data"
echo "  POST /transcribe_file - Transcribe an uploaded file"
echo "  WebSocket /ws/transcribe - Real-time transcription"
echo ""
echo "Press Ctrl+C to exit"
echo ""

# Set environment variables
export DEFAULT_MODEL_SIZE="$MODEL"

# Start the API server
CMD="python src/api/speech_recognition_api.py --host $API_HOST --port $API_PORT --model $MODEL"
echo "Running command: $CMD"
echo ""

# Execute the command
$CMD

# Script end message
echo ""
echo "Speech Recognition API server stopped"
