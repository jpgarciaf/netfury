"""OpenAI GPT-4o client for vision-based extraction."""

from __future__ import annotations

import base64

import openai

from llm.base_client import BaseLLMClient, LLMResponse
from settings import get_settings


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI GPT-4o and GPT-4o-mini models."""

    provider = "openai"

    def __init__(self, model: str | None = None) -> None:
        cfg = get_settings()
        self.model = model or cfg.llm_model
        self._client = openai.OpenAI(api_key=cfg.openai_api_key)

    def extract_from_image(
        self,
        image_bytes: bytes,
        prompt: str,
    ) -> LLMResponse:
        """Send image to GPT-4o and get extraction response.

        Args:
            image_bytes: PNG/JPEG screenshot bytes.
            prompt: Structured extraction prompt.

        Returns:
            LLMResponse with extracted text and token usage.
        """
        b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}",
                                "detail": "high",
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

        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=self.model,
        )
