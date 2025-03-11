# System Architecture

This document outlines the high-level architecture of the voice control system, including component interactions and data flows.

## System Components

The system consists of several key components:

1. **Audio Recording**: Captures user's voice input
2. **Speech Recognition**: Transcribes audio to text using Whisper
   - Local model for standalone usage
   - Speech Recognition API for distributed processing
3. **Command Processing**: Interprets text as commands or dictation
4. **Speech Synthesis**: Converts text to speech via external API
5. **UI Integration**: Provides user feedback
6. **Cloud Code API**: Allows external applications to integrate with speech recognition
7. **Standalone Speech API**: Provides speech recognition as a separate service

## Architecture Diagrams

### Basic Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Audio Input    ├────►│  Audio          ├────►│  Whisper        │
│  (Microphone)   │     │  Processor      │     │  Model          │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  macOS System   │◄────┤  Command        │◄────┤  Text           │
│  (Actions)      │     │  Processor      │     │  Transcription  │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 │
┌─────────────────┐     ┌────────▼────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Audio Output   │◄────┤  Speech         │◄────┤  External TTS   │
│  (Speakers)     │     │  Synthesis      │     │  API Server     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Distributed Architecture with Speech API

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Audio Input    ├────►│  Audio          ├────►│  Speech         │
│  (Microphone)   │     │  Processor      │     │  Recognition    │
│                 │     │                 │     │  Client         │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Speech         │     │  Whisper        │     │  Speech         │
│  Recognition    │◄────┤  Model          │◄────┤  Recognition    │
│  API Server     │     │  (GPU Machine)  │     │  API Request    │
│                 │     │                 │     │                 │
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Cloud Code     │     │  Command        │     │  Text           │
│  API Server     │◄────┤  Processor      │◄────┤  Transcription  │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Web Client     │     │  Speech         │◄────┤  External TTS   │
│  Applications   │     │  Synthesis      │     │  API Server     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │                 │
                        │  Audio Output   │
                        │  (Speakers)     │
                        │                 │
                        └─────────────────┘
```

## Sequence Diagrams

### Voice Command Processing

This sequence diagram shows the flow from voice input to command execution and speech feedback:

```mermaid
sequenceDiagram
    participant User
    participant Microphone
    participant AudioProcessor
    participant WhisperModel
    participant CommandProcessor
    participant TTSAPIServer
    participant SpeechSynthesis
    participant System

    User->>Microphone: Speak command
    Microphone->>AudioProcessor: Capture audio
    AudioProcessor->>WhisperModel: Process audio
    WhisperModel->>CommandProcessor: Transcribed text
    CommandProcessor->>System: Execute command
    CommandProcessor->>TTSAPIServer: Request speech synthesis
    TTSAPIServer->>SpeechSynthesis: Return audio data
    SpeechSynthesis->>User: Play audio feedback
```

### Dictation Mode Flow

This sequence diagram shows the flow for dictation mode:

```mermaid
sequenceDiagram
    participant User
    participant Microphone
    participant AudioProcessor
    participant WhisperModel
    participant CoreDictation
    participant System
    participant TTSAPIServer
    participant SpeechSynthesis

    User->>Microphone: Speak text for dictation
    Microphone->>AudioProcessor: Capture audio
    AudioProcessor->>WhisperModel: Process audio
    WhisperModel->>AudioProcessor: Transcribed text
    AudioProcessor->>CoreDictation: Send text for typing
    CoreDictation->>System: Type text at cursor
    AudioProcessor->>TTSAPIServer: Request confirmation speech
    TTSAPIServer->>SpeechSynthesis: Return audio data
    SpeechSynthesis->>User: Play confirmation audio
```

### Speech Synthesis Flow

This sequence diagram shows the detailed flow of the speech synthesis process:

```mermaid
sequenceDiagram
    participant Application
    participant SpeechModule
    participant SpeechQueue
    participant TTSAPIServer
    participant AudioPlayer
    participant User

    Application->>SpeechModule: speak("Hello world")
    SpeechModule->>SpeechQueue: Add text to queue
    SpeechQueue->>TTSAPIServer: POST /synthesize
    Note over TTSAPIServer: Convert text to speech
    TTSAPIServer->>SpeechQueue: Return audio data
    SpeechQueue->>AudioPlayer: Play audio file
    AudioPlayer->>User: Audio output
    SpeechQueue->>SpeechModule: Process next item
