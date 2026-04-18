"""Anthropic Claude client for vision-based extraction."""

from __future__ import annotations

import base64

import anthropic

from llm.base_client import BaseLLMClient, LLMResponse
from settings import get_settings


class ClaudeClient(BaseLLMClient):
    """Client for Anthropic Claude models (Sonnet, Haiku)."""

    provider = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        cfg = get_settings()
        self.model = model or cfg.llm_model
        self._client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

    def extract_from_image(
        self,
        image_bytes: bytes,
        prompt: str,
    ) -> LLMResponse:
        """Send image to Claude and get extraction response.

        Args:
            image_bytes: PNG/JPEG screenshot bytes.
            prompt: Structured extraction prompt.

        Returns:
            LLMResponse with extracted text and token usage.
        """
        b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

        message = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                },
            ],
        )

        return LLMResponse(
            content=message.content[0].text,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=self.model,
        )
