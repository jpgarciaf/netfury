"""Per-image LLM vision extraction with budget enforcement.

Sends individual banner images to the LLM for plan data extraction,
respecting configurable budget limits on calls, tokens, and cost.

Reuses existing LLM client factory and validation pipeline.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from extractors.guardrails import parse_llm_response, validate_and_build_plans
from extractors.prompt_image import build_image_extraction_prompt
from llm.budget import BudgetManager
from llm.cost_tracker import CostTracker
from schemas.plan import PlanISP
from scraper.image_discoverer import DiscoveredImage

logger = logging.getLogger(__name__)


def extract_plans_from_individual_images(
    images: list[DiscoveredImage],
    isp_key: str,
    marca: str,
    model: str,
    *,
    budget: BudgetManager | None = None,
) -> tuple[list[PlanISP], list[str]]:
    """Extract plans from individual banner images using LLM vision.

    Processes each image separately, checking budget before each call.
    Stops gracefully when budget is exhausted and returns partial results.

    Args:
        images: List of discovered images to analyze.
        isp_key: ISP identifier (e.g., "xtrim").
        marca: Brand name (e.g., "Xtrim").
        model: LLM model to use (e.g., "gpt-4o").
        budget: Optional budget manager for limiting API usage.

    Returns:
        Tuple of (valid PlanISP list, error messages).
    """
    from extractors.llm_extractor import get_client

    if not images:
        return [], []

    tracker = CostTracker()
    client = get_client(model)
    now = datetime.now()
    all_plans: list[PlanISP] = []
    all_errors: list[str] = []
    images_processed = 0

    for idx, image in enumerate(images):
        # Budget pre-check
        if budget and not budget.can_call():
            reason = budget.exhausted_reason()
            logger.info(
                "Budget exhausted after %d/%d images: %s",
                idx, len(images), reason,
            )
            break

        logger.info(
            "Analyzing image %d/%d from %s (%d KB)",
            idx + 1, len(images), isp_key,
            len(image.image_bytes) // 1024,
        )

        prompt = build_image_extraction_prompt(
            isp_key, marca, image.context_text,
        )

        start_ms = int(time.time() * 1000)
        try:
            response = client.extract_from_image(image.image_bytes, prompt)
            latency_ms = int(time.time() * 1000) - start_ms

            # Record in budget
            if budget:
                budget.record_call(
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    model=model,
                )

            # Record in cost tracker
            tracker.record(
                provider=client.provider,
                model=model,
                isp=isp_key,
                image_size_bytes=len(image.image_bytes),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=latency_ms,
                extraction_success=True,
                fields_extracted=0,
                fields_total=len(PlanISP.model_fields),
                plans_extracted=0,
                image_path=image.url,
            )

            # Parse and validate
            raw_plans = parse_llm_response(response.content)
            plans, errors = validate_and_build_plans(raw_plans, isp_key, now)
            all_plans.extend(plans)
            all_errors.extend(errors)
            images_processed += 1

            logger.info(
                "Image %d: %d plans extracted (%.1fs, $%.6f)",
                idx + 1, len(plans), latency_ms / 1000,
                tracker.records[-1].cost_usd if tracker.records else 0,
            )

        except Exception as e:
            latency_ms = int(time.time() * 1000) - start_ms
            logger.warning("Image %d analysis failed: %s", idx + 1, e)
            all_errors.append(f"Image {idx + 1} ({image.url}): {e}")

            # Still record the failed call in budget
            if budget:
                budget.record_call(input_tokens=0, output_tokens=0, model=model)

            tracker.record(
                provider=client.provider,
                model=model,
                isp=isp_key,
                image_size_bytes=len(image.image_bytes),
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                extraction_success=False,
                fields_extracted=0,
                fields_total=len(PlanISP.model_fields),
                plans_extracted=0,
                image_path=image.url,
            )

    # Deduplicate plans by (nombre_plan, velocidad, precio)
    seen: set[tuple] = set()
    unique: list[PlanISP] = []
    for plan in all_plans:
        key = (plan.nombre_plan, plan.velocidad_download_mbps, plan.precio_plan)
        if key not in seen:
            seen.add(key)
            unique.append(plan)

    logger.info(
        "Image extraction complete: %d images processed, %d unique plans",
        images_processed, len(unique),
    )
    return unique, all_errors
