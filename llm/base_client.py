"""Abstract base class for LLM vision clients.

All LLM clients must implement extract_from_image() which takes
an image as bytes and returns a list of extracted plan dicts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Raw response from an LLM API call."""

    content: str
    input_tokens: int
    output_tokens: int
    model: str


class BaseLLMClient(ABC):
    """Abstract LLM client for vision-based data extraction."""

    provider: str
    model: str

    @abstractmethod
    def extract_from_image(
        self,
        image_bytes: bytes,
        prompt: str,
    ) -> LLMResponse:
        """Send an image to the LLM and get the raw text response.

        Args:
            image_bytes: PNG/JPEG image as bytes.
            prompt: The extraction prompt with schema instructions.

        Returns:
            LLMResponse with content, token counts, and model name.
        """
        ...

    @abstractmethod
    def extract_from_text(
        self,
        text: str,
        prompt: str,
    ) -> LLMResponse:
        """Send text (e.g. HTML diff) to the LLM and get the raw text response.

        Args:
            text: Input text content.
            prompt: The extraction prompt with schema instructions.

        Returns:
            LLMResponse with content, token counts, and model name.
        """
        ...
