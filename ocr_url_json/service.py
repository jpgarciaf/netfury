"""Servicio para ejecutar OCR sobre una imagen remota y serializar a JSON."""

from __future__ import annotations

import json
from urllib.parse import urlparse

from extractors.ocr_extractor import extract_plans_with_ocr
from scraper.utils.http_client import fetch_bytes
from settings import ISP_URLS


def _infer_isp_key_from_url(image_url: str) -> str:
    """Infer ISP key from image URL host when possible."""
    parsed = urlparse(image_url)
    host = parsed.netloc.lower()

    for isp_key, base_url in ISP_URLS.items():
        base_host = urlparse(base_url).netloc.lower()
        if host == base_host or host.endswith(f".{base_host}") or base_host.endswith(f".{host}"):
            return isp_key

    if host.startswith("www."):
        host = host[4:]

    candidate = host.split(".")[0].strip()
    return candidate or "unknown"


def extract_plans_json_from_url(
    image_url: str,
    *,
    engine: str = "tesseract",
    isp_key: str | None = None,
    respect_robots: bool = True,
) -> dict:
    """Fetch an image URL, run the current OCR logic, and return JSON-ready data."""
    resolved_isp_key = isp_key or _infer_isp_key_from_url(image_url)
    image_bytes = fetch_bytes(image_url, respect_robots=respect_robots)
    plans, errors = extract_plans_with_ocr(
        image_bytes,
        resolved_isp_key,
        engine=engine,
        image_path=image_url,
    )

    return {
        "image_url": image_url,
        "isp_key": resolved_isp_key,
        "engine": engine,
        "plans_count": len(plans),
        "plans": [plan.model_dump(mode="json") for plan in plans],
        "errors": errors,
    }


def extract_plans_json_string_from_url(
    image_url: str,
    *,
    engine: str = "tesseract",
    isp_key: str | None = None,
    respect_robots: bool = True,
    indent: int = 2,
) -> str:
    """Return the OCR extraction result as a JSON string."""
    payload = extract_plans_json_from_url(
        image_url,
        engine=engine,
        isp_key=isp_key,
        respect_robots=respect_robots,
    )
    return json.dumps(payload, indent=indent, ensure_ascii=False)
