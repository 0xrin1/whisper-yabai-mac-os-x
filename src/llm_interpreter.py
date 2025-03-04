#!/usr/bin/env python3
"""
LLM-based interpreter for natural language commands.
Uses llama.cpp to run local language models for command processing.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from llama_cpp import Llama

# Configure logging
logger = logging.getLogger('llm-interpreter')

class CommandInterpreter:
    """
    Interprets natural language commands using a local LLM.
    Translates speech into structured command actions.
    """
    
    def __init__(self, model_path: Optional[str] = None, n_ctx: int = 2048):
        """Initialize the LLM-based command interpreter."""
        
        # Default model path from environment or use a sensible default
        if model_path is None:
            model_path = os.getenv('LLM_MODEL_PATH', 'models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf')
        
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.llm = None
        self.available_commands = self._load_available_commands()
        
        # Load the model
        self._load_model()
    
    def _load_model(self):
        """Load the LLM model."""
        if not os.path.exists(self.model_path):
            logger.error(f"Model file not found: {self.model_path}")
            logger.error("Please download a GGUF format model and set LLM_MODEL_PATH environment variable.")
            return False
        
        try:
            logger.info(f"Loading LLM model from {self.model_path}")
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=int(os.getenv('LLM_THREADS', '4')),
                verbose=False
            )
            logger.info("LLM model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load LLM model: {e}")
            return False
    
    def _load_available_commands(self) -> Dict[str, Any]:
        """Load available commands from commands.json."""
        try:
            with open('commands.json', 'r') as f:
                commands_data = json.load(f)
                
            # Extract custom commands if present
            if 'custom_commands' in commands_data:
                commands = commands_data['custom_commands']
            else:
                commands = commands_data
                
            # Add built-in command descriptions
            built_in = {
                "open": "Open an application",
                "focus": "Focus on an application window",
                "type": "Type text",
                "move": "Move a window (left, right, top, bottom)",
                "resize": "Resize a window (left, right, top, bottom)",
                "space": "Move window to a space (1-10)",
                "maximize": "Maximize the current window",
                "close": "Close the current window",
                "click": "Click the mouse at current position"
            }
            
            # Combine built-in and custom commands
            all_commands = {**built_in, **commands}
            return all_commands
            
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading commands: {e}")
            return {}
    
    def interpret_command(self, text: str) -> Tuple[str, List[str]]:
        """
        Interpret natural language command and convert to a structured command.
        
        Args:
            text: The natural language text to interpret
            
        Returns:
            Tuple of (command, arguments)
        """
        if self.llm is None:
            logger.error("LLM model not loaded. Cannot interpret command.")
            # Fall back to simple command extraction (first word)
            parts = text.lower().strip().split()
            if not parts:
                return ("", [])
            return (parts[0], parts[1:])
        
        # Construct prompt with available commands
        commands_list = "\n".join([f"- {cmd}: {desc}" for cmd, desc in self.available_commands.items()])
        
        prompt = f"""You are a voice command interpreter for a Mac OS X system. 
Convert the following natural language input into a structured command and arguments ONLY if it's clearly a command.

Available commands:
{commands_list}

Rules:
1. FIRST, determine if this is actually a command or just casual speech. If it's not clearly a command, respond with "COMMAND: none".
2. If it IS a command, extract the most appropriate command from the list of available commands.
3. Extract any relevant arguments for the command.
4. Be strict and conservative - only identify something as a command if it's clearly intended as one.
5. Return ONLY the command and arguments, nothing else.

Input: "{text}"

Output format:
COMMAND: [single command word or "none" if not a command]
ARGS: [comma-separated list of arguments]

Examples:
- "Open Safari" → "COMMAND: open" "ARGS: Safari"
- "Could you please maximize this window" → "COMMAND: maximize" "ARGS: "
- "I was thinking about going to the store later" → "COMMAND: none" "ARGS: "
- "The weather is nice today" → "COMMAND: none" "ARGS: "
- "Move this window to the left" → "COMMAND: move" "ARGS: left"

Output:
"""

        # Generate response from LLM
        try:
            response = self.llm(
                prompt, 
                max_tokens=50,
                stop=["Input:", "\n\n"],
                echo=False
            )
            
            # Parse the response
            response_text = response['choices'][0]['text'].strip()
            logger.debug(f"LLM response: {response_text}")
            
            # Extract command and arguments
            command = ""
            args = []
            
            for line in response_text.split('\n'):
                line = line.strip()
                if line.startswith("COMMAND:"):
                    command = line[8:].strip().lower()
                elif line.startswith("ARGS:"):
                    args_str = line[5:].strip()
                    if args_str:
                        args = [arg.strip() for arg in args_str.split(',')]
            
            logger.info(f"Interpreted command: {command}, args: {args}")
            return (command, args)
            
        except Exception as e:
            logger.error(f"Error interpreting command with LLM: {e}")
            # Fall back to simple command extraction
            parts = text.lower().strip().split()
            if not parts:
                return ("", [])
            return (parts[0], parts[1:])

    def generate_dynamic_response(self, transcription: str) -> Dict[str, Any]:
        """
        Generate a more dynamic response to an input that doesn't match any command.
        Returns a dictionary with potential actions or information.
        """
        if self.llm is None:
            return {"status": "error", "message": "LLM not available for dynamic responses"}
        
        prompt = f"""You are a Mac OS voice assistant. The user said: "{transcription}"

FIRST, determine if this input is clearly intended as a computer command or just casual speech.
Be very strict about this - only classify clear, explicit instructions as commands.

If this IS clearly a command that should control the computer, explain exactly what you think the user
wants to do in terms of:
1. Which application to interact with
2. What specific action to take
3. What parameters might be needed

Respond in this JSON format:
{{
  "is_command": true/false,
  "command_type": "application_control" or "system_control" or "information_request" or "other",
  "application": "name of application if relevant",
  "action": "specific action to take",
  "parameters": ["any", "needed", "parameters"],
  "explanation": "brief explanation of what you think the user wants"
}}

Examples:
- "Open Safari" → is_command: true
- "Could you please maximize this window" → is_command: true
- "I was thinking about going to the store later" → is_command: false
- "The weather is nice today" → is_command: false
- "Move this window to the left" → is_command: true

Be conservative. Only mark as commands if they're explicit instructions to do something on the computer.

JSON:
"""

        try:
            response = self.llm(
                prompt, 
                max_tokens=300,
                stop=["```", "Input:"],
                echo=False
            )
            
            response_text = response['choices'][0]['text'].strip()
            
            # Try to parse JSON response
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response as JSON")
                return {
                    "is_command": False,
                    "command_type": "other",
                    "explanation": "Could not understand command structure"
                }
                
        except Exception as e:
            logger.error(f"Error generating dynamic response: {e}")
            return {"status": "error", "message": str(e)}


# Standalone test function
def test_interpreter():
    """Test the command interpreter with sample commands."""
    interpreter = CommandInterpreter()
    
    test_commands = [
        "Open Safari browser",
        "Maximize my window",
        "Move this window to the left",
        "I want to focus on my terminal",
        "Type hello world",
        "Can you resize this window to make it smaller?"
    ]
    
    for cmd in test_commands:
        print(f"\nTesting: '{cmd}'")
        command, args = interpreter.interpret_command(cmd)
        print(f"Interpreted as: {command} {args}")
        
        # Test dynamic response
        response = interpreter.generate_dynamic_response(cmd)
        print(f"Dynamic response: {json.dumps(response, indent=2)}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Run test
    test_interpreter()