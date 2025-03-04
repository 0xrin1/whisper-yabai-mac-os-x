#!/bin/bash
# Script to retrieve trained neural voice model from GPU server

# Configuration
SERVER_USER="user"
SERVER_HOST="gpu-server.example.com" 
SERVER_PATH="/home/user/voice-training"
MODEL_DIR="voice_models/neural_voice"
REMOTE_MODEL_PATH="models/neural_voice"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Display banner
echo -e "${GREEN}"
echo "==============================================="
echo "   Neural Voice Model - Retrieval Script"
echo "==============================================="
echo -e "${NC}"

# Request server information if not provided
if [ "$SERVER_HOST" == "gpu-server.example.com" ]; then
    echo -e "${YELLOW}Please provide GPU server information:${NC}"
    read -p "Server hostname or IP: " SERVER_HOST
    read -p "Username: " SERVER_USER
    read -p "Remote directory path: " SERVER_PATH
    
    if [ -z "$SERVER_HOST" ] || [ -z "$SERVER_USER" ] || [ -z "$SERVER_PATH" ]; then
        echo -e "${RED}Error: Server information incomplete.${NC}"
        exit 1
    fi
fi

# Check if remote training is complete
echo -e "\n${GREEN}Checking if training is complete...${NC}"
SSH_CHECK=$(ssh "$SERVER_USER@$SERVER_HOST" "if [ -f '$SERVER_PATH/$REMOTE_MODEL_PATH/model_info.json' ]; then echo 'FOUND'; else echo 'NOT_FOUND'; fi")

if [ "$SSH_CHECK" != "FOUND" ]; then
    echo -e "${RED}Error: Trained model not found on server!${NC}"
    echo -e "${YELLOW}The training might not be complete yet or failed.${NC}"
    echo -e "${YELLOW}Check the training_log.txt file on the server for details.${NC}"
    
    read -p "Check training log now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ssh -t "$SERVER_USER@$SERVER_HOST" "cat $SERVER_PATH/training_log.txt 2>/dev/null || echo 'Log file not found!'"
    fi
    
    exit 1
fi

# Create local directory
mkdir -p "$MODEL_DIR"

# Transfer model from server
echo -e "\n${GREEN}Retrieving neural voice model from server...${NC}"
rsync -avz --progress "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/$REMOTE_MODEL_PATH/" "$MODEL_DIR/"

# Check if transfer was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to retrieve model from server!${NC}"
    exit 1
fi

# Install model
echo -e "\n${GREEN}Installing neural voice model...${NC}"
cat > voice_models/active_model.json << EOF
{
  "active_model": "neural_voice",
  "path": "$(cd "$MODEL_DIR" && pwd)",
  "engine": "neural"
}
EOF

echo -e "\n${GREEN}Neural voice model retrieved and installed successfully!${NC}"
echo -e "${GREEN}The model is now set as the active voice for your system.${NC}"
echo
echo -e "${YELLOW}To test the model, run:${NC}"
echo -e "  python -c \"import src.speech_synthesis as speech; speech.speak('This is my neural voice model speaking')\"" 
echo
echo -e "${YELLOW}If you need to fine-tune the model or make adjustments, edit:${NC}"
echo -e "  $MODEL_DIR/model_info.json"