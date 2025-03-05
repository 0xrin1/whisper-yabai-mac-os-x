#!/bin/bash
# Script to process the entire documentation workflow
# 1. Add docstrings to key files
# 2. Extract documentation
# 3. Build documentation site

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_DIR="$PROJECT_ROOT/src"
DOCS_SRC_DIR="$PROJECT_ROOT/docs-src"

# Make sure necessary directories exist
mkdir -p "$DOCS_SRC_DIR/src"
mkdir -p "$DOCS_SRC_DIR/theme"

# Display heading
echo "======================================================================================="
echo "                  Whisper Voice Control Documentation Generator                        "
echo "======================================================================================="

echo "Step 1: Adding docstrings to key files..."
# Process important source files first
KEY_FILES=(
  "$SRC_DIR/core/state_manager.py"
  "$SRC_DIR/core/error_handler.py"
  "$SRC_DIR/audio/audio_processor.py"
  "$SRC_DIR/audio/audio_recorder.py"
  "$SRC_DIR/audio/neural_voice_client.py"
  "$SRC_DIR/utils/command_processor.py"
  "$SRC_DIR/utils/llm_interpreter.py"
)

# Add docstrings to key files individually for more control
for file in "${KEY_FILES[@]}"; do
  echo "Processing docstrings for $file"
  python3 "$SCRIPT_DIR/add_docstrings.py" --file "$file"
done

# Process the remaining files by directory
echo "Processing docstrings for remaining files in src/core..."
python3 "$SCRIPT_DIR/add_docstrings.py" --dir "$SRC_DIR/core"

echo "Processing docstrings for remaining files in src/audio..."
python3 "$SCRIPT_DIR/add_docstrings.py" --dir "$SRC_DIR/audio"

echo "Processing docstrings for remaining files in src/utils..."
python3 "$SCRIPT_DIR/add_docstrings.py" --dir "$SRC_DIR/utils"

echo "Processing docstrings for remaining files in src/ui..."
python3 "$SCRIPT_DIR/add_docstrings.py" --dir "$SRC_DIR/ui"

echo "Processing docstrings for remaining files in src/config..."
python3 "$SCRIPT_DIR/add_docstrings.py" --dir "$SRC_DIR/config"

echo "Processing docstrings for root modules in src/..."
find "$SRC_DIR" -maxdepth 1 -name "*.py" | while read -r file; do
  echo "Processing docstrings for $file"
  python3 "$SCRIPT_DIR/add_docstrings.py" --file "$file"
done

echo "Step 2: Extracting documentation..."
# Extract docstrings to markdown
python3 "$SCRIPT_DIR/extract_docs.py" --base-dir "$SRC_DIR" --output-dir "$DOCS_SRC_DIR/src"

echo "Step 3: Building documentation site..."
# Check if mdBook is installed
if ! command -v mdbook &> /dev/null; then
  echo "Installing mdBook..."
  cargo install mdbook
fi

# Build the documentation
mdbook build "$DOCS_SRC_DIR"

echo "Step 4: Serving documentation..."
echo "Documentation built successfully at $DOCS_SRC_DIR/book"
echo ""
echo "To serve the documentation, run one of the following:"
echo "  1. mdbook serve $DOCS_SRC_DIR"
echo "  2. $SCRIPT_DIR/build_docs.sh --serve-only"
echo "  3. Use Docker with: docker build -t whisper-voice-control-docs -f $PROJECT_ROOT/Dockerfile.docs $PROJECT_ROOT"
echo ""

# Ask if user wants to serve the documentation
read -p "Would you like to serve the documentation now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Starting documentation server..."
  mdbook serve --open "$DOCS_SRC_DIR"
fi