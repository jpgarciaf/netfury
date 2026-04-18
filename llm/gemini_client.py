"""Google Gemini client for vision-based extraction."""

from __future__ import annotations

from google import genai
from google.genai import types

from llm.base_client import BaseLLMClient, LLMResponse
from settings import get_settings


class GeminiClient(BaseLLMClient):
    """Client for Google Gemini 2.0 Flash model."""

    provider = "google"

    def __init__(self, model: str | None = None) -> None:
        cfg = get_settings()
        self.model = model or cfg.llm_model
        self._client = genai.Client(api_key=cfg.google_api_key)

    def extract_from_image(
        self,
        image_bytes: bytes,
        prompt: str,
    ) -> LLMResponse:
        """Send image to Gemini and get extraction response.

        Args:
            image_bytes: PNG/JPEG screenshot bytes.
            prompt: Structured extraction prompt.

        Returns:
            LLMResponse with extracted text and token usage.
        """
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png",
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=[image_part, prompt],
        )

        usage = response.usage_metadata
        return LLMResponse(
            content=response.text or "",
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
            model=self.model,
        )