```

### Speech Recognition API Flow

This sequence diagram shows the flow when using the standalone Speech Recognition API:

```mermaid
sequenceDiagram
    participant User
    participant Microphone
    participant AudioProcessor
    participant SpeechClient
    participant SpeechAPI
    participant WhisperModel
    participant CommandProcessor
    participant System
    participant TTSAPIServer
    participant SpeechSynthesis

    User->>Microphone: Speak command
    Microphone->>AudioProcessor: Capture audio
    AudioProcessor->>SpeechClient: Send audio data
    SpeechClient->>SpeechAPI: API request with audio
    SpeechAPI->>WhisperModel: Process audio
    WhisperModel->>SpeechAPI: Transcription result
    SpeechAPI->>SpeechClient: JSON response
    SpeechClient->>AudioProcessor: Transcribed text
    AudioProcessor->>CommandProcessor: Interpreted command
    CommandProcessor->>System: Execute command
    CommandProcessor->>TTSAPIServer: Request speech synthesis
    TTSAPIServer->>SpeechSynthesis: Return audio data
    SpeechSynthesis->>User: Play audio feedback
```

### Cloud Code API Integration

This sequence diagram shows how external applications can integrate with the system:

```mermaid
sequenceDiagram
    participant ExternalApp
    participant CloudCodeAPI
    participant WebSocket
    participant AudioProcessor
    participant SpeechAPI
    participant CommandProcessor
    participant TTSAPIServer

    ExternalApp->>WebSocket: Connect to /ws/transcription
    WebSocket-->>ExternalApp: Connection established

    AudioProcessor->>SpeechAPI: Process audio
    SpeechAPI-->>AudioProcessor: Transcription
    AudioProcessor->>WebSocket: Transcription event
    WebSocket-->>ExternalApp: Real-time transcription

    ExternalApp->>CloudCodeAPI: POST /cloud-code request
    CloudCodeAPI->>CommandProcessor: Process request
    CommandProcessor-->>CloudCodeAPI: Generate response
    CloudCodeAPI-->>ExternalApp: JSON response

    ExternalApp->>CloudCodeAPI: POST /speak request
    CloudCodeAPI->>TTSAPIServer: Synthesize speech
    TTSAPIServer-->>CloudCodeAPI: Speech processed
    CloudCodeAPI-->>ExternalApp: Success response
```

## Component Details

### Audio Processing

- Handles recording from microphone
- Manages silence detection and audio chunking
- Provides sound effects for user feedback
- Interfaces with Whisper for transcription
- Can connect to external Speech Recognition API

### Command Processing

- Interprets transcribed text
- Identifies commands vs. dictation
- Uses LLM for natural language understanding (optional)
- Executes commands via appropriate system interfaces
- Can be integrated with Cloud Code API

### Speech Synthesis

- Communicates with external TTS API
- Manages text-to-speech request queue
- Handles audio playback
- Provides both blocking and non-blocking speech options
- Implements fallback mechanisms

### External TTS API Integration

- HTTP REST API interface
- JSON-based request/response format
- Authentication via API key
- Supports various voices and speech parameters
- Returns WAV format audio data

### Speech Recognition API

- Standalone service for speech recognition
- RESTful API endpoints for transcription
- WebSocket support for real-time transcription
- Multiple Whisper model support
- Can be deployed on separate machine with GPU
- Docker container support for easy deployment
- Fallback mechanisms for reliability

### Cloud Code API

- Integration point for external applications
- WebSocket server for real-time transcription events
- REST endpoints for command processing and speech synthesis
- JSON-based communication protocol
- Supports session management for contextual interactions
- Enables distributed application architecture

## Environment Configuration

The system uses environment variables for configuration:

### Main Voice Control System
```
SPEECH_API_URL="https://api.example.com/synthesize"
SPEECH_API_KEY="your_api_key_here"
WHISPER_MODEL_SIZE="large-v3"
USE_LLM="true"
LLM_MODEL_PATH="models/llm-model.gguf"
```

### Speech Recognition API
```
USE_SPEECH_API="true"
SPEECH_API_URL="http://gpu-server:8080"
DEFAULT_MODEL_SIZE="large-v3"
SPEECH_API_HOST="0.0.0.0"
SPEECH_API_PORT="8080"
```

### Cloud Code API
```
API_PORT="8000"
API_HOST="127.0.0.1"
```

For detailed environment configuration options, see `README.md` and `SPEECH_API.md`.
