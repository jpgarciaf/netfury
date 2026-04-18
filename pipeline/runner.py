"""End-to-end pipeline: scrape -> extract -> validate -> Parquet.

Orchestrates the full data extraction workflow for one or all ISPs.
Supports HTML, OCR, and LLM extraction strategies.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from extractors.html_extractor import extract_plans_from_html
from extractors.llm_extractor import extract_plans_from_image
from extractors.ocr_extractor import extract_plans_with_ocr
from llm.cost_tracker import CostTracker
from pipeline.parquet_writer import write_parquet
from schemas.plan import PlanISP
from scraper.spiders import get_spider
from settings import ISP_URLS, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_single_isp(
    isp_key: str,
    *,
    strategy: str = "llm",
    model: str | None = None,
    take_screenshot: bool = True,
) -> list[PlanISP]:
    """Run the extraction pipeline for a single ISP.

    Args:
        isp_key: ISP identifier (e.g., "xtrim").
        strategy: Extraction strategy: "html", "ocr", "llm", or "all".
        model: LLM model to use (defaults to settings).
        take_screenshot: Whether to capture a screenshot.

    Returns:
        List of validated PlanISP objects.
    """
    cfg = get_settings()
    model = model or cfg.llm_model
    spider = get_spider(isp_key)

    logger.info("=== Processing %s ===", isp_key)

    # Scrape
    if take_screenshot:
        page = spider.scrape_with_screenshot()
    else:
        page = spider.scrape()

    all_plans: list[PlanISP] = []

    # Strategy: HTML
    if strategy in ("html", "all") and page.html:
        html_plans, html_errors = extract_plans_from_html(
            page.html, isp_key,
        )
        logger.info("HTML: %d plans, %d errors", len(html_plans), len(html_errors))
        if strategy == "html":
            return html_plans
        all_plans.extend(html_plans)

    # Strategy: OCR
    if strategy in ("ocr", "all") and page.screenshot_bytes:
        ocr_plans, ocr_errors = extract_plans_with_ocr(
            page.screenshot_bytes, isp_key,
            image_path=page.screenshot_path,
        )
        logger.info("OCR: %d plans, %d errors", len(ocr_plans), len(ocr_errors))
        if strategy == "ocr":
            return ocr_plans
        all_plans.extend(ocr_plans)

    # Strategy: LLM
    if strategy in ("llm", "all") and page.screenshot_bytes:
        llm_plans, llm_errors = extract_plans_from_image(
            page.screenshot_bytes, isp_key, spider.marca,
            model=model,
            image_path=page.screenshot_path,
        )
        logger.info("LLM: %d plans, %d errors", len(llm_plans), len(llm_errors))
        if strategy == "llm":
            return llm_plans
        all_plans.extend(llm_plans)

    # Deduplicate by nombre_plan + velocidad
    seen = set()
    unique: list[PlanISP] = []
    for plan in all_plans:
        key = (plan.nombre_plan, plan.velocidad_download_mbps, plan.precio_plan)
        if key not in seen:
            seen.add(key)
            unique.append(plan)

    return unique


def run_all_isps(
    *,
    strategy: str = "llm",
    model: str | None = None,
    isps: list[str] | None = None,
) -> list[PlanISP]:
    """Run the pipeline for all (or selected) ISPs.

    Args:
        strategy: Extraction strategy.
        model: LLM model to use.
        isps: Optional list of ISP keys to process.

    Returns:
        Combined list of all extracted plans.
    """
    targets = isps or list(ISP_URLS.keys())
    all_plans: list[PlanISP] = []

    for isp_key in targets:
        try:
            plans = run_single_isp(
                isp_key, strategy=strategy, model=model,
            )
            all_plans.extend(plans)
            logger.info("%s: %d plans extracted", isp_key, len(plans))
        except Exception as e:
            logger.error("Failed to process %s: %s", isp_key, e)

    return all_plans


def main() -> None:
    """CLI entry point for the pipeline."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(
        description="NetFury Benchmark 360 Pipeline",
    )
    parser.add_argument(
        "--isp", type=str, default=None,
        help="Single ISP to process (e.g., 'xtrim'). "
        "If omitted, processes all ISPs.",
    )
    parser.add_argument(
        "--strategy", type=str, default="llm",
        choices=["html", "ocr", "llm", "all"],
        help="Extraction strategy (default: llm)",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="LLM model override",
    )
    parser.add_argument(
        "--output", type=str,
        default="data/processed/benchmark_industria.parquet",
        help="Output Parquet file path",
    )
    args = parser.parse_args()

    if args.isp:
        plans = run_single_isp(
            args.isp, strategy=args.strategy, model=args.model,
        )
    else:
        plans = run_all_isps(strategy=args.strategy, model=args.model)

    if plans:
        output_path = write_parquet(plans, args.output)
        logger.info("Output: %s (%d plans)", output_path, len(plans))
    else:
        logger.warning("No plans extracted!")

    # Export cost tracking
    tracker = CostTracker()
    if tracker.records:
        cost_path = tracker.export_parquet()
        logger.info("Cost tracking: %s", cost_path)
        print("\n=== Cost Summary ===")
        print(tracker.summary().to_string(index=False))


if __name__ == "__main__":
    main()
