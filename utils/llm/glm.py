"""
GLM (Zhipu AI) client for DeepDel.

This module provides a client for interacting with Zhipu AI's GLM models.
"""

import json
from typing import Optional

import requests

from utils.llm.base import BaseLLM


class GLMClient(BaseLLM):
    """
    Client for Zhipu AI's GLM models.

    This client interacts with the GLM API for AI-powered folder analysis.

    Attributes:
        API_URL: The GLM API endpoint for chat completions.
    """

    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(
        self,
        api_key: str = "",
        model: str = "glm-4-flash",
        timeout: int = 10
    ):
        """
        Initialize the GLM client.

        Args:
            api_key: The API key for authentication.
            model: The model to use (default: glm-4-flash).
            timeout: Request timeout in seconds (default: 10).
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def chat(self, message: str, system_prompt: str = None) -> Optional[str]:
        """
        Send a chat message to the GLM API and get a response.

        Args:
            message: The user message to send.
            system_prompt: Optional system prompt to set context.

        Returns:
            The model's response as a string, or None if the request fails.
        """
        if not self.is_available():
            return None

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content")
            return None

        except requests.RequestException:
            return None
        except json.JSONDecodeError:
            return None

    def is_available(self) -> bool:
        """
        Check if the GLM client is properly configured.

        Returns:
            True if the API key is set, False otherwise.
        """
        return bool(self.api_key and self.api_key.strip())
