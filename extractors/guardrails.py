"""Input sanitization and output validation for LLM responses.

Provides guardrails against prompt injection and ensures LLM output
conforms to the expected PlanISP schema.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from pydantic import ValidationError

from schemas.plan import AdditionalService, PlanISP
from settings import ISP_COMPANY_MAP

logger = logging.getLogger(__name__)

# Fields that the LLM should NOT return (auto-computed or set by us)
_FORBIDDEN_OUTPUT_KEYS = {
    "fecha", "anio", "mes", "dia", "empresa", "marca",
}

# Maximum expected plans per page (sanity check)
_MAX_PLANS_PER_PAGE = 50


def sanitize_input(text: str) -> str:
    """Remove potentially dangerous content from text before sending to LLM.

    Args:
        text: Raw text content (HTML fragments, etc.).

    Returns:
        Sanitized text with script tags and suspicious patterns removed.
    """
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(
        r"(ignore\s+(previous|above|all)\s+instructions)",
        "[REDACTED]",
        text,
        flags=re.IGNORECASE,
    )
    return text


def parse_llm_response(raw: str) -> list[dict]:
    """Parse raw LLM response into a list of plan dicts.

    Handles markdown code fences, extra whitespace, and common
    LLM output quirks.

    Args:
        raw: Raw text from the LLM response.

    Returns:
        List of plan dictionaries.

    Raises:
        ValueError: If the response cannot be parsed as JSON.
    """
    cleaned = raw.strip()

    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Try to find JSON array within the response
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Could not parse JSON from LLM response: {e}")

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        raise ValueError(f"Expected list, got {type(data).__name__}")

    if len(data) > _MAX_PLANS_PER_PAGE:
        logger.warning(
            "LLM returned %d plans (max expected %d), truncating",
            len(data), _MAX_PLANS_PER_PAGE,
        )
        data = data[:_MAX_PLANS_PER_PAGE]

    return data


def validate_and_build_plans(
    raw_plans: list[dict],
    isp_key: str,
    extraction_time: datetime | None = None,
) -> tuple[list[PlanISP], list[str]]:
    """Validate raw plan dicts and build PlanISP objects.

    Adds empresa, marca, fecha, and other auto-computed fields.

    Args:
        raw_plans: List of dicts from LLM response.
        isp_key: ISP identifier (e.g., "xtrim").
        extraction_time: Override for fecha (defaults to now).

    Returns:
        Tuple of (valid plans, error messages).
    """
    now = extraction_time or datetime.now()
    empresa = ISP_COMPANY_MAP.get(isp_key, isp_key.upper())
    marca = isp_key.capitalize()
    valid: list[PlanISP] = []
    errors: list[str] = []

    for i, raw in enumerate(raw_plans):
        try:
            # Inject required fields
            raw["fecha"] = now.isoformat()
            raw["empresa"] = empresa
            raw["marca"] = marca

            # Convert pys_adicionales_detalle if present
            if "pys_adicionales_detalle" in raw and raw["pys_adicionales_detalle"]:
                detail = raw["pys_adicionales_detalle"]
                if isinstance(detail, dict):
                    converted = {}
                    for k, v in detail.items():
                        key = _to_snake_case(k)
                        if isinstance(v, dict):
                            converted[key] = AdditionalService(**v)
                        else:
                            converted[key] = v
                    raw["pys_adicionales_detalle"] = converted

            plan = PlanISP(**raw)
            valid.append(plan)

        except (ValidationError, TypeError, ValueError) as e:
            msg = f"Plan {i}: {e}"
            logger.warning(msg)
            errors.append(msg)

    return valid, errors


def count_non_null_fields(plan: PlanISP) -> int:
    """Count non-null fields in a PlanISP instance.

    Args:
        plan: A validated PlanISP object.

    Returns:
        Number of fields that have non-null, non-empty values.
    """
    count = 0
    for field_name in PlanISP.model_fields:
        value = getattr(plan, field_name)
        if value is not None and value != "" and value != [] and value != {}:
            count += 1
    return count


def _to_snake_case(name: str) -> str:
    """Convert a string to snake_case.

    Args:
        name: Input string (e.g., "Disney Plus", "disney+").

    Returns:
        snake_case version (e.g., "disney_plus").
    """
    s = name.lower().strip()
    s = re.sub(r"[+]", "_plus", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    return s
