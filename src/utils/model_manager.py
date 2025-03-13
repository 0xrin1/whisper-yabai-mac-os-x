#!/usr/bin/env python3
"""
Model manager for discovering and managing available language models.
Provides unified interface for listing and selecting models from various providers.
"""

import os
import sys
import json
import logging
import requests
from typing import Dict, Any, List, Optional

# Import our modules
from src.config.config import config
from src.utils.llm_client import LLMClient

# Configure logging
logger = logging.getLogger("model-manager")


class ModelManager:
    """
    Manages the discovery and selection of available language models.
    Supports multiple model providers and API formats.
    """

    def __init__(self):
        """Initialize the model manager."""
        # Get server details from environment or config
        self.server_url = os.getenv("LLM_SERVER_URL", config.get("LLM_SERVER_URL", "http://192.168.191.55:7860"))
        self.api_key = os.getenv("OPENWEBUI_API_KEY", "")

        # Get available models
        self.llm_client = LLMClient(self.server_url, api_key=self.api_key)
        self.available_models = []
        self.refresh_models()

    def refresh_models(self) -> List[Dict[str, Any]]:
        """
        Refresh the list of available models.

        Returns:
            List of available model information dictionaries
        """
        self.available_models = []

        # Try specialized API endpoints first
        if self.llm_client.server_available:
            try:
                # Get models using the LLM client
                models = self.llm_client.list_models()
                if models:
                    self.available_models = models
                    return self.available_models
            except Exception as e:
                logger.warning(f"Error getting models from primary API: {e}")

        # Try multiple endpoints as fallback
        endpoints_to_try = [
            ("/ollama/api/tags", "models", self._extract_ollama_models),
            ("/api/models", None, self._extract_generic_models),
            ("/v1/models", "data", self._extract_openai_models),
            ("/api/ollama/tags", "models", self._extract_ollama_models),
        ]

        for endpoint, key, extractor in endpoints_to_try:
            try:
                url = f"{self.server_url}{endpoint}"

                # Set up headers with authentication
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
                }

                # Make request
                response = requests.get(url, headers=headers, timeout=5)

                # If successful, extract models
                if response.status_code == 200:
                    response_data = response.json()

                    # Extract models using the appropriate extractor
                    models = []
                    if key is not None and key in response_data:
                        models = extractor(response_data[key])
                    else:
                        models = extractor(response_data)

                    if models:
                        self.available_models = models
                        return self.available_models

            except Exception as e:
                logger.debug(f"Error trying endpoint {endpoint}: {e}")

        logger.warning("Could not find any models from any endpoint")
        return self.available_models

    def _extract_ollama_models(self, models_data: Any) -> List[Dict[str, Any]]:
        """Extract models from Ollama API response."""
        result = []

        if isinstance(models_data, list):
            for model in models_data:
                if isinstance(model, dict):
                    model_info = {
                        "id": model.get("name", "unknown"),
                        "name": model.get("name", "unknown"),
                        "provider": "ollama",
                        "size": model.get("size", 0),
                        "modified_at": model.get("modified_at", ""),
                    }
                    result.append(model_info)

        return result

    def _extract_openai_models(self, models_data: Any) -> List[Dict[str, Any]]:
        """Extract models from OpenAI API response."""
        result = []

        if isinstance(models_data, list):
            for model in models_data:
                if isinstance(model, dict):
                    model_info = {
                        "id": model.get("id", "unknown"),
                        "name": model.get("id", "unknown"),
                        "provider": "openai",
                        "created": model.get("created", 0),
                        "owned_by": model.get("owned_by", "unknown"),
                    }
                    result.append(model_info)

        return result

    def _extract_generic_models(self, data: Any) -> List[Dict[str, Any]]:
        """Extract models from generic API response."""
        result = []

        # Try to handle various response formats
        if isinstance(data, dict):
            # Check for various fields that might contain models
            for field in ["models", "data", "results", "available_models"]:
                if field in data and isinstance(data[field], list):
                    for model in data[field]:
                        if isinstance(model, dict):
                            # Try various field names that might contain the model name
                            name = model.get("name", model.get("id", model.get("model", "unknown")))
                            model_info = {
                                "id": model.get("id", name),
                                "name": name,
                                "provider": "unknown",
                            }
                            result.append(model_info)
                    if result:
                        return result

            # If no models found in known fields, try to extract from the raw data
            if "name" in data:
                return [{"id": data.get("id", data["name"]), "name": data["name"], "provider": "unknown"}]

        elif isinstance(data, list):
            # Direct list of models
            for item in data:
                if isinstance(item, dict) and "name" in item:
                    model_info = {
                        "id": item.get("id", item["name"]),
                        "name": item["name"],
                        "provider": "unknown",
                    }
                    result.append(model_info)
                elif isinstance(item, str):
                    model_info = {
                        "id": item,
                        "name": item,
                        "provider": "unknown",
                    }
                    result.append(model_info)

        return result

    def get_models(self) -> List[Dict[str, Any]]:
        """
        Get the list of available models.

        Returns:
            List of model information dictionaries
        """
        if not self.available_models:
            self.refresh_models()
        return self.available_models

    def get_model_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a model by its name.

        Args:
            name: The name of the model to find

        Returns:
            Model information dictionary or None if not found
        """
        if not self.available_models:
            self.refresh_models()

        # Exact match
        for model in self.available_models:
            if model["name"] == name or model["id"] == name:
                return model

        # Partial match
        name_lower = name.lower()
        for model in self.available_models:
            model_name = model["name"].lower()
            model_id = model["id"].lower()
            if name_lower in model_name or name_lower in model_id:
                return model

        return None


# Standalone test
if __name__ == "__main__":
    # Set up logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create model manager
    manager = ModelManager()

    # Print server information
    print(f"Server URL: {manager.server_url}")
    print(f"API Key: {manager.api_key[:4]}...{manager.api_key[-4:] if len(manager.api_key) > 8 else ''}")

    # Print available models
    models = manager.get_models()
    if models:
        print("\nAvailable models:")
        for i, model in enumerate(models):
            print(f"{i+1}. {model['name']} (ID: {model['id']}, Provider: {model.get('provider', 'unknown')})")
    else:
        print("\nNo models found")

    # Test looking up a model
    model_name = os.getenv("LLM_MODEL_NAME", config.get("LLM_MODEL_NAME", "unsloth/QwQ-32B-GGUF:Q4_K_M"))
    print(f"\nLooking up model: {model_name}")
    model = manager.get_model_by_name(model_name)
    if model:
        print(f"Found model: {json.dumps(model, indent=2)}")
    else:
        print(f"Model not found: {model_name}")
