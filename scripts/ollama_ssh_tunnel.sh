#!/bin/bash

# SSH tunnel script for Ollama API
# This script creates an SSH tunnel to forward the Ollama port (11434)
# from a remote GPU server to your local machine

# Configuration

REMOTE_SERVER="user@gpu-server"  # Replace with your server details
REMOTE_PORT=11434
LOCAL_PORT=11434

# Create the SSH tunnel
echo "Creating SSH tunnel for Ollama API..."
echo "Remote: $REMOTE_SERVER:$REMOTE_PORT → Local: localhost:$LOCAL_PORT"

ssh -N -L $LOCAL_PORT:localhost:$REMOTE_PORT $REMOTE_SERVER

# The -N flag tells SSH not to execute a remote command
# The -L flag specifies the port forwarding: local_port:remote_host:remote_port

# Note: This script will run until terminated. Press Ctrl+C to stop the tunnel.
