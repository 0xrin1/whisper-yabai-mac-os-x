# Speech Recognition API

The Speech Recognition API is a standalone service that provides speech-to-text functionality using Whisper. It can be run on a separate machine from the main voice control system, allowing for better resource allocation and scalability.

## Quick Start

1. Start the Speech Recognition API server:
   ```bash
   ./scripts/run_speech_api.sh
   ```

2. Configure the main application to use the API:
   ```bash
   # Set environment variables
   export USE_SPEECH_API=true
   export SPEECH_API_URL=http://localhost:8080

   # Or use the provided configuration file
   source config/speech_api.env
   ```

3. Start the voice control daemon as usual:
   ```bash
   python src/daemon.py
   ```

## Architecture

The Speech Recognition API architecture consists of two main components:

1. **API Server**: A standalone service that handles speech recognition requests
   - Runs the Whisper model for speech-to-text
   - Provides RESTful and WebSocket interfaces
   - Can be deployed on a separate, more powerful machine

2. **API Client**: Integrated into the voice control system
   - Sends audio data to the API server
   - Processes transcription results
   - Falls back to local model if the API is unavailable

This separation allows for:
- Distributing computational load across machines
- Using more powerful hardware for speech recognition
- Centralized speech recognition for multiple clients
- Easier scaling and maintenance

## API Server

### Features

- RESTful API for transcription
- WebSocket support for real-time transcription
- Multiple Whisper model support
- JSON-based communication
- Automatic model loading and unloading
- Error handling and fallback mechanisms

### API Endpoints

- `GET /`: API information
- `GET /models`: List available models
- `POST /transcribe`: Transcribe audio data
- `POST /transcribe_file`: Transcribe an uploaded file
- `WebSocket /ws/transcribe`: Real-time transcription

### Running the Server

```bash
# Basic usage (default port 8080)
./scripts/run_speech_api.sh

# Custom port and host
./scripts/run_speech_api.sh --port 9000 --host 0.0.0.0

# Specify model size
./scripts/run_speech_api.sh --model medium
```

Or run the Python module directly:

```bash
python src/api/speech_recognition_api.py --host 0.0.0.0 --port 8080 --model large-v3
```

### Environment Variables

- `DEFAULT_MODEL_SIZE`: Default Whisper model size (tiny, base, small, medium, large-v3)
- `SPEECH_API_HOST`: Host to bind the server to (default: 0.0.0.0)
- `SPEECH_API_PORT`: Port to bind the server to (default: 8080)

## API Client

### Features

- Automatic connection to the API server
- Fallback to local model if API is unavailable
- Supports both REST and WebSocket interfaces
- Handles serialization and deserialization of audio data
- Manages connections and error handling

### Using the Client

```python
from src.api.speech_recognition_client import SpeechRecognitionClient

# Create client
client = SpeechRecognitionClient(api_url="http://localhost:8080")

# Check connection
if await client.check_connection():
    # Transcribe a file
    result = await client.transcribe("audio_file.wav")

    # Process the result
    text = result.get("text", "")
    confidence = result.get("confidence", 0.0)
    print(f"Transcription: {text} (Confidence: {confidence})")
```

### Environment Variables

- `USE_SPEECH_API`: Enable/disable the API client (true/false)
- `SPEECH_API_URL`: URL of the API server (default: http://localhost:8080)

## Example: Transcribing a File

Using the REST API:

```bash
# Using curl to transcribe a file
curl -X POST -F "file=@audio.wav" -F "model_size=large-v3" http://localhost:8080/transcribe_file
```

Using the Python client:

```bash
# Using the client script
python src/api/speech_recognition_client.py --api-url http://localhost:8080 --file audio.wav --model large-v3
```

## Performance Considerations

- The API server can be resource-intensive, especially with larger models
- For optimal performance:
  - Use a machine with a GPU for the API server
  - Adjust model size based on accuracy vs. speed requirements
  - Consider using WebSocket for real-time applications
  - Implement caching if processing similar audio repeatedly

## Troubleshooting

- If the API server fails to start, check:
  - Port availability (other services might be using the port)
  - Sufficient memory for the selected model
  - Python environment and dependencies

- If the client fails to connect:
  - Verify the server is running
  - Check network connectivity between client and server
  - Ensure correct URL and port configuration

- If transcription quality is poor:
  - Try a larger model (medium or large-v3)
  - Check audio quality and format
  - Adjust microphone settings for better input

## Security Considerations

The API server does not include authentication by default. For production use:

1. Restrict access to trusted networks
2. Implement an authentication mechanism
3. Use HTTPS for secure communication
4. Set up proper access controls

## Extending the API

The API can be extended with additional features:

1. Multiple language support
2. Speaker diarization
3. Custom prompt engineering
4. Integration with other speech processing tools
5. Caching for improved performance
