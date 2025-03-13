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

        # Get server URL from environment or config
        from src.config.config import config
        self.server_url = os.getenv("LLM_SERVER_URL", config.get("LLM_SERVER_URL", "http://192.168.191.55:7860"))
        self.model_name = os.getenv("LLM_MODEL_NAME", config.get("LLM_MODEL_NAME", "unsloth/QwQ-32B-GGUF:Q4_K_M"))
        self.api_key = os.getenv("OPENWEBUI_API_KEY", "")
        
        # For backward compatibility
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.llm_server_available = False
        self.available_commands = self._load_available_commands()
        self.model_type = "qwen"  # Default to qwen-style prompting for the QwQ model

        # Load the model
        self._load_model()

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

    def _load_model(self):
        """Check connection to the LLM server."""
        try:
            # Test the server connection with a ping
            logger.info(f"Connecting to LLM server at {self.server_url}")
            
            # Check if server is responsive using the OpenAI models endpoint with API key
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = requests.get(f"{self.server_url}/v1/models", headers=headers, timeout=5)
                
                if response.status_code == 200:
                    self.llm_server_available = True
                    logger.info("Successfully connected to LLM server with OpenAI-compatible API")
                    logger.info(f"Using model: {self.model_name}")
                    return True
                else:
                    # Fall back to just checking if the server is up by hitting the root URL
                    logger.info(f"OpenAI models endpoint not available ({response.status_code}), trying root URL")
                    response = requests.get(self.server_url, timeout=5)
                    if response.status_code == 200:
                        self.llm_server_available = True
                        logger.info("Successfully connected to LLM server")
                        logger.info(f"Using model: {self.model_name}")
                        return True
                    else:
                        logger.error(f"LLM server responded with status code: {response.status_code}")
                        self.llm_server_available = False
                        return False
            except requests.exceptions.RequestException as e:
                raise e  # Re-raise to be caught by the outer exception handler
            
            # If we get here, the first request succeeded but returned a non-200 status
            logger.error(f"LLM server responded with status code: {response.status_code}")
            self.llm_server_available = False
            return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to LLM server: {e}")
            logger.warning("Will fall back to simple command extraction")
            self.llm_server_available = False
            return False

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

        # Select the appropriate prompt template based on model type
        if self.model_type == "qwen":
            template = self._get_qwen_prompt_template(commands_list, text)
        elif self.model_type == "deepseek":
            template = self._get_deepseek_prompt_template(commands_list, text)
        else:
            # Default/Llama-style prompt
            template = self._get_llama_prompt_template(commands_list, text)

        # Try multiple API formats (Text Generation Web UI, Gradio, etc.)
        try:
            # Try OpenAI-compatible API with the API key
            try:
                logger.info("Trying OpenAI-compatible API")
                openai_headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                openai_payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": "You are a voice command interpreter for Mac OS X that converts natural language into structured commands."},
                        {"role": "user", "content": f"Available commands:\n{commands_list}\n\nUser input: {text}\n\nExtract the command and arguments in this format:\nCOMMAND: [command]\nARGS: [comma-separated args]"}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 128
                }
                
                response = requests.post(
                    f"{self.server_url}/v1/chat/completions",
                    headers=openai_headers,
                    json=openai_payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        response_text = response_data["choices"][0]["message"]["content"].strip()
                        logger.debug(f"LLM response (OpenAI): {response_text}")
                        return response_text
                    else:
                        raise Exception("Unexpected response format from OpenAI API")
            except Exception as e:
                logger.info(f"OpenAI-compatible API not available: {e}")
                
            # 1. Try Text Generation Web UI format
            try:
                logger.info("Trying Text Generation Web UI API")
                tgwui_payload = {
                    "prompt": template,
                    "max_new_tokens": 128,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "stop": ["Input:", "\n\n", "User:"],
                    "seed": -1,
                    "stream": False
                }
                
                response = requests.post(
                    f"{self.server_url}/api/v1/generate",
                    json=tgwui_payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    # Parse Text Generation Web UI response
                    response_data = response.json()
                    if "results" in response_data and len(response_data["results"]) > 0:
                        response_text = response_data["results"][0].get("text", "").strip()
                        logger.debug(f"LLM response (TGWUI): {response_text}")
                        return response_text
                    else:
                        raise Exception("Unexpected response format from Text Generation Web UI API")
            except Exception as e:
                logger.info(f"Text Generation Web UI API not available: {e}")
            
            # 2. Try Gradio API
            try:
                logger.info("Trying Gradio API")
                gradio_payload = {
                    "data": [
                        template,  # prompt
                        0.1,       # temperature
                        128,       # max_tokens
                        0.9,       # top_p
                    ]
                }
                
                response = requests.post(
                    f"{self.server_url}/run/predict",  # Alternate Gradio endpoint
                    json=gradio_payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    # Parse Gradio response
                    response_data = response.json()
                    if "data" in response_data and len(response_data["data"]) > 0:
                        response_text = str(response_data["data"][0]).strip()
                        logger.debug(f"LLM response (Gradio): {response_text}")
                        return response_text
                    else:
                        raise Exception("Unexpected response format from Gradio API")
            except Exception as e:
                logger.info(f"Gradio API not available: {e}")
            
            # 3. Try standard Gradio API
            try:
                logger.info("Trying standard Gradio endpoint")
                gradio_payload = {
                    "fn_index": 0,  # Usually the main interface is at index 0
                    "data": [template],
                }
                
                response = requests.post(
                    f"{self.server_url}/api/predict",
                    json=gradio_payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if "data" in response_data:
                        response_text = str(response_data["data"]).strip()
                        logger.debug(f"LLM response (Standard Gradio): {response_text}")
                        return response_text
                    else:
                        raise Exception("Unexpected response format from Standard Gradio API")
            except Exception as e:
                logger.info(f"Standard Gradio API not available: {e}")
            
            # If we've tried all APIs and none worked, raise an exception
            logger.error("All API endpoints failed")
            raise Exception("No compatible API endpoint found on the server")
        
        except Exception as e:
            logger.error(f"Error interpreting command with LLM: {e}")
            # Fall back to simple command extraction
            parts = text.lower().strip().split()
            if not parts:
                return ("", [])
            return (parts[0], parts[1:])
            
        # If we get a response, process it to extract command and args    
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

        # Select appropriate prompt based on model type
        if self.model_type == "qwen":
            prompt = self._get_qwen_dynamic_prompt(transcription)
        elif self.model_type == "deepseek":
            prompt = self._get_deepseek_dynamic_prompt(transcription)
        else:
            prompt = self._get_llama_dynamic_prompt(transcription)

        try:
            # Try OpenAI-compatible API first
            try:
                logger.info("Trying OpenAI-compatible API for dynamic response")
                openai_headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                openai_payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": "You are a voice command analyzer for Mac OS X that determines if inputs are commands and how to process them."},
                        {"role": "user", "content": f"Analyze this user input: '{transcription}'\n\nRespond with a JSON object containing is_command (boolean), command_type, action, parameters, and explanation fields."}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 512
                }
                
                response = requests.post(
                    f"{self.server_url}/v1/chat/completions",
                    headers=openai_headers,
                    json=openai_payload,
                    timeout=15
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        response_text = response_data["choices"][0]["message"]["content"].strip()
                        logger.debug(f"Dynamic response (OpenAI): {response_text}")
                    else:
                        raise Exception("Unexpected response format from OpenAI API")
                else:
                    raise Exception(f"OpenAI API returned status code {response.status_code}")
            except Exception as e:
                logger.info(f"OpenAI-compatible API not available for dynamic response: {e}")
                
                # Fall back to Text Generation Web UI format
                logger.info("Trying Text Generation Web UI for dynamic response")
                tgwui_payload = {
                    "prompt": prompt,
                    "max_new_tokens": 512,
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "stop": ["```", "User:", "<human>"],
                    "seed": -1,
                    "stream": False
                }
                
                response = requests.post(
                    f"{self.server_url}/api/v1/generate",
                    json=tgwui_payload,
                    timeout=15
                )
            
            if response.status_code == 200:
                # Parse Text Generation Web UI response
                response_data = response.json()
                if "results" in response_data and len(response_data["results"]) > 0:
                    response_text = response_data["results"][0].get("text", "").strip()
                    logger.debug(f"Dynamic response (TGWUI): {response_text}")
                else:
                    raise Exception("Unexpected response format from Text Generation Web UI API")
            else:
                # Try Gradio format
                logger.info(f"Text Generation Web UI API not available, trying Gradio API")
                gradio_payload = {
                    "data": [
                        prompt,     # prompt
                        0.2,        # temperature
                        512,        # max_tokens
                        0.9,        # top_p
                    ]
                }
                
                response = requests.post(
                    f"{self.server_url}/run/predict",  # Alternate Gradio endpoint
                    json=gradio_payload,
                    timeout=15
                )
                
                if response.status_code != 200:
                    logger.error(f"LLM server error: {response.status_code} - {response.text}")
                    raise Exception(f"LLM server returned status code {response.status_code}")
                
                # Parse Gradio response
                response_data = response.json()
                if "data" in response_data and len(response_data["data"]) > 0:
                    response_text = str(response_data["data"][0]).strip()
                    logger.debug(f"Dynamic response (Gradio): {response_text}")
                else:
                    raise Exception("Unexpected response format from Gradio API")
            
            if response.status_code != 200:
                logger.error(f"LLM server error: {response.status_code} - {response.text}")
                raise Exception(f"LLM server returned status code {response.status_code}")
                
            # Parse the Gradio response format
            response_data = response.json()
            # Gradio returns data in a format like {"data": [generated_text]}
            if "data" in response_data and isinstance(response_data["data"], list) and len(response_data["data"]) > 0:
                response_text = str(response_data["data"][0]).strip()
            else:
                logger.error(f"Unexpected response format: {response_data}")
                raise Exception("Unexpected response format from Gradio API")

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
