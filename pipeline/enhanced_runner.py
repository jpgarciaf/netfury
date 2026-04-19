"""Enhanced pipeline with recursive crawling, image analysis, and budget limits.

Composes:
1. Recursive BFS crawling to discover plan pages
2. Free HTML extraction from all crawled pages
3. Individual banner image analysis via LLM Vision (budget-controlled)
4. Merge, deduplicate, and export to Parquet/CSV/JSON

Usage:
    uv run python -m pipeline.enhanced_runner
    uv run python -m pipeline.enhanced_runner --isp xtrim --crawl-depth 2
    uv run python -m pipeline.enhanced_runner --max-llm-calls 20 --max-cost 1.0
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from extractors.full_html_extractor import extract_plans_full_html
from extractors.image_extractor import extract_plans_from_individual_images
from llm.budget import Budget, BudgetManager
from llm.cost_tracker import CostTracker
from pipeline.parquet_writer import plans_to_dataframe, write_parquet
from schemas.plan import PlanISP
from scraper.crawler import CrawlConfig, RecursiveCrawler
from scraper.image_discoverer import ImageDiscoverer
from scraper.spiders import ISP_PLAN_URLS
from settings import ISP_URLS, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BENCHMARK_ISPS = list(ISP_URLS.keys())


def run_enhanced_isp(
    isp_key: str,
    *,
    model: str | None = None,
    crawl_depth: int = 1,
    max_images: int = 10,
    budget: BudgetManager | None = None,
) -> list[PlanISP]:
    """Run enhanced extraction for a single ISP.

    Layers:
    1. Recursive crawl to discover pages
    2. HTML parsing (free) on all pages
    3. Image discovery + LLM analysis (budget-controlled)

    Args:
        isp_key: ISP identifier.
        model: LLM model for image analysis.
        crawl_depth: Max depth for recursive crawling.
        max_images: Max images to analyze per ISP.
        budget: Budget manager for LLM limits.

    Returns:
        List of validated PlanISP objects.
    """
    cfg = get_settings()
    model = model or cfg.llm_model
    marca = isp_key.capitalize()
    if isp_key == "cnt":
        marca = "CNT"

    seed_urls = ISP_PLAN_URLS.get(isp_key, [ISP_URLS.get(isp_key, "")])

    logger.info("=" * 50)
    logger.info("Enhanced pipeline: %s (depth=%d)", isp_key, crawl_depth)
    logger.info("=" * 50)

    # --- Layer 1: Recursive crawl ---
    crawl_config = CrawlConfig(
        max_depth=crawl_depth,
        max_pages=max(5, crawl_depth * 3),
    )
    crawler = RecursiveCrawler(crawl_config)
    crawl_results = crawler.crawl(seed_urls)

    if not crawl_results:
        logger.warning("No pages crawled for %s", isp_key)
        return []

    logger.info("Crawled %d pages for %s", len(crawl_results), isp_key)

    # --- Layer 2: HTML extraction (free) ---
    html_plans: list[PlanISP] = []
    all_images: list = []

    for result in crawl_results:
        # Extract plans from HTML
        plans, errors = extract_plans_full_html(
            [result.url], isp_key, html_override=result.html,
        )
        html_plans.extend(plans)

        if errors:
            logger.debug("HTML errors on %s: %s", result.url, errors)

        # Discover images on this page
        discoverer = ImageDiscoverer()
        images = discoverer.discover_images(
            result.html, result.url, max_images=max_images,
        )
        all_images.extend(images)

    logger.info(
        "HTML extraction: %d plans from %d pages",
        len(html_plans), len(crawl_results),
    )

    # Deduplicate images by URL
    seen_img_urls: set[str] = set()
    unique_images = []
    for img in all_images:
        if img.url not in seen_img_urls:
            seen_img_urls.add(img.url)
            unique_images.append(img)
    unique_images = unique_images[:max_images]

    logger.info("Discovered %d unique images for %s", len(unique_images), isp_key)

    # --- Layer 3: Image LLM analysis (budget-controlled) ---
    image_plans: list[PlanISP] = []
    if unique_images and (budget is None or budget.can_call()):
        image_plans, img_errors = extract_plans_from_individual_images(
            unique_images, isp_key, marca, model, budget=budget,
        )
        logger.info("Image extraction: %d plans", len(image_plans))
    elif budget and not budget.can_call():
        logger.info("Skipping image analysis: budget exhausted")

    # --- Merge and deduplicate ---
    all_plans = html_plans + image_plans
    seen: set[tuple] = set()
    unique: list[PlanISP] = []
    for plan in all_plans:
        key = (plan.nombre_plan, plan.velocidad_download_mbps, plan.precio_plan)
        if key not in seen:
            seen.add(key)
            unique.append(plan)

    logger.info(
        "Final: %d unique plans for %s (HTML=%d, Image=%d)",
        len(unique), isp_key, len(html_plans), len(image_plans),
    )
    return unique


def run_enhanced_all(
    *,
    isps: list[str] | None = None,
    model: str | None = None,
    crawl_depth: int = 1,
    max_images: int = 10,
    max_llm_calls: int | None = None,
    max_tokens: int | None = None,
    max_cost_usd: float | None = None,
    output_dir: str = "data/processed",
) -> list[PlanISP]:
    """Run enhanced extraction for all ISPs with budget limits.

    Args:
        isps: Optional list of ISP keys. Defaults to all.
        model: LLM model override.
        crawl_depth: Max crawling depth.
        max_images: Max images per ISP.
        max_llm_calls: Budget: max LLM API calls.
        max_tokens: Budget: max total tokens.
        max_cost_usd: Budget: max USD cost.
        output_dir: Directory for output files.

    Returns:
        Combined list of all extracted plans.
    """
    targets = isps or BENCHMARK_ISPS
    now = datetime.now()

    # Create budget manager
    budget = BudgetManager(Budget(
        max_llm_calls=max_llm_calls,
        max_tokens=max_tokens,
        max_cost_usd=max_cost_usd,
    ))

    logger.info("=" * 60)
    logger.info("ENHANCED PIPELINE — %d ISPs", len(targets))
    logger.info(
        "Crawl depth: %d | Max images/ISP: %d | Budget: calls=%s tokens=%s cost=$%s",
        crawl_depth, max_images,
        max_llm_calls or "unlimited",
        max_tokens or "unlimited",
        max_cost_usd or "unlimited",
    )
    logger.info("=" * 60)

    all_plans: list[PlanISP] = []
    summary: list[dict] = []

    for isp_key in targets:
        try:
            plans = run_enhanced_isp(
                isp_key,
                model=model,
                crawl_depth=crawl_depth,
                max_images=max_images,
                budget=budget,
            )
            all_plans.extend(plans)
            summary.append({
                "isp": isp_key,
                "plans_extracted": len(plans),
                "status": "ok" if plans else "no_data",
            })
        except Exception as e:
            logger.error("Failed %s: %s", isp_key, e)
            summary.append({
                "isp": isp_key, "plans_extracted": 0, "status": "error",
            })

    if not all_plans:
        logger.warning("No plans extracted!")
        return []

    # --- Save outputs ---
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Parquet
    parquet_path = write_parquet(all_plans, str(out / "benchmark_industria.parquet"))

    # CSV
    df = plans_to_dataframe(all_plans)
    for col in ["pys_adicionales_detalle", "sectores", "parroquia", "canton", "provincia"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False, default=str)
                if isinstance(x, (dict, list)) else str(x) if x else "{}",
            )
    csv_path = out / "benchmark_industria.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # JSON
    json_records = [plan.model_dump(mode="json") for plan in all_plans]
    json_path = out / "benchmark_industria.json"
    json_path.write_text(
        json.dumps(json_records, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # Summary
    budget_info = budget.remaining()
    report = {
        "extraction_date": now.isoformat(),
        "strategy": "enhanced",
        "crawl_depth": crawl_depth,
        "max_images_per_isp": max_images,
        "total_plans": len(all_plans),
        "total_isps": len(targets),
        "isps_with_data": sum(1 for s in summary if s["status"] == "ok"),
        "budget": budget_info,
        "details": summary,
    }
    summary_path = out / "benchmark_summary.json"
    summary_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # Print report
    print("\n" + "=" * 60)
    print("ENHANCED PIPELINE — RESULTS")
    print("=" * 60)
    for s in summary:
        icon = "+" if s["status"] == "ok" else "x"
        print(f"  [{icon}] {s['isp']:12s} — {s['plans_extracted']} planes ({s['status']})")
    print(f"\n  Total: {len(all_plans)} planes")
    print(f"  Budget used: {budget.calls} calls, {budget.tokens} tokens, ${budget.cost_usd:.4f}")
    print(f"\n  Files: {out}/benchmark_industria.[parquet|csv|json]")
    print("=" * 60)

    return all_plans


def main() -> None:
    """CLI entry point."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(
        description="Enhanced Pipeline — Crawl + Image Analysis + Budget Limits",
    )
    parser.add_argument("--isp", type=str, default=None, help="Single ISP to process")
    parser.add_argument("--model", type=str, default=None, help="LLM model override")
    parser.add_argument("--crawl-depth", type=int, default=1, help="Max crawl depth (default: 1)")
    parser.add_argument("--max-images", type=int, default=10, help="Max images per ISP (default: 10)")
    parser.add_argument("--max-llm-calls", type=int, default=None, help="Budget: max LLM calls")
    parser.add_argument("--max-tokens", type=int, default=None, help="Budget: max tokens")
    parser.add_argument("--max-cost", type=float, default=None, help="Budget: max USD cost")
    parser.add_argument("--output", type=str, default="data/processed", help="Output directory")
    args = parser.parse_args()

    isps = [args.isp] if args.isp else None

    plans = run_enhanced_all(
        isps=isps,
        model=args.model,
        crawl_depth=args.crawl_depth,
        max_images=args.max_images,
        max_llm_calls=args.max_llm_calls,
        max_tokens=args.max_tokens,
        max_cost_usd=args.max_cost,
        output_dir=args.output,
    )

    # Cost summary
    tracker = CostTracker()
    if tracker.records:
        cost_path = tracker.export_parquet()
        logger.info("Cost tracking: %s", cost_path)
        print("\n=== Cost Summary ===")
        print(tracker.summary().to_string(index=False))


if __name__ == "__main__":
    main()
