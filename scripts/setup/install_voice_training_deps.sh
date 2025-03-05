#!/bin/bash
# Install voice training dependencies including advanced audio analysis libraries

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== Installing Voice Training Dependencies =====${NC}"
echo "This script will install the necessary Python packages for enhanced voice analysis"

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo -e "${RED}Error: pip is not installed or not in PATH${NC}"
    echo "Please install pip first, then run this script again"
    exit 1
fi

# Function to install a package with pip
install_package() {
    package=$1
    echo -e "${YELLOW}Installing $package...${NC}"
    pip install $package
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully installed $package${NC}"
    else
        echo -e "${RED}✗ Failed to install $package${NC}"
        return 1
    fi
    return 0
}

# Install required packages
echo "Installing key packages for advanced voice analysis..."

# Install main dependencies
packages=(
    "librosa>=0.9.0"
    "numpy>=1.20.0"
    "matplotlib>=3.5.0"
    "scipy>=1.7.0"
    "soundfile>=0.10.0"
)

# Install each package
for package in "${packages[@]}"; do
    install_package "$package"
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}Warning: Some packages may not have installed correctly.${NC}"
        echo "You can still use voice training, but with reduced functionality."
    fi
done

# Test if librosa can be imported
echo "Testing librosa installation..."
python -c "import librosa; print(f'Librosa {librosa.__version__} installed successfully')" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Librosa installed and working correctly${NC}"
else
    echo -e "${YELLOW}Librosa couldn't be imported. Installing system dependencies for librosa...${NC}"
    
    # On macOS, we might need to install additional dependencies
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Detected macOS, installing additional dependencies with brew..."
        if command -v brew &> /dev/null; then
            brew install libsndfile llvm
            echo "Installing librosa with system libsndfile..."
            pip install --no-binary :all: librosa
        else
            echo -e "${YELLOW}Homebrew not found. Please install libsndfile manually.${NC}"
        fi
    # On Linux, we need different dependencies
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Detected Linux, you may need to install libsndfile manually with your package manager"
        echo "For Debian/Ubuntu: sudo apt-get install libsndfile1"
        echo "For Red Hat/Fedora: sudo dnf install libsndfile"
    fi
    
    # Test again
    python -c "import librosa; print(f'Librosa {librosa.__version__} installed successfully')" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Librosa now installed and working correctly${NC}"
    else
        echo -e "${YELLOW}Librosa installation still problematic, but voice training will still work with basic functionality${NC}"
    fi
fi

echo
echo -e "${GREEN}===== Dependencies Installation Complete =====${NC}"
echo "You can now use enhanced voice training with advanced audio analysis"
echo "To train your voice model, run:"
echo "  python src/audio/voice_training.py"
echo
echo "For neural voice training with GPU, see the following script:"
echo "  scripts/gpu/train_neural_voice.py"