"""Recursive benchmark from ISP homepages using semantic link discovery.

This variant is similar to `benchmark-full`, but instead of starting from
predefined plan URLs it starts from each ISP homepage and discovers relevant
pages recursively with the semantic crawler.

Usage:
    uv run python main.py benchmark-recursive
    uv run python main.py benchmark-recursive --isp claro
    uv run python main.py benchmark-recursive --isp claro --crawl-depth 2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from extractors.full_html_extractor import extract_plans_full_html
from pipeline.parquet_writer import plans_to_dataframe, write_parquet
from schemas.plan import PlanISP
from scraper.crawler import CrawlConfig, RecursiveCrawler
from settings import ISP_URLS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BENCHMARK_ISPS = list(ISP_URLS.keys())


def _plan_key(plan: PlanISP) -> tuple[str, str, float, float]:
    """Build a stable dedupe key for plan rows."""
    return (
        plan.marca.strip().lower(),
        plan.nombre_plan.strip().lower(),
        round(plan.velocidad_download_mbps, 2),
        round(plan.precio_plan, 2),
    )


def _deduplicate_plans(plans: list[PlanISP]) -> list[PlanISP]:
    """Remove duplicate plans discovered across crawled pages."""
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
    """Normalize nested columns before CSV export."""
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
    """Choose a conservative page budget per ISP."""
    return max(8, crawl_depth * 5)


def run_recursive_isp(
    isp_key: str,
    *,
    crawl_depth: int,
    max_pages: int,
) -> tuple[list[PlanISP], list[dict]]:
    """Run recursive extraction for one ISP starting from the homepage."""
    seed_url = ISP_URLS.get(isp_key, "")
    if not seed_url:
        logger.warning("No homepage configured for %s", isp_key)
        return [], []

    crawl_config = CrawlConfig(
        max_depth=crawl_depth,
        max_pages=max_pages,
    )
    crawler = RecursiveCrawler(crawl_config)
    crawl_results = crawler.crawl([seed_url])

    if not crawl_results:
        logger.warning("No pages discovered for %s", isp_key)
        return [], []

    all_plans: list[PlanISP] = []
    pages: list[dict] = []

    for result in crawl_results:
        try:
            plans, errors = extract_plans_full_html(
                [result.url],
                isp_key,
                html_override=result.html,
            )
        except Exception as exc:
            logger.warning("Extraction failed on %s: %s", result.url, exc)
            plans = []
            errors = [str(exc)]

        all_plans.extend(plans)
        pages.append({
            "url": result.url,
            "depth": result.depth,
            "plans_extracted": len(plans),
            "errors": errors,
            "discovered_urls": result.discovered_urls,
        })

    unique_plans = _deduplicate_plans(all_plans)
    logger.info(
        "Recursive benchmark: %s => %d unique plans from %d crawled pages",
        isp_key, len(unique_plans), len(crawl_results),
    )
    return unique_plans, pages


def run_benchmark_recursive(
    *,
    isps: list[str] | None = None,
    output_dir: str = "data/processed",
    crawl_depth: int = 2,
    max_pages: int | None = None,
) -> list[PlanISP]:
    """Run the recursive homepage-first benchmark for one or more ISPs."""
    targets = isps or BENCHMARK_ISPS
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    all_plans: list[PlanISP] = []
    summary: list[dict] = []
    crawl_trace: dict[str, dict] = {}
    pages_budget = max_pages or _default_max_pages(crawl_depth)

    logger.info("=" * 60)
    logger.info(
        "BENCHMARK RECURSIVE — %d ISP(s) from homepage only",
        len(targets),
    )
    logger.info(
        "Crawl depth=%d | max_pages=%d | seed strategy=homepage_only",
        crawl_depth, pages_budget,
    )
    logger.info("=" * 60)

    for isp_key in targets:
        try:
            plans, pages = run_recursive_isp(
                isp_key,
                crawl_depth=crawl_depth,
                max_pages=pages_budget,
            )
            all_plans.extend(plans)
            summary.append({
                "isp": isp_key,
                "seed_url": ISP_URLS.get(isp_key, ""),
                "plans_extracted": len(plans),
                "pages_crawled": len(pages),
                "status": "ok" if plans else "no_data",
            })
            crawl_trace[isp_key] = {
                "seed_url": ISP_URLS.get(isp_key, ""),
                "pages": pages,
            }
        except Exception as exc:
            logger.error("FAIL %s: %s", isp_key, exc)
            summary.append({
                "isp": isp_key,
                "seed_url": ISP_URLS.get(isp_key, ""),
                "plans_extracted": 0,
                "pages_crawled": 0,
                "status": "error",
                "error": str(exc),
            })
            crawl_trace[isp_key] = {
                "seed_url": ISP_URLS.get(isp_key, ""),
                "pages": [],
                "error": str(exc),
            }

    if not all_plans:
        logger.warning("No plans extracted from any ISP")
    else:
        parquet_path = write_parquet(
            all_plans,
            str(out / "benchmark_recursive_industria.parquet"),
        )
        logger.info("Parquet: %s", parquet_path)

        df = plans_to_dataframe(all_plans)
        _serialize_df_for_csv(df)
        csv_path = out / "benchmark_recursive_industria.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info("CSV: %s", csv_path)

        json_path = out / "benchmark_recursive_industria.json"
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

    summary_path = out / "benchmark_recursive_summary.json"
    report = {
        "extraction_date": now.isoformat(),
        "strategy": "recursive_full_html",
        "seed_strategy": "homepage_only",
        "crawl_depth": crawl_depth,
        "max_pages_per_isp": pages_budget,
        "total_plans": len(all_plans),
        "total_isps_processed": len(targets),
        "isps_with_data": sum(1 for s in summary if s["status"] == "ok"),
        "details": summary,
    }
    summary_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Summary: %s", summary_path)

    trace_path = out / "benchmark_recursive_trace.json"
    trace_path.write_text(
        json.dumps(crawl_trace, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Trace: %s", trace_path)

    print("\n" + "=" * 60)
    print("BENCHMARK RECURSIVE — RESULTS")
    print("=" * 60)
    for item in summary:
        icon = "+" if item["status"] == "ok" else "x"
        print(
            f"  [{icon}] {item['isp']:12s} — {item['plans_extracted']} planes "
            f"desde {item['pages_crawled']} paginas",
        )
    print(f"\n  Total: {len(all_plans)} planes")
    print(f"  Crawl depth: {crawl_depth} | Max pages/ISP: {pages_budget}")
    print(f"  Files: {out}/benchmark_recursive_*")
    print("=" * 60)

    return all_plans


def main() -> None:
    """CLI entry point."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(
        description="Recursive benchmark from homepage with semantic crawling",
    )
    parser.add_argument(
        "--isp", type=str, default=None,
        help="Single ISP to process (default: all)",
    )
    parser.add_argument(
        "--crawl-depth", type=int, default=2,
        help="Max crawl depth from the homepage (default: 2)",
    )
    parser.add_argument(
        "--max-pages", type=int, default=None,
        help="Max pages to crawl per ISP (default: auto based on depth)",
    )
    parser.add_argument(
        "--output", type=str, default="data/processed",
        help="Output directory",
    )
    args = parser.parse_args()

    isps = [args.isp] if args.isp else None
    run_benchmark_recursive(
        isps=isps,
        output_dir=args.output,
        crawl_depth=args.crawl_depth,
        max_pages=args.max_pages,
    )


if __name__ == "__main__":
    main()
