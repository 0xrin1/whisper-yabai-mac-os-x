# neural_voice_client

Neural Voice Client - Connects to GPU-powered voice server
Enables high-quality neural voice synthesis on lightweight clients

Source: `audio/neural_voice_client.py`

## Function: `configure(server: str = DEFAULT_SERVER, enable_fallback: bool = True)`

Configure the neural voice client.
    
    Args:
        server: URL of the neural voice server (including protocol and port)
        enable_fallback: Whether to enable fallback to local TTS if server is unavailable

## Function: `check_server_connection()`

Check if the neural voice server is available.
    
    Returns:
        Boolean indicating if server is available

## Function: `play_audio(file_path: str)`

Play an audio file.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Boolean indicating success

## Function: `cleanup()`

Clean up temporary files.

