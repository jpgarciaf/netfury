"""Ollama local model client for vision-based extraction."""

from __future__ import annotations

import base64

import httpx

from llm.base_client import BaseLLMClient, LLMResponse
from settings import get_settings


class LocalClient(BaseLLMClient):
    """Client for Ollama local models (llava, moondream)."""

    provider = "local"

    def __init__(self, model: str | None = None) -> None:
        cfg = get_settings()
        self.model = model or cfg.llm_model
        self._base_url = cfg.ollama_base_url

    def extract_from_image(
        self,
        image_bytes: bytes,
        prompt: str,
    ) -> LLMResponse:
        """Send image to Ollama local model and get extraction response.

        Args:
            image_bytes: PNG/JPEG screenshot bytes.
            prompt: Structured extraction prompt.

        Returns:
            LLMResponse with extracted text (tokens estimated).
        """
        b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [b64_image],
            "stream": False,
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self._base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data.get("response", "")
        # Ollama provides token counts in some versions
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        return LLMResponse(
            content=content,
            input_tokens=prompt_eval_count,
            output_tokens=eval_count,
            model=self.model,
        )

    def extract_from_text(
        self,
        text: str,
        prompt: str,
    ) -> LLMResponse:
        """Send text to Ollama local model and get extraction response."""
        payload = {
            "model": self.model,
            "prompt": f"{prompt}\n\n{text}",
            "stream": False,
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self._base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data.get("response", "")
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        return LLMResponse(
            content=content,
            input_tokens=prompt_eval_count,
            output_tokens=eval_count,
            model=self.model,
        )
