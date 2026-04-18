"""Local OCR extraction strategy using Tesseract and EasyOCR.

Free alternative to LLM vision. Lower accuracy but zero cost.
Extracts text from screenshots and uses regex patterns to find
plan data (prices, speeds, plan names).
"""

from __future__ import annotations

import io
import logging
import re
import time
from datetime import datetime

from PIL import Image

from extractors.guardrails import validate_and_build_plans
from llm.cost_tracker import CostTracker
from schemas.plan import PlanISP

logger = logging.getLogger(__name__)


def _ocr_with_tesseract(image_bytes: bytes) -> str:
    """Extract text using Tesseract OCR.

    Args:
        image_bytes: PNG/JPEG image bytes.

    Returns:
        Extracted text or empty string if Tesseract unavailable.
    """
    try:
        import pytesseract
        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img, lang="spa")
    except Exception as e:
        logger.warning("Tesseract OCR failed: %s", e)
        return ""


def _ocr_with_easyocr(image_bytes: bytes) -> str:
    """Extract text using EasyOCR.

    Args:
        image_bytes: PNG/JPEG image bytes.

    Returns:
        Extracted text or empty string if EasyOCR unavailable.
    """
    try:
        import easyocr
        reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
        results = reader.readtext(image_bytes)
        return " ".join(text for _, text, _ in results)
    except Exception as e:
        logger.warning("EasyOCR failed: %s", e)
        return ""


def _parse_plans_from_text(text: str) -> list[dict]:
    """Parse plan data from raw OCR text using regex patterns.

    This is a best-effort parser. It looks for common patterns:
    - Prices: $XX.XX, XX.XX USD
    - Speeds: XXX Mbps, XX Megas
    - Plan names: common ISP plan naming patterns

    Args:
        text: Raw OCR text.

    Returns:
        List of partially-filled plan dicts.
    """
    plans: list[dict] = []

    # Find all price-speed pairs
    prices = re.findall(
        r"\$\s*(\d+[.,]\d{2})", text,
    )
    speeds = re.findall(
        r"(\d+)\s*(?:Mbps|megas|MEGAS|MB)", text, re.IGNORECASE,
    )

    # Try to match prices with speeds
    n_plans = min(len(prices), len(speeds)) if prices and speeds else 0

    for i in range(n_plans):
        price_str = prices[i].replace(",", ".")
        try:
            price = float(price_str)
        except ValueError:
            continue

        try:
            speed = float(speeds[i])
        except ValueError:
            continue

        plans.append({
            "nombre_plan": f"Plan {int(speed)} Mbps",
            "velocidad_download_mbps": speed,
            "precio_plan": price,
        })

    # If no pairs found, try to extract at least speeds
    if not plans and speeds:
        for spd in speeds:
            try:
                speed = float(spd)
                plans.append({
                    "nombre_plan": f"Plan {int(speed)} Mbps",
                    "velocidad_download_mbps": speed,
                    "precio_plan": 0.0,
                })
            except ValueError:
                continue

    return plans


def extract_plans_with_ocr(
    image_bytes: bytes,
    isp_key: str,
    *,
    engine: str = "tesseract",
    image_path: str | None = None,
) -> tuple[list[PlanISP], list[str]]:
    """Extract ISP plans from a screenshot using local OCR.

    Args:
        image_bytes: PNG/JPEG screenshot bytes.
        isp_key: ISP identifier (e.g., "xtrim").
        engine: OCR engine to use: "tesseract" or "easyocr".
        image_path: Optional path for cost tracking.

    Returns:
        Tuple of (valid PlanISP list, error messages).
    """
    tracker = CostTracker()
    now = datetime.now()
    start_ms = int(time.time() * 1000)

    # Run OCR
    if engine == "easyocr":
        raw_text = _ocr_with_easyocr(image_bytes)
    else:
        raw_text = _ocr_with_tesseract(image_bytes)

    latency_ms = int(time.time() * 1000) - start_ms

    if not raw_text.strip():
        tracker.record(
            provider="local",
            model=f"ocr-{engine}",
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
        return [], ["OCR returned empty text"]

    # Parse plans from text
    raw_plans = _parse_plans_from_text(raw_text)
    plans, errors = validate_and_build_plans(raw_plans, isp_key, now)

    avg_fields = 0
    if plans:
        from extractors.guardrails import count_non_null_fields
        avg_fields = sum(
            count_non_null_fields(p) for p in plans
        ) // len(plans)

    tracker.record(
        provider="local",
        model=f"ocr-{engine}",
        isp=isp_key,
        image_size_bytes=len(image_bytes),
        input_tokens=0,
        output_tokens=0,
        latency_ms=latency_ms,
        extraction_success=len(plans) > 0,
        fields_extracted=avg_fields,
        fields_total=len(PlanISP.model_fields),
        plans_extracted=len(plans),
        image_path=image_path,
    )

    logger.info(
        "OCR (%s) extracted %d plans from %s (%.1fs, FREE)",
        engine, len(plans), isp_key, latency_ms / 1000,
    )
    return plans, errors
