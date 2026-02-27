"""
Base LLM abstract class for DeepDel.

This module defines the abstract interface for LLM clients.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLM(ABC):
    """
    Abstract base class for LLM clients.

    All LLM implementations (GLM, OpenAI, etc.) should inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    def chat(self, message: str, system_prompt: str = None) -> Optional[str]:
        """
        Send a chat message to the LLM and get a response.

        Args:
            message: The user message to send to the LLM.
            system_prompt: Optional system prompt to set the context.

        Returns:
            The LLM's response as a string, or None if the request fails.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM client is properly configured and available.

        Returns:
            True if the client can make requests, False otherwise.
        """
        pass
