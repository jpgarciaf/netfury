"""Recursive homepage-first benchmark with HTML and image analysis.

Starts from each ISP homepage, discovers relevant pages recursively using the
semantic crawler, extracts plans from rendered HTML, then discovers relevant
images on those pages and runs vision extraction on them.

Usage:
    uv run python main.py benchmark-recursive-images --isp alfanet
    uv run python main.py benchmark-recursive-images --isp alfanet --crawl-depth 2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from extractors.image_extractor import extract_plans_from_individual_images
from extractors.full_html_extractor import extract_plans_full_html
from llm.budget import Budget, BudgetManager
from pipeline.parquet_writer import plans_to_dataframe, write_parquet
from schemas.plan import PlanISP
from scraper.crawler import CrawlConfig, RecursiveCrawler
from scraper.image_discoverer import ImageDiscoverer
from settings import ISP_URLS, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BENCHMARK_ISPS = list(ISP_URLS.keys())


def _plan_key(plan: PlanISP) -> tuple[str, str, float, float]:
    return (
        plan.marca.strip().lower(),
        plan.nombre_plan.strip().lower(),
        round(plan.velocidad_download_mbps, 2),
        round(plan.precio_plan, 2),
    )


def _deduplicate_plans(plans: list[PlanISP]) -> list[PlanISP]:
    unique: list[PlanISP] = []
    seen: set[tuple[str, str, float, float]] = set()
    for plan in plans:
        key = _plan_key(plan)
        if key in seen:
            continue
        seen.add(key)
        unique.append(plan)
    return unique


def _serialize_df_for_csv(df) -> None:
    for col in [
        "pys_adicionales_detalle", "sectores", "parroquia", "canton", "provincia",
    ]:
        if col not in df.columns:
            continue
        df[col] = df[col].apply(
            lambda x: json.dumps(x, ensure_ascii=False, default=str)
            if isinstance(x, (dict, list)) else str(x) if x else "{}",
        )


def _default_max_pages(crawl_depth: int) -> int:
    return max(8, crawl_depth * 5)


def run_recursive_images_isp(
    isp_key: str,
    *,
    crawl_depth: int,
    max_pages: int,
    max_images: int,
    model: str | None = None,
    budget: BudgetManager | None = None,
) -> tuple[list[PlanISP], dict]:
    """Run recursive HTML + image extraction for a single ISP homepage."""
    cfg = get_settings()
    model = model or cfg.llm_model
    marca = isp_key.capitalize() if isp_key != "cnt" else "CNT"
    seed_url = ISP_URLS.get(isp_key, "")
    if not seed_url:
        logger.warning("No homepage configured for %s", isp_key)
        return [], {"seed_url": "", "pages": [], "images": []}

    crawl_config = CrawlConfig(
        max_depth=crawl_depth,
        max_pages=max_pages,
    )
    crawler = RecursiveCrawler(crawl_config)
    crawl_results = crawler.crawl([seed_url])

    if not crawl_results:
        logger.warning("No pages discovered for %s", isp_key)
        return [], {"seed_url": seed_url, "pages": [], "images": []}

    html_plans: list[PlanISP] = []
    image_candidates = []
    pages: list[dict] = []
    discoverer = ImageDiscoverer()

    for result in crawl_results:
        try:
            plans, errors = extract_plans_full_html(
                [result.url],
                isp_key,
                html_override=result.html,
            )
        except Exception as exc:
            logger.warning("HTML extraction failed on %s: %s", result.url, exc)
            plans = []
            errors = [str(exc)]

        html_plans.extend(plans)
        images = discoverer.discover_images(
            result.html,
            result.url,
            max_images=max_images,
        )
        image_candidates.extend(images)
        pages.append({
            "url": result.url,
            "depth": result.depth,
            "plans_extracted_html": len(plans),
            "errors": errors,
            "discovered_urls": result.discovered_urls,
            "images_discovered": len(images),
        })

    unique_images = []
    seen_image_urls: set[str] = set()
    for image in image_candidates:
        if image.url in seen_image_urls:
            continue
        seen_image_urls.add(image.url)
        unique_images.append(image)
    unique_images = unique_images[:max_images]

    image_plans: list[PlanISP] = []
    image_errors: list[str] = []
    if unique_images and (budget is None or budget.can_call()):
        image_plans, image_errors = extract_plans_from_individual_images(
            unique_images,
            isp_key,
            marca,
            model,
            budget=budget,
        )

    all_plans = _deduplicate_plans(html_plans + image_plans)
    logger.info(
        "Recursive images benchmark: %s => %d unique plans (HTML=%d, Image=%d)",
        isp_key, len(all_plans), len(html_plans), len(image_plans),
    )
    return all_plans, {
        "seed_url": seed_url,
        "pages": pages,
        "images": [
            {
                "url": image.url,
                "context_text": image.context_text,
                "alt_text": image.alt_text,
            }
            for image in unique_images
        ],
        "image_errors": image_errors,
    }


def run_benchmark_recursive_images(
    *,
    isps: list[str] | None = None,
    output_dir: str = "data/processed",
    crawl_depth: int = 2,
    max_pages: int | None = None,
    max_images: int = 10,
    model: str | None = None,
    max_llm_calls: int | None = None,
    max_tokens: int | None = None,
    max_cost_usd: float | None = None,
) -> list[PlanISP]:
    """Run the recursive HTML + image benchmark for one or more ISPs."""
    targets = isps or BENCHMARK_ISPS
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    all_plans: list[PlanISP] = []
    summary: list[dict] = []
    crawl_trace: dict[str, dict] = {}
    pages_budget = max_pages or _default_max_pages(crawl_depth)
    budget = BudgetManager(Budget(
        max_llm_calls=max_llm_calls,
        max_tokens=max_tokens,
        max_cost_usd=max_cost_usd,
    ))

    logger.info("=" * 60)
    logger.info(
        "BENCHMARK RECURSIVE IMAGES — %d ISP(s) from homepage only",
        len(targets),
    )
    logger.info(
        "Crawl depth=%d | max_pages=%d | max_images=%d | seed=homepage_only",
        crawl_depth, pages_budget, max_images,
    )
    logger.info("=" * 60)

    for isp_key in targets:
        try:
            plans, trace = run_recursive_images_isp(
                isp_key,
                crawl_depth=crawl_depth,
                max_pages=pages_budget,
                max_images=max_images,
                model=model,
                budget=budget,
            )
            all_plans.extend(plans)
            summary.append({
                "isp": isp_key,
                "seed_url": ISP_URLS.get(isp_key, ""),
                "plans_extracted": len(plans),
                "pages_crawled": len(trace["pages"]),
                "images_analyzed": len(trace["images"]),
                "status": "ok" if plans else "no_data",
            })
            crawl_trace[isp_key] = trace
        except Exception as exc:
            logger.error("FAIL %s: %s", isp_key, exc)
            summary.append({
                "isp": isp_key,
                "seed_url": ISP_URLS.get(isp_key, ""),
                "plans_extracted": 0,
                "pages_crawled": 0,
                "images_analyzed": 0,
                "status": "error",
                "error": str(exc),
            })
            crawl_trace[isp_key] = {
                "seed_url": ISP_URLS.get(isp_key, ""),
                "pages": [],
                "images": [],
                "error": str(exc),
            }

    if all_plans:
        parquet_path = write_parquet(
            all_plans,
            str(out / "benchmark_recursive_images_industria.parquet"),
        )
        logger.info("Parquet: %s", parquet_path)

        df = plans_to_dataframe(all_plans)
        _serialize_df_for_csv(df)
        csv_path = out / "benchmark_recursive_images_industria.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info("CSV: %s", csv_path)

        json_path = out / "benchmark_recursive_images_industria.json"
        json_path.write_text(
            json.dumps(
                [plan.model_dump(mode="json") for plan in all_plans],
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        logger.info("JSON: %s", json_path)
    else:
        logger.warning("No plans extracted from any ISP")

    summary_path = out / "benchmark_recursive_images_summary.json"
    report = {
        "extraction_date": now.isoformat(),
        "strategy": "recursive_full_html_plus_images",
        "seed_strategy": "homepage_only",
        "crawl_depth": crawl_depth,
        "max_pages_per_isp": pages_budget,
        "max_images_per_isp": max_images,
        "total_plans": len(all_plans),
        "total_isps_processed": len(targets),
        "isps_with_data": sum(1 for s in summary if s["status"] == "ok"),
        "budget": budget.remaining(),
        "details": summary,
    }
    summary_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Summary: %s", summary_path)

    trace_path = out / "benchmark_recursive_images_trace.json"
    trace_path.write_text(
        json.dumps(crawl_trace, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Trace: %s", trace_path)

    print("\n" + "=" * 60)
    print("BENCHMARK RECURSIVE IMAGES — RESULTS")
    print("=" * 60)
    for item in summary:
        icon = "+" if item["status"] == "ok" else "x"
        print(
            f"  [{icon}] {item['isp']:12s} — {item['plans_extracted']} planes "
            f"desde {item['pages_crawled']} paginas / {item['images_analyzed']} imagenes",
        )
    print(f"\n  Total: {len(all_plans)} planes")
    print(f"  Crawl depth: {crawl_depth} | Max pages/ISP: {pages_budget} | Max images/ISP: {max_images}")
    print(f"  Files: {out}/benchmark_recursive_images_*")
    print("=" * 60)

    return all_plans


def main() -> None:
    """CLI entry point."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(
        description="Recursive benchmark from homepage with HTML + image analysis",
    )
    parser.add_argument("--isp", type=str, default=None, help="Single ISP to process")
    parser.add_argument("--crawl-depth", type=int, default=2, help="Max crawl depth (default: 2)")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages to crawl per ISP")
    parser.add_argument("--max-images", type=int, default=10, help="Max images to analyze per ISP")
    parser.add_argument("--model", type=str, default=None, help="LLM model override")
    parser.add_argument("--max-llm-calls", type=int, default=None, help="Budget: max LLM calls")
    parser.add_argument("--max-tokens", type=int, default=None, help="Budget: max tokens")
    parser.add_argument("--max-cost", type=float, default=None, help="Budget: max USD cost")
    parser.add_argument("--output", type=str, default="data/processed", help="Output directory")
    args = parser.parse_args()

    isps = [args.isp] if args.isp else None
    run_benchmark_recursive_images(
        isps=isps,
        output_dir=args.output,
        crawl_depth=args.crawl_depth,
        max_pages=args.max_pages,
        max_images=args.max_images,
        model=args.model,
        max_llm_calls=args.max_llm_calls,
        max_tokens=args.max_tokens,
        max_cost_usd=args.max_cost,
    )


if __name__ == "__main__":
    main()
