"""Benchmark 360 — Full extraction of all ISPs for the challenge.

Scrapes all 8 ISPs, extracts plan data, and saves results
in multiple formats: Parquet, CSV, and JSON.

Usage:
    uv run python main.py benchmark
    uv run python main.py benchmark --strategy ocr
    uv run python main.py benchmark --strategy llm --model gpt-4o
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from pipeline.parquet_writer import plans_to_dataframe, write_parquet
from pipeline.runner import run_single_isp
from schemas.plan import PlanISP
from settings import ISP_URLS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# All ISPs required by the challenge
BENCHMARK_ISPS = list(ISP_URLS.keys())


def run_benchmark(
    *,
    strategy: str = "ocr",
    model: str | None = None,
    output_dir: str = "data/processed",
) -> list[PlanISP]:
    """Run extraction for all ISPs and save results.

    Args:
        strategy: Extraction strategy: "html", "ocr", "llm", or "all".
        model: LLM model override (only for llm/all strategy).
        output_dir: Directory to save output files.

    Returns:
        Combined list of all extracted plans.
    """
    all_plans: list[PlanISP] = []
    summary: list[dict] = []
    now = datetime.now()

    logger.info("=" * 60)
    logger.info("BENCHMARK 360 — Extracting %d ISPs", len(BENCHMARK_ISPS))
    logger.info("Strategy: %s | Date: %s", strategy, now.strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 60)

    for isp_key in BENCHMARK_ISPS:
        try:
            plans = run_single_isp(
                isp_key,
                strategy=strategy,
                model=model,
                take_screenshot=True,
            )
            all_plans.extend(plans)
            status = f"{len(plans)} plans"
            logger.info("OK  %s: %s", isp_key, status)
        except Exception as e:
            plans = []
            status = f"ERROR: {e}"
            logger.error("FAIL %s: %s", isp_key, e)

        summary.append({
            "isp": isp_key,
            "plans_extracted": len(plans),
            "status": "ok" if plans else "failed",
        })

    if not all_plans:
        logger.warning("No plans extracted from any ISP!")
        return []

    # Save outputs
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Parquet (required deliverable)
    parquet_path = write_parquet(all_plans, str(out / "benchmark_industria.parquet"))
    logger.info("Parquet: %s", parquet_path)

    # 2. CSV
    df = plans_to_dataframe(all_plans)
    # Convert complex columns to JSON strings for CSV
    for col in ["pys_adicionales_detalle", "sectores", "parroquia", "canton", "provincia"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False, default=str)
                if isinstance(x, (dict, list)) else str(x) if x else "{}",
            )
    csv_path = out / "benchmark_industria.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info("CSV: %s", csv_path)

    # 3. JSON (complete records)
    json_records = []
    for plan in all_plans:
        record = plan.model_dump(mode="json")
        json_records.append(record)
    json_path = out / "benchmark_industria.json"
    json_path.write_text(
        json.dumps(json_records, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("JSON: %s", json_path)

    # 4. Summary report
    summary_path = out / "benchmark_summary.json"
    report = {
        "extraction_date": now.isoformat(),
        "strategy": strategy,
        "model": model,
        "total_plans": len(all_plans),
        "total_isps_processed": len(BENCHMARK_ISPS),
        "isps_with_data": sum(1 for s in summary if s["status"] == "ok"),
        "isps_failed": sum(1 for s in summary if s["status"] == "failed"),
        "details": summary,
    }
    summary_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Summary: %s", summary_path)

    # Print final report
    print("\n" + "=" * 60)
    print("BENCHMARK 360 — RESULTS")
    print("=" * 60)
    for s in summary:
        icon = "+" if s["status"] == "ok" else "x"
        print(f"  [{icon}] {s['isp']:12s} — {s['plans_extracted']} planes")
    print(f"\n  Total: {len(all_plans)} planes de {len(BENCHMARK_ISPS)} ISPs")
    print(f"\n  Files saved in {out}/:")
    print(f"    - benchmark_industria.parquet")
    print(f"    - benchmark_industria.csv")
    print(f"    - benchmark_industria.json")
    print(f"    - benchmark_summary.json")
    print(f"  Screenshots in data/raw/")
    print("=" * 60)

    return all_plans


def main() -> None:
    """CLI entry point for benchmark extraction."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(
        description="Benchmark 360 — Extract all ISP plans",
    )
    parser.add_argument(
        "--strategy", type=str, default="ocr",
        choices=["html", "ocr", "llm", "all"],
        help="Extraction strategy (default: ocr)",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="LLM model override (for llm/all strategy)",
    )
    parser.add_argument(
        "--output", type=str, default="data/processed",
        help="Output directory (default: data/processed)",
    )
    args = parser.parse_args()

    plans = run_benchmark(
        strategy=args.strategy,
        model=args.model,
        output_dir=args.output,
    )

    # Cost tracking
    from llm.cost_tracker import CostTracker
    tracker = CostTracker()
    if tracker.records:
        cost_path = tracker.export_parquet()
        logger.info("Cost tracking: %s", cost_path)
        print("\n=== Cost Summary ===")
        print(tracker.summary().to_string(index=False))


if __name__ == "__main__":
    main()
