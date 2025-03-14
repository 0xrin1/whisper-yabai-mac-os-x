#!/usr/bin/env python3
"""
LLM-based interpreter for natural language commands.
Uses llama.cpp to run local language models for command processing.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List, Tuple

# Configure logging
logger = logging.getLogger("llm-interpreter")


class CommandInterpreter:
    """
    Interprets natural language commands using a local LLM.
    Translates speech into structured command actions.
    """

    def __init__(self, model_path: Optional[str] = None, n_ctx: int = 4096):
        """Initialize the LLM-based command interpreter."""

        # For backward compatibility
        self.model_path = model_path
        self.n_ctx = n_ctx

        # Use the unified LLM client
        from src.utils.llm_client import LLMClient
        self.llm_client = LLMClient()

        # Set properties based on LLM client
        self.server_url = self.llm_client.server_url
        self.model_name = self.llm_client.model_name
        self.api_key = self.llm_client.api_key
        self.llm_server_available = self.llm_client.server_available
        self.model_type = self.llm_client.model_type

        # Load available commands
        self.available_commands = self._load_available_commands()

    def _determine_model_type(self):
        """Determine the model type based on the filename."""
        model_filename = os.path.basename(self.model_path).lower()

        if "qwen" in model_filename:
            return "qwen"
        elif "deepseek" in model_filename:
            return "deepseek"
        elif "llama" in model_filename or "mistral" in model_filename:
            return "llama"
        else:
            # Default to llama-style models
            return "llama"

    def _determine_model_type(self):
        """Determine the model type based on the filename."""
        # This method is kept for backward compatibility
        # The actual model type detection is now handled by LLMClient
        return self.model_type

    def _load_available_commands(self) -> Dict[str, Any]:
        """Load available commands from commands.json."""
        try:
            with open("config/commands.json", "r") as f:
                commands_data = json.load(f)

            # Extract custom commands if present
            if "custom_commands" in commands_data:
                commands = commands_data["custom_commands"]
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
                "click": "Click the mouse at current position",
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
        if not self.llm_server_available:
            logger.warning("LLM server not available. Using simple command extraction.")
            # Fall back to simple command extraction (first word)
            parts = text.lower().strip().split()
            if not parts:
                return ("", [])
            return (parts[0], parts[1:])

        # Construct prompt with available commands
        commands_list = "\n".join(
            [f"- {cmd}: {desc}" for cmd, desc in self.available_commands.items()]
        )

        # Create system prompt and user prompt based on model type
        if self.model_type == "qwen":
            system_prompt = "You are a voice command interpreter for Mac OS X that converts natural language into structured commands."
            user_prompt = f"Available commands:\n{commands_list}\n\nUser input: \"{text}\"\n\nExtract the command and arguments in this format:\nCOMMAND: [command]\nARGS: [comma-separated args]"
        elif self.model_type == "deepseek":
            system_prompt = "You are a voice command interpreter for a Mac OS X system."
            user_prompt = f"Available commands:\n{commands_list}\n\nInput: \"{text}\"\n\nIf this is clearly a command, respond with:\nCOMMAND: [command name]\nARGS: [comma-separated arguments]\n\nIf this is not a command, respond with:\nCOMMAND: none\nARGS:"
        else:
            # Default/Llama-style prompt
            system_prompt = "You are a voice command interpreter for Mac OS X that converts natural language into structured commands."
            user_prompt = f"Available commands:\n{commands_list}\n\nConvert the following natural language input into a structured command and arguments ONLY if it's clearly a command. If not a command, respond with 'COMMAND: none'\n\nInput: \"{text}\"\n\nOutput format:\nCOMMAND: [command or 'none']\nARGS: [comma-separated arguments]"

        try:
            # Generate response using the unified LLM client
            response_text = self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=128,
                temperature=0.1,
                stop_sequences=["Input:", "\n\n", "User:"]
            )

            # Parse the response to extract command and arguments
            command = ""
            args = []

            for line in response_text.split("\n"):
                line = line.strip()
                if line.startswith("COMMAND:"):
                    command = line[8:].strip().lower()
                elif line.startswith("ARGS:"):
                    args_str = line[5:].strip()
                    if args_str:
                        args = [arg.strip() for arg in args_str.split(",")]

            logger.info(f"Interpreted command: {command}, args: {args}")
            return (command, args)

        except Exception as e:
            logger.error(f"Error interpreting command with LLM: {e}")
            # Fall back to simple command extraction
            parts = text.lower().strip().split()
            if not parts:
                return ("", [])
            return (parts[0], parts[1:])

    def _get_qwen_prompt_template(self, commands_list, text):
        """Get prompt template optimized for Qwen models."""
        return f"""<|im_start|>system
You are a voice command interpreter for a Mac OS X system that converts natural language into structured commands.

