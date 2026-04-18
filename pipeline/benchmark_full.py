"""Benchmark 360 Full — Extract all 30+ fields using enhanced HTML parsing.

Uses Playwright-rendered HTML with ISP-specific parsers to fill
as many of the 30+ required columns as possible, without LLM APIs.

Usage:
    uv run python main.py benchmark-full
    uv run python main.py benchmark-full --isp xtrim
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
from scraper.spiders import ISP_PLAN_URLS
from settings import ISP_URLS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BENCHMARK_ISPS = list(ISP_URLS.keys())


def run_benchmark_full(
    *,
    isps: list[str] | None = None,
    output_dir: str = "data/processed",
    use_cached_html: bool = False,
) -> list[PlanISP]:
    """Run full 30+ field extraction for all ISPs.

    Args:
        isps: Optional list of ISP keys. Defaults to all.
        output_dir: Directory to save output files.
        use_cached_html: If True, use pre-downloaded HTML from data/raw/.

    Returns:
        Combined list of all extracted plans.
    """
    targets = isps or BENCHMARK_ISPS
    all_plans: list[PlanISP] = []
    summary: list[dict] = []
    now = datetime.now()

    logger.info("=" * 60)
    logger.info("BENCHMARK 360 FULL — Extracting %d ISPs (30+ fields)", len(targets))
    logger.info("Date: %s", now.strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 60)

    for isp_key in targets:
        urls = ISP_PLAN_URLS.get(isp_key, [ISP_URLS.get(isp_key, "")])

        # Optionally use cached HTML
        html_override = None
        if use_cached_html:
            cached_path = Path(f"data/raw/{isp_key}_rendered.html")
            if cached_path.exists():
                html_override = cached_path.read_text(encoding="utf-8")
                logger.info("Using cached HTML for %s", isp_key)

        try:
            plans, errors = extract_plans_full_html(
                urls, isp_key, html_override=html_override,
            )
            all_plans.extend(plans)
            status = "ok" if plans else "no_data"
            logger.info(
                "%s %s: %d plans, %d errors",
                "OK " if plans else "WARN",
                isp_key, len(plans), len(errors),
            )
        except Exception as e:
            plans = []
            errors = [str(e)]
            status = "error"
            logger.error("FAIL %s: %s", isp_key, e)

        summary.append({
            "isp": isp_key,
            "plans_extracted": len(plans),
            "errors": len(errors),
            "status": status,
        })

    if not all_plans:
        logger.warning("No plans extracted from any ISP!")
        return []

    # Save outputs
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Parquet
    parquet_path = write_parquet(all_plans, str(out / "benchmark_industria.parquet"))
    logger.info("Parquet: %s", parquet_path)

    # 2. CSV
    df = plans_to_dataframe(all_plans)
    for col in ["pys_adicionales_detalle", "sectores", "parroquia", "canton", "provincia"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False, default=str)
                if isinstance(x, (dict, list)) else str(x) if x else "{}",
            )
    csv_path = out / "benchmark_industria.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info("CSV: %s", csv_path)

    # 3. JSON
    json_records = [plan.model_dump(mode="json") for plan in all_plans]
    json_path = out / "benchmark_industria.json"
    json_path.write_text(
        json.dumps(json_records, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("JSON: %s", json_path)

    # 4. Summary
    summary_path = out / "benchmark_summary.json"
    # Count non-null fields per plan
    field_counts = []
    for plan in all_plans:
        count = sum(
            1 for f in PlanISP.model_fields
            if getattr(plan, f) is not None
            and getattr(plan, f) != ""
            and getattr(plan, f) != []
            and getattr(plan, f) != {}
        )
        field_counts.append(count)

    avg_fields = sum(field_counts) / len(field_counts) if field_counts else 0
    total_fields = len(PlanISP.model_fields)

    report = {
        "extraction_date": now.isoformat(),
        "strategy": "full_html",
        "total_plans": len(all_plans),
        "total_isps_processed": len(targets),
        "isps_with_data": sum(1 for s in summary if s["status"] == "ok"),
        "avg_fields_filled": round(avg_fields, 1),
        "total_possible_fields": total_fields,
        "field_coverage_pct": round(avg_fields / total_fields * 100, 1),
        "details": summary,
    }
    summary_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Summary: %s", summary_path)

    # Print report
    print("\n" + "=" * 60)
    print("BENCHMARK 360 FULL — RESULTS")
    print("=" * 60)
    for s in summary:
        icon = "+" if s["status"] == "ok" else "x"
        print(f"  [{icon}] {s['isp']:12s} — {s['plans_extracted']} planes ({s['errors']} errors)")
    print(f"\n  Total: {len(all_plans)} planes de {len(targets)} ISPs")
    print(f"  Field coverage: {avg_fields:.1f}/{total_fields} ({avg_fields/total_fields*100:.0f}%)")
    print(f"\n  Files:")
    print(f"    - {out}/benchmark_industria.parquet")
    print(f"    - {out}/benchmark_industria.csv")
    print(f"    - {out}/benchmark_industria.json")
    print(f"    - {out}/benchmark_summary.json")
    print("=" * 60)

    return all_plans


def main() -> None:
    """CLI entry point."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(
        description="Benchmark 360 Full — Extract all 30+ fields",
    )
    parser.add_argument(
        "--isp", type=str, default=None,
        help="Single ISP to process (default: all)",
    )
    parser.add_argument(
        "--output", type=str, default="data/processed",
        help="Output directory",
    )
    parser.add_argument(
        "--cached", action="store_true",
        help="Use cached HTML from data/raw/ (skip Playwright)",
    )
    args = parser.parse_args()

    isps = [args.isp] if args.isp else None

    run_benchmark_full(
        isps=isps,
        output_dir=args.output,
        use_cached_html=args.cached,
    )


if __name__ == "__main__":
    main()
