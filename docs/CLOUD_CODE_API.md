# Cloud Code API Integration

The Cloud Code API allows external applications to interact with the voice control system's speech recognition capabilities. This enables you to create cloud-based assistants that leverage the local speech processing while adding custom responses and interactions.

## Quick Start

1. Start the voice control daemon with API enabled:
   ```bash
   ./scripts/launch_cloud_api.sh
   ```

2. Open the example integration in your browser:
   ```bash
   open examples/cloud_code_demo.html
   ```

3. Click "Connect to WebSocket" to start receiving real-time transcriptions

## API Endpoints

### Status Endpoint

Get the current status of the voice control system.

```
GET http://127.0.0.1:8000/status
```

Example response:
```json
{
  "status": "running",
  "mode": "dictation",
  "muted": false,
  "recording": false
}
```

### Speak Endpoint

Synthesize speech from text.

```
POST http://127.0.0.1:8000/speak?text=Hello%20world&voice_id=optional_voice_id
```

Parameters:
- `text` (required): Text to synthesize
- `voice_id` (optional): Voice ID to use

Example response:
```json
{
  "message": "Speech synthesized successfully"
}
```

### Cloud Code Endpoint

Process a Cloud Code request.

```
POST http://127.0.0.1:8000/cloud-code
```

Request body:
```json
{
  "prompt": "What's the weather like today?",
  "session_id": "optional_session_id"
}
```

Parameters:
- `prompt` (required): The prompt to process
- `session_id` (optional): Session ID for context

Example response:
```json
{
  "response": "Processing your request: What's the weather like today?",
  "conversation_id": "session_1713112345"
}
```

### WebSocket Endpoint

Connect to the WebSocket endpoint to receive real-time transcriptions.

```
WebSocket ws://127.0.0.1:8000/ws/transcription
```

Example message:
```json
{
  "text": "Open Safari",
  "is_command": true,
  "confidence": 0.95,
  "timestamp": 1713112345.67
}
```

## Using the Test Client

A test client is included to demonstrate API usage:

```bash
# Test API status
python src/api/client.py --status

# Connect to real-time transcription WebSocket
python src/api/client.py --ws

# Test speech synthesis
python src/api/client.py --speak "Hello, world"

# Test cloud code integration
python src/api/client.py --prompt "What's the weather like today?"
```

## Integration Examples

### JavaScript/Web Integration

```javascript
// Connect to WebSocket for real-time transcriptions
const socket = new WebSocket('ws://127.0.0.1:8000/ws/transcription');

socket.addEventListener('open', (event) => {
  console.log('Connected to transcription WebSocket');
});

socket.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  console.log(`Transcription: ${data.text} (${data.is_command ? 'Command' : 'Dictation'})`);
});

// Send text to be spoken
async function speakText(text) {
  const response = await fetch('http://127.0.0.1:8000/speak?text=' + encodeURIComponent(text), {
    method: 'POST'
  });
  return response.json();
}

// Send a cloud code request
async function processPrompt(prompt) {
  const response = await fetch('http://127.0.0.1:8000/cloud-code', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      prompt: prompt,
      session_id: 'web-client-' + Date.now()
    })
  });
  return response.json();
}
```

### Python Integration

```python
import asyncio
import websockets
import json
import requests

# Function to connect to the WebSocket
async def connect_to_transcription():
    async with websockets.connect('ws://127.0.0.1:8000/ws/transcription') as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Transcription: {data['text']} ({'Command' if data['is_command'] else 'Dictation'})")

# Function to speak text
def speak_text(text, voice_id=None):
    url = 'http://127.0.0.1:8000/speak'
    params = {'text': text}
    if voice_id:
        params['voice_id'] = voice_id
    response = requests.post(url, params=params)
    return response.json()

# Function to process a cloud code request
def process_prompt(prompt, session_id=None):
    url = 'http://127.0.0.1:8000/cloud-code'
    data = {'prompt': prompt}
    if session_id:
        data['session_id'] = session_id
    response = requests.post(url, json=data)
    return response.json()
```

## Advanced Integration

For more advanced integrations, you can extend the Cloud Code handler in your own application:

1. Create a custom Cloud Code handler by subclassing `CloudCodeHandler`
2. Override the `_process_request` method to implement your custom logic
3. Register your handler with the API server

This allows you to implement custom LLM integration, external API calls, and more sophisticated conversations while still leveraging the local speech recognition capabilities.

## Security Considerations

The API server does not include authentication by default. For production use, consider:

1. Restricting access to localhost only
2. Implementing an authentication mechanism
3. Using HTTPS for secure communication
4. Setting up proper access controls

## Extending the API

You can extend the API with additional endpoints by modifying `src/api/api_server.py`:

1. Create a new endpoint in the `setup_routes` method
2. Add corresponding functionality to the CloudCodeHandler
3. Update the client to use your new endpoints

## Troubleshooting

- If the API server fails to start, check the logs for error messages
- Verify that the required dependencies are installed (`fastapi`, `uvicorn`)
- Make sure the specified port is not already in use
- For WebSocket connection issues, verify that your client supports WebSockets
- If speech synthesis fails, check that the TTS API is configured correctly