Available commands:
{commands_list}

Your task is to determine if the user input is clearly a command and extract the command and arguments.
Follow these rules:
1. If the input is not clearly a command, respond with "COMMAND: none"
2. If it is a command, extract the command and any arguments
3. Be precise and only return the command and arguments in the specified format
4. Commands must match one of the available commands exactly
<|im_end|>

<|im_start|>user
Interpret this user input: "{text}"
<|im_end|>

<|im_start|>assistant
COMMAND: [command or "none"]
ARGS: [arguments]
<|im_end|>"""

    def _get_deepseek_prompt_template(self, commands_list, text):
        """Get prompt template optimized for DeepSeek models."""
        return f"""<human>
You are a voice command interpreter for a Mac OS X system. I'll provide a voice input, and you need to determine if it's a command and extract the command and arguments.

Available commands:
{commands_list}

Input: "{text}"

If this is clearly a command, respond with:
COMMAND: [command name]
ARGS: [comma-separated arguments]

If this is not a command, respond with:
COMMAND: none
ARGS:

Be precise and match only to available commands.
</human>

<assistant>"""

    def _get_llama_prompt_template(self, commands_list, text):
        """Get prompt template for Llama-style models."""
        return f"""You are a voice command interpreter for a Mac OS X system.
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

    def generate_dynamic_response(self, transcription: str) -> Dict[str, Any]:
        """
        Generate a more dynamic response to an input that doesn't match any command.
        Returns a dictionary with potential actions or information.
        """
        if not self.llm_server_available:
            return {
                "status": "error",
                "message": "LLM server not available for dynamic responses",
            }

        # Create appropriate system prompt based on model type
        if self.model_type == "qwen":
            system_prompt = "You are a Mac OS voice assistant that determines if user inputs are computer commands."
            prompt = f"The user said: \"{transcription}\"\n\nAnalyze this and tell me if it's a computer command. If it is, determine what action and parameters are needed."
        elif self.model_type == "deepseek":
            system_prompt = "You are a Mac OS voice assistant that analyzes user input."
            prompt = f"Analyze this user voice input: \"{transcription}\"\n\nDetermine if this is intended as a computer command or just casual speech."
        else:
            system_prompt = "You are a Mac OS voice assistant."
            prompt = f"The user said: \"{transcription}\"\n\nDetermine if this input is clearly intended as a computer command or just casual speech."

        try:
            # Generate the response using the unified LLM client
            response_text = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=512,
                temperature=0.2,
                stop_sequences=["```", "User:", "<human>"]
            )

            # Try to parse JSON response
            try:
                # Extract JSON part from response
                response_text = response_text.strip()

                # Look for any JSON structure in the response
                if "{" in response_text and "}" in response_text:
                    # Find JSON start and end positions
                    start_pos = response_text.find("{")
                    end_pos = response_text.rfind("}") + 1
                    json_part = response_text[start_pos:end_pos]

                    # Remove any ```json or ``` markers if present
                    json_part = json_part.replace("```json", "").replace("```", "")

                    # Parse the JSON
                    try:
                        result = json.loads(json_part)
                        return result
                    except json.JSONDecodeError as e:
                        logger.warning(f"First JSON parsing attempt failed: {e}")
                        # Try to fix common JSON issues
                        fixed_json = self._fix_json_string(json_part)
                        result = json.loads(fixed_json)
                        return result
                else:
                    # Try to parse the whole text as JSON
                    try:
                        result = json.loads(response_text)
                        return result
                    except json.JSONDecodeError:
                        # If that fails, try to extract key-value pairs manually
                        return self._extract_key_values(response_text)
            except Exception as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                # Create a basic response
                return {
                    "is_command": False,
                    "command_type": "other",
                    "action": "none",
                    "explanation": "Could not parse response: " + str(e),
                }

        except Exception as e:
            logger.error(f"Error generating dynamic response: {e}")
            return {"status": "error", "message": str(e)}

    def _get_qwen_dynamic_prompt(self, transcription):
        """Get dynamic response prompt for Qwen models."""
        return f"""<|im_start|>system
You are a Mac OS voice assistant that determines if user inputs are computer commands. Analyze the input to see if it's intended to control the computer.

Respond with a JSON object containing your analysis.
<|im_end|>

<|im_start|>user
The user said: "{transcription}"

Analyze this and tell me if it's a computer command. If it is, determine what action and parameters are needed.
<|im_end|>

<|im_start|>assistant
```json
{{
  "is_command": true/false,
  "command_type": "application_control" or "system_control" or "information_request" or "other",
  "application": "name of application if relevant",
  "action": "specific action to take",
  "parameters": ["any", "needed", "parameters"],
  "explanation": "brief explanation of what you think the user wants"
}}
```
<|im_end|>"""

    def _get_deepseek_dynamic_prompt(self, transcription):
        """Get dynamic response prompt for DeepSeek models."""
        return f"""<human>
Analyze this user voice input: "{transcription}"

Determine if this is intended as a computer command (e.g., "open Safari", "maximize window") or just casual speech.
If it IS a command, extract the specific action and parameters needed.

Respond with a JSON object following this structure:
{{
  "is_command": true/false,
  "command_type": "application_control" or "system_control" or "information_request" or "other",
  "application": "name of application if relevant",
  "action": "specific action to take",
  "parameters": ["any", "needed", "parameters"],
  "explanation": "brief explanation of what you think the user wants"
}}

Be conservative - only mark inputs as commands if they are clearly instructions to control the computer.
</human>

<assistant>"""

    def _get_llama_dynamic_prompt(self, transcription):
        """Get dynamic response prompt for Llama-style models."""
        return f"""You are a Mac OS voice assistant. The user said: "{transcription}"

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

    def _fix_json_string(self, json_str):
        """Fix common JSON formatting issues in LLM responses."""
        # Remove any non-JSON text before or after
        if "{" in json_str and "}" in json_str:
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            json_str = json_str[start:end]

        # Fix missing quotes around keys
        import re

        json_str = re.sub(
            r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', json_str
        )

        # Fix single quotes to double quotes
        json_str = json_str.replace("'", '"')

        # Fix unquoted true/false/null values
        json_str = re.sub(r":\s*true\b", r":true", json_str)
        json_str = re.sub(r":\s*false\b", r":false", json_str)
        json_str = re.sub(r":\s*null\b", r":null", json_str)

        # Fix trailing commas
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)

        return json_str

    def _extract_key_values(self, text):
        """Extract key-value pairs from text when JSON parsing fails."""
        result = {
            "is_command": False,
            "command_type": "other",
            "action": "none",
            "parameters": [],
        }

        # Check if it looks like a command
        command_indicators = [
            "open",
            "maximize",
            "focus",
            "type",
            "move",
            "resize",
            "close",
        ]
        if any(indicator in text.lower() for indicator in command_indicators):
            result["is_command"] = True

            # Try to determine the action
            for indicator in command_indicators:
                if indicator in text.lower():
                    result["action"] = indicator
                    result["command_type"] = (
                        "application_control"
                        if indicator == "open"
                        else "system_control"
                    )
                    break

        # Look for application names
        app_indicators = [
            "safari",
            "chrome",
            "firefox",
            "terminal",
            "finder",
            "browser",
        ]
        for app in app_indicators:
            if app in text.lower():
                result["application"] = app
                break

        # Add explanation
        result["explanation"] = "Extracted from text: " + text[:100]

        return result


# Standalone test function
def test_interpreter():
    """Test the command interpreter with sample commands."""
    # Load config
    from src.config.config import config

    # Get server URL from environment or config
    server_url = os.getenv("LLM_SERVER_URL", config.get("LLM_SERVER_URL", "http://192.168.191.55:7860"))
    model_name = os.getenv("LLM_MODEL_NAME", config.get("LLM_MODEL_NAME", "unsloth/QwQ-32B-GGUF:Q4_K_M"))

    # Print server info
    print(f"Using LLM server at: {server_url}")
    print(f"Using model: {model_name}")

    interpreter = CommandInterpreter()

    # Make sure server connection is available
    if not interpreter.llm_server_available:
        print("ERROR: Failed to connect to LLM server. Please check the server URL.")
        return

    print(f"LLM server connection successful. Using model type: {interpreter.model_type}")

    test_commands = [
        "Open Safari browser",
        "Maximize my window",
        "Move this window to the left",
        "I want to focus on my terminal",
        "Type hello world",
        "Can you resize this window to make it smaller?",
    ]

    for cmd in test_commands:
        print(f"\n------------------------------")
        print(f"Testing: '{cmd}'")
        print(f"------------------------------")

        # Test command interpretation
        try:
            command, args = interpreter.interpret_command(cmd)
            print(f"Command: {command}")
            print(f"Arguments: {args}")
        except Exception as e:
            print(f"Error during command interpretation: {e}")
            continue

        # Test dynamic response separately to isolate any issues
        try:
            print("\nTesting dynamic response...")
            response = interpreter.generate_dynamic_response(cmd)

            # Check if response is valid
            if "is_command" in response:
                print(f"Is command: {response.get('is_command', False)}")
                print(f"Command type: {response.get('command_type', 'unknown')}")
                print(f"Action: {response.get('action', 'none')}")

                # Only print parameters if they exist
                params = response.get("parameters", [])
                if params:
                    print(f"Parameters: {params}")
            else:
                print("Invalid dynamic response format")
                print(f"Response: {response}")
        except Exception as e:
            print(f"Error during dynamic response: {e}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Run test
    test_interpreter()
