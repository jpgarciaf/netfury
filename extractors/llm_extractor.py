"""LLM vision-based extraction strategy.

Sends screenshots to a configured LLM model and extracts structured
ISP plan data. Supports multiple providers via factory pattern.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from extractors.guardrails import (
    count_non_null_fields,
    parse_llm_response,
    validate_and_build_plans,
)
from extractors.prompt_templates import build_extraction_prompt
from llm.base_client import BaseLLMClient
from llm.claude_client import ClaudeClient
from llm.cost_tracker import CostTracker
from llm.gemini_client import GeminiClient
from llm.local_client import LocalClient
from llm.openai_client import OpenAIClient
from schemas.plan import PlanISP

logger = logging.getLogger(__name__)

# Model -> provider mapping for the factory
_MODEL_PROVIDER_MAP: dict[str, str] = {
    "claude-sonnet-4-20250514": "anthropic",
    "claude-haiku-4-5-20251001": "anthropic",
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gemini-2.0-flash": "google",
    "llava:13b": "local",
    "moondream": "local",
}


def get_client(model: str) -> BaseLLMClient:
    """Factory: create the appropriate LLM client for a model.

    Args:
        model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-20250514").

    Returns:
        An instantiated LLM client.

    Raises:
        ValueError: If the model is not recognized.
    """
    provider = _MODEL_PROVIDER_MAP.get(model)
    if provider is None:
        # Try to infer provider from model name
        if "claude" in model or "haiku" in model or "sonnet" in model:
            provider = "anthropic"
        elif "gpt" in model:
            provider = "openai"
        elif "gemini" in model:
            provider = "google"
        else:
            provider = "local"

    clients: dict[str, type[BaseLLMClient]] = {
        "anthropic": ClaudeClient,
        "openai": OpenAIClient,
        "google": GeminiClient,
        "local": LocalClient,
    }
    client_cls = clients[provider]
    return client_cls(model=model)


def extract_plans_from_image(
    image_bytes: bytes,
    isp_key: str,
    marca: str,
    model: str,
    *,
    image_path: str | None = None,
) -> tuple[list[PlanISP], list[str]]:
    """Extract ISP plans from a screenshot using an LLM.

    Args:
        image_bytes: PNG/JPEG screenshot bytes.
        isp_key: ISP identifier (e.g., "xtrim").
        marca: Brand name (e.g., "Xtrim").
        model: LLM model to use.
        image_path: Optional path for cost tracking.

    Returns:
        Tuple of (valid PlanISP list, error messages).
    """
    tracker = CostTracker()
    client = get_client(model)
    prompt = build_extraction_prompt(isp_key, marca)
    now = datetime.now()

    start_ms = int(time.time() * 1000)
    try:
        response = client.extract_from_image(image_bytes, prompt)
        latency_ms = int(time.time() * 1000) - start_ms

        raw_plans = parse_llm_response(response.content)
        plans, errors = validate_and_build_plans(raw_plans, isp_key, now)

        # Compute average field coverage
        avg_fields = 0
        if plans:
            avg_fields = sum(
                count_non_null_fields(p) for p in plans
            ) // len(plans)

        total_fields = len(PlanISP.model_fields)

        tracker.record(
            provider=client.provider,
            model=model,
            isp=isp_key,
            image_size_bytes=len(image_bytes),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=latency_ms,
            extraction_success=len(plans) > 0,
            fields_extracted=avg_fields,
            fields_total=total_fields,
            plans_extracted=len(plans),
            image_path=image_path,
        )

        logger.info(
            "Extracted %d plans from %s using %s (%.1fs, $%.6f)",
            len(plans), isp_key, model,
            latency_ms / 1000, tracker.records[-1].cost_usd,
        )
        return plans, errors

    except Exception as e:
        latency_ms = int(time.time() * 1000) - start_ms
        logger.error("LLM extraction failed for %s: %s", isp_key, e)

        tracker.record(
            provider=client.provider,
            model=model,
            isp=isp_key,
            image_size_bytes=len(image_bytes),
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
            extraction_success=False,
            fields_extracted=0,
            fields_total=len(PlanISP.model_fields),
            plans_extracted=0,
            image_path=image_path,
        )
        return [], [str(e)]
