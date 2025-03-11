#!/usr/bin/env python3
"""Client script for testing the Cloud Code API."""

import argparse
import asyncio
import json
import requests
import websockets
import os
import time

async def connect_to_websocket(url):
    """Connect to the WebSocket API and print transcriptions.

    Args:
        url: WebSocket URL to connect to
    """
    print(f"Connecting to WebSocket: {url}")
    try:
        async with websockets.connect(url) as websocket:
            print("Connected to WebSocket")

            # Keep connection open and print received messages
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)

                    # Format and print the transcription
                    timestamp = time.strftime('%H:%M:%S', time.localtime(data.get('timestamp', time.time())))
                    mode = "COMMAND" if data.get('is_command', False) else "DICTATION"
                    confidence = f"{data.get('confidence', 0.0) * 100:.1f}%"

                    print(f"[{timestamp}] [{mode}] ({confidence}) {data.get('text', '')}")

                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    break
    except Exception as e:
        print(f"Failed to connect: {e}")

def test_api_status(base_url):
    """Test the API status endpoint.

    Args:
        base_url: Base URL of the API
    """
    url = f"{base_url}/status"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print("API Status:")
            for key, value in data.items():
                print(f"  {key}: {value}")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Failed to connect: {e}")

def test_speech(base_url, text, voice_id=None):
    """Test the speech synthesis endpoint.

    Args:
        base_url: Base URL of the API
        text: Text to synthesize
        voice_id: Optional voice ID
    """
    url = f"{base_url}/speak"
    try:
        params = {"text": text}
        if voice_id:
            params["voice_id"] = voice_id

        response = requests.post(url, params=params)
        if response.status_code == 200:
            print("Speech synthesis request sent successfully")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Failed to connect: {e}")

def test_cloud_code(base_url, prompt, session_id=None):
    """Test the cloud code endpoint.

    Args:
        base_url: Base URL of the API
        prompt: Prompt to process
        session_id: Optional session ID
    """
    url = f"{base_url}/cloud-code"
    try:
        data = {"prompt": prompt}
        if session_id:
            data["session_id"] = session_id

        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            print("Cloud Code Response:")
            print(f"  Response: {result.get('response', '')}")
            print(f"  Conversation ID: {result.get('conversation_id', '')}")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Failed to connect: {e}")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Cloud Code API")
    parser.add_argument("--host", default="127.0.0.1", help="API host")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    parser.add_argument("--status", action="store_true", help="Test API status endpoint")
    parser.add_argument("--speak", help="Test speech synthesis with specified text")
    parser.add_argument("--voice", help="Voice ID for speech synthesis")
    parser.add_argument("--prompt", help="Test cloud code with specified prompt")
    parser.add_argument("--session", help="Session ID for cloud code request")
    parser.add_argument("--ws", action="store_true", help="Connect to WebSocket transcription stream")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    ws_url = f"ws://{args.host}:{args.port}/ws/transcription"

    # If no specific action is specified, test status
    if not (args.status or args.speak or args.prompt or args.ws):
        args.status = True

    # Test API status
    if args.status:
        test_api_status(base_url)

    # Test speech synthesis
    if args.speak:
        test_speech(base_url, args.speak, args.voice)

    # Test cloud code
    if args.prompt:
        test_cloud_code(base_url, args.prompt, args.session)

    # Connect to WebSocket
    if args.ws:
        await connect_to_websocket(ws_url)

if __name__ == "__main__":
    asyncio.run(main())
