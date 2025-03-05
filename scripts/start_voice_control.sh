#!/bin/bash
# Simple script to start the voice control daemon

# Change to the project directory
cd "$(dirname "$0")/.."

# Bypass permission check for Ghostty
echo "Starting voice control daemon in Ghostty..."
echo "Note: Make sure Ghostty has been granted accessibility permissions in System Preferences"
echo "Press Ctrl+C to exit"
python src/daemon.py