#!/bin/bash
# Script to build and serve the documentation for Whisper Voice Control

set -e

# Define constants
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCS_SRC_DIR="$PROJECT_ROOT/docs-src"
SRC_DIR="$PROJECT_ROOT/src"
DOCKER_IMAGE="whisper-voice-control-docs"
DOCKER_PORT=8080

# Function for checking command availability
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 is required but not installed" >&2
        exit 1
    fi
}

# Check for required commands
check_command python3
check_command docker

# Function to display usage instructions
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build and serve the documentation for Whisper Voice Control"
    echo ""
    echo "Options:"
    echo "  --build-only      Build the documentation without serving"
    echo "  --serve-only      Serve the existing documentation without rebuilding"
    echo "  --port PORT       Specify a port for serving (default: $DOCKER_PORT)"
    echo "  --help            Show this help message"
    echo ""
}

# Initialize variables
BUILD_ONLY=false
SERVE_ONLY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --serve-only)
            SERVE_ONLY=true
            shift
            ;;
        --port)
            DOCKER_PORT="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Create necessary directories
mkdir -p "$DOCS_SRC_DIR/src"
mkdir -p "$DOCS_SRC_DIR/theme"

# Check if we should extract documentation
if [[ "$SERVE_ONLY" = false ]]; then
    echo "Extracting documentation from Python source files..."
    python3 "$SCRIPT_DIR/extract_docs.py" --base-dir "$SRC_DIR" --output-dir "$DOCS_SRC_DIR/src"
    echo "Documentation extraction complete!"
fi

# Build the Docker image if not in serve-only mode
if [[ "$SERVE_ONLY" = false ]]; then
    echo "Building documentation Docker image..."
    docker build -t "$DOCKER_IMAGE" -f "$PROJECT_ROOT/Dockerfile.docs" "$PROJECT_ROOT"
    echo "Docker image build complete!"
fi

# Exit if build-only mode
if [[ "$BUILD_ONLY" = true ]]; then
    echo "Documentation build complete. The Docker image is ready to serve."
    exit 0
fi

# Run the documentation server
echo "Starting documentation server on http://localhost:$DOCKER_PORT..."
docker run --rm -p "$DOCKER_PORT:8080" "$DOCKER_IMAGE"