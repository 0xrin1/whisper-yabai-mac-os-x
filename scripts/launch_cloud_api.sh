#!/bin/bash
# Script to launch the Voice Control daemon with Cloud Code API enabled

# Default values
API_PORT=8000
API_HOST="127.0.0.1"
ONBOARD=false

# Display banner
echo "========================================"
echo "  Voice Control with Cloud Code API"
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
    --onboard)
      ONBOARD=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Set environment variables
export API_PORT="$API_PORT"
export API_HOST="$API_HOST"

# Print configuration
echo "Starting Voice Control daemon with Cloud Code API:"
echo "  API Host: $API_HOST"
echo "  API Port: $API_PORT"
echo ""

# Launch with appropriate options
CMD="python src/daemon.py --api --api-port $API_PORT --api-host $API_HOST"

if [ "$ONBOARD" = true ]; then
  CMD="$CMD --onboard"
  echo "Enabling onboarding conversation"
fi

echo "Running command: $CMD"
echo "Press Ctrl+C to exit"
echo ""

# Start the daemon
$CMD

# Script end message
echo ""
echo "Voice Control daemon stopped"
