#!/usr/bin/env python3
"""
Unified LLM client for connecting to language model APIs.
Abstracts API endpoint discovery and communication for different LLM providers.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List, Union

# Configure logging
logger = logging.getLogger("llm-client")


class LLMClient:
    """
    Base client for communicating with language model APIs.
    Provides automatic endpoint discovery and unified interface for different API formats.
    """

    def __init__(self, server_url: Optional[str] = None, model_name: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the LLM client with server details.

        Args:
            server_url: URL of the LLM server
            model_name: Name of the model to use
            api_key: API key for authentication
        """
        # Get server details from environment or config
        from src.config.config import config
        self.server_url = server_url or os.getenv("LLM_SERVER_URL", config.get("LLM_SERVER_URL", "http://192.168.191.55:7860"))
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME", config.get("LLM_MODEL_NAME", "unsloth/QwQ-32B-GGUF:Q4_K_M"))
        self.api_key = api_key or os.getenv("OPENWEBUI_API_KEY", "")

        # Initialize state
        self.server_available = False
        self.api_format = None
        self.model_type = self._determine_model_type()

        # Test connection to find working API format
        self.check_connection()

    def _determine_model_type(self) -> str:
        """
        Determine the model type based on the model name.

        Returns:
            String identifying the model architecture
        """
        model_lower = self.model_name.lower()

        if "qwen" in model_lower:
            return "qwen"
        elif "deepseek" in model_lower:
            return "deepseek"
        elif "llama" in model_lower or "mistral" in model_lower:
            return "llama"
        else:
            # Default to llama-style models
            return "llama"

    def check_connection(self) -> bool:
        """
        Check connection to the LLM server and discover working API format.

        Returns:
            True if a working API endpoint was found, False otherwise
        """
        logger.info(f"Connecting to LLM server at {self.server_url}")

        # Try OpenAI-compatible API first
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(f"{self.server_url}/v1/models", headers=headers, timeout=5)

            if response.status_code == 200:
                self.server_available = True
                self.api_format = "openai"
                logger.info("Successfully connected to LLM server with OpenAI-compatible API")
                logger.info(f"Using model: {self.model_name}")
                return True
        except requests.exceptions.RequestException as e:
            logger.info(f"OpenAI-compatible API check failed: {e}")

        # Try Ollama API format
        try:
            ollama_url = f"{self.server_url}/ollama/api/tags"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
            }

            response = requests.get(ollama_url, headers=headers, timeout=5)

            if response.status_code == 200:
                self.server_available = True
                self.api_format = "ollama"
                logger.info("Successfully connected to LLM server with Ollama API")
                logger.info(f"Using model: {self.model_name}")
                return True
        except requests.exceptions.RequestException as e:
            logger.info(f"Ollama API check failed: {e}")

        # Try Text Generation Web UI format
        try:
            tgwui_url = f"{self.server_url}/api/v1/model"
            response = requests.get(tgwui_url, timeout=5)

            if response.status_code == 200:
                self.server_available = True
                self.api_format = "tgwui"
                logger.info("Successfully connected to LLM server with Text Generation Web UI API")
                logger.info(f"Using model: {self.model_name}")
                return True
        except requests.exceptions.RequestException as e:
            logger.info(f"Text Generation Web UI API check failed: {e}")

        # If all specific API checks fail, try a simple connection to the root URL
        try:
            response = requests.get(self.server_url, timeout=5)
            if response.status_code == 200:
                self.server_available = True
                self.api_format = "unknown"
                logger.info("Successfully connected to LLM server (API format unknown)")
                logger.info(f"Using model: {self.model_name}")
                return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to LLM server: {e}")
            logger.warning("Will fall back to simple processing or default values")
            self.server_available = False
            return False

        # If we got here, none of the API formats worked
        self.server_available = False
        logger.error("Failed to find a compatible API format on the LLM server")
        return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 max_tokens: int = 128, temperature: float = 0.7,
                 stop_sequences: Optional[List[str]] = None) -> str:
        """
        Generate text using the LLM based on a prompt.

        Args:
            prompt: The user prompt to send to the model
            system_prompt: Optional system prompt/instruction
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for sampling (higher = more random)
            stop_sequences: Optional list of sequences that stop generation

        Returns:
            Generated text response
        """
        if not self.server_available:
            logger.warning("LLM server not available. Cannot generate text.")
            return ""

        stop_sequences = stop_sequences or ["User:", "Input:", "\n\n"]

        # Try the detected API format
        if self.api_format == "openai":
            return self._generate_openai(prompt, system_prompt, max_tokens, temperature, stop_sequences)
        elif self.api_format == "ollama":
            return self._generate_ollama(prompt, system_prompt, max_tokens, temperature, stop_sequences)
        elif self.api_format == "tgwui":
            return self._generate_tgwui(prompt, system_prompt, max_tokens, temperature, stop_sequences)
        else:
            # Try all formats sequentially as fallback
            try:
                return self._generate_openai(prompt, system_prompt, max_tokens, temperature, stop_sequences)
            except Exception as e:
                logger.info(f"OpenAI generation failed: {e}")

            try:
                return self._generate_ollama(prompt, system_prompt, max_tokens, temperature, stop_sequences)
            except Exception as e:
                logger.info(f"Ollama generation failed: {e}")

            try:
                return self._generate_tgwui(prompt, system_prompt, max_tokens, temperature, stop_sequences)
            except Exception as e:
                logger.info(f"TGWUI generation failed: {e}")

            logger.error("All generation methods failed")
            return ""

    def _generate_openai(self, prompt: str, system_prompt: Optional[str],
                        max_tokens: int, temperature: float,
                        stop_sequences: List[str]) -> str:
        """Generate text using OpenAI-compatible API format."""
        system_prompt = system_prompt or "You are a helpful assistant."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if stop_sequences:
            payload["stop"] = stop_sequences

        response = requests.post(
            f"{self.server_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            response_data = response.json()
            if "choices" in response_data and len(response_data["choices"]) > 0:
                response_text = response_data["choices"][0]["message"]["content"].strip()
                logger.debug(f"LLM response (OpenAI): {response_text[:100]}...")
                return response_text
            else:
                raise Exception("Unexpected response format from OpenAI API")
        else:
            raise Exception(f"OpenAI API returned status code {response.status_code}: {response.text}")

    def _generate_ollama(self, prompt: str, system_prompt: Optional[str],
                        max_tokens: int, temperature: float,
                        stop_sequences: List[str]) -> str:
        """Generate text using Ollama API format."""
        system_prompt = system_prompt or "You are a helpful assistant."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        # Extract exact model name that Ollama might use
        model_exact_name = self.model_name
        if "/" in model_exact_name:
            # Handle hf.co prefix for models
            model_exact_name = f"hf.co/{self.model_name}"

        payload = {
            "model": model_exact_name,
            "prompt": prompt,
            "system": system_prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": False
        }

        if stop_sequences:
            payload["options"]["stop"] = stop_sequences

        response = requests.post(
            f"{self.server_url}/ollama/api/generate",
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            response_data = json.loads(response.text.strip())
            if "response" in response_data:
                response_text = response_data["response"].strip()
                logger.debug(f"LLM response (Ollama): {response_text[:100]}...")
                return response_text
            else:
                raise Exception("Unexpected response format from Ollama API")
        else:
            raise Exception(f"Ollama API returned status code {response.status_code}: {response.text}")

    def _generate_tgwui(self, prompt: str, system_prompt: Optional[str],
                       max_tokens: int, temperature: float,
                       stop_sequences: List[str]) -> str:
        """Generate text using Text Generation Web UI API format."""
        full_prompt = prompt
        if system_prompt:
            if self.model_type == "qwen":
                full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n\n<|im_start|>user\n{prompt}<|im_end|>\n\n<|im_start|>assistant"
            elif self.model_type == "deepseek":
                full_prompt = f"<human>\n{system_prompt}\n\n{prompt}</human>\n\n<assistant>"
            else:
                full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "prompt": full_prompt,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "seed": -1,
            "stream": False
        }

        if stop_sequences:
            payload["stop"] = stop_sequences

        response = requests.post(
            f"{self.server_url}/api/v1/generate",
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            response_data = response.json()
            if "results" in response_data and len(response_data["results"]) > 0:
                response_text = response_data["results"][0].get("text", "").strip()
                logger.debug(f"LLM response (TGWUI): {response_text[:100]}...")
                return response_text
            else:
                raise Exception("Unexpected response format from Text Generation Web UI API")
        else:
            raise Exception(f"TGWUI API returned status code {response.status_code}: {response.text}")

    def list_models(self) -> List[Dict[str, Any]]:
        """
        Get a list of available models on the server.

        Returns:
            List of model information dictionaries
        """
        if not self.server_available:
            logger.warning("LLM server not available. Cannot list models.")
            return []

        # Try the detected API format
        if self.api_format == "openai":
            return self._list_models_openai()
        elif self.api_format == "ollama":
            return self._list_models_ollama()
        elif self.api_format == "tgwui":
            return self._list_models_tgwui()
        else:
            # Try all formats sequentially as fallback
            try:
                return self._list_models_openai()
            except Exception:
                pass

            try:
                return self._list_models_ollama()
            except Exception:
                pass

            try:
                return self._list_models_tgwui()
            except Exception:
                pass

            logger.error("Failed to list models from any API")
            return []

    def _list_models_openai(self) -> List[Dict[str, Any]]:
        """List models using OpenAI-compatible API format."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        response = requests.get(
            f"{self.server_url}/v1/models",
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            response_data = response.json()
            if "data" in response_data:
                return response_data["data"]
            else:
                return []
        else:
            raise Exception(f"OpenAI API returned status code {response.status_code}")

    def _list_models_ollama(self) -> List[Dict[str, Any]]:
        """List models using Ollama API format."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        response = requests.get(
            f"{self.server_url}/ollama/api/tags",
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            response_data = response.json()
            if "models" in response_data:
                return response_data["models"]
            else:
                return []
        else:
            raise Exception(f"Ollama API returned status code {response.status_code}")

    def _list_models_tgwui(self) -> List[Dict[str, Any]]:
        """List models using Text Generation Web UI API format."""
        response = requests.get(
            f"{self.server_url}/api/v1/model",
            timeout=5
        )

        if response.status_code == 200:
            return [{"id": "default", "name": response.json().get("result", "unknown")}]
        else:
            raise Exception(f"TGWUI API returned status code {response.status_code}")
