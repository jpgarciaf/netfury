"""Multi-model evaluator for comparing extraction accuracy and cost.

Takes a single ISP page, runs it through all configured models
(LLM + OCR), and produces a comparison table with accuracy,
cost, cost/MB, and latency per model.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from extractors.guardrails import count_non_null_fields
from extractors.llm_extractor import extract_plans_from_image
from extractors.ocr_extractor import extract_plans_with_ocr
from llm.cost_tracker import CostTracker
from schemas.plan import PlanISP
from scraper.spiders import get_spider
from settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _compare_with_ground_truth(
    extracted: list[PlanISP],
    ground_truth: list[dict],
) -> float:
    """Compare extracted plans against ground truth.

    Uses a simple field-level accuracy metric: for each plan in
    ground truth, find the best matching extracted plan and compute
    the percentage of fields that match.

    Args:
        extracted: List of extracted PlanISP objects.
        ground_truth: List of ground truth plan dicts.

    Returns:
        Average accuracy percentage (0-100).
    """
    if not ground_truth or not extracted:
        return 0.0

    compare_fields = [
        "nombre_plan", "velocidad_download_mbps", "precio_plan",
        "velocidad_upload_mbps", "precio_plan_descuento",
        "meses_contrato", "tecnologia", "costo_instalacion",
    ]
    total_accuracy = 0.0

    for gt in ground_truth:
        best_match = 0.0
        for plan in extracted:
            matches = 0
            checked = 0
            for field in compare_fields:
                gt_val = gt.get(field)
                if gt_val is None:
                    continue
                checked += 1
                ext_val = getattr(plan, field, None)
                if ext_val is None:
                    continue
                # Numeric tolerance
                if isinstance(gt_val, (int, float)) and isinstance(ext_val, (int, float)):
                    if abs(gt_val - ext_val) <= max(0.01, abs(gt_val) * 0.05):
                        matches += 1
                # String comparison (case-insensitive)
                elif str(gt_val).strip().lower() == str(ext_val).strip().lower():
                    matches += 1

            if checked > 0:
                accuracy = matches / checked * 100
                best_match = max(best_match, accuracy)

        total_accuracy += best_match

    return round(total_accuracy / len(ground_truth), 1)


def evaluate_models(
    isp_key: str | None = None,
    ground_truth_path: str | None = None,
) -> pd.DataFrame:
    """Run all configured models on a single ISP and compare results.

    Args:
        isp_key: ISP to evaluate (defaults to settings.eval_isp).
        ground_truth_path: Path to ground truth JSON file.

    Returns:
        DataFrame with comparison metrics per model.
    """
    cfg = get_settings()
    isp_key = isp_key or cfg.eval_isp
    models = cfg.get_eval_models_list()
    tracker = CostTracker()
    tracker.reset()

    # Scrape and screenshot
    spider = get_spider(isp_key)
    logger.info("Capturing screenshot for %s...", isp_key)
    page = spider.scrape_with_screenshot()

    if not page.screenshot_bytes:
        logger.error("No screenshot captured for %s", isp_key)
        return pd.DataFrame()

    image_size_mb = len(page.screenshot_bytes) / 1_048_576
    logger.info(
        "Screenshot: %.2f MB (%s)",
        image_size_mb, page.screenshot_path,
    )

    # Load ground truth if available
    ground_truth: list[dict] = []
    if ground_truth_path and Path(ground_truth_path).exists():
        with open(ground_truth_path) as f:
            ground_truth = json.load(f)
        logger.info("Loaded %d ground truth plans", len(ground_truth))

    results: list[dict] = []

    # Run OCR extractors
    for engine in ["tesseract"]:
        logger.info("Running OCR (%s)...", engine)
        plans, errors = extract_plans_with_ocr(
            page.screenshot_bytes, isp_key,
            engine=engine, image_path=page.screenshot_path,
        )
        accuracy = _compare_with_ground_truth(plans, ground_truth) if ground_truth else 0.0

        results.append({
            "model": f"ocr-{engine}",
            "provider": "local",
            "plans_found": len(plans),
            "accuracy_pct": accuracy,
            "cost_usd": 0.0,
            "cost_per_mb": 0.0,
            "image_size_mb": round(image_size_mb, 3),
        })

    # Run LLM extractors
    for model in models:
        logger.info("Running %s...", model)
        plans, errors = extract_plans_from_image(
            page.screenshot_bytes, isp_key, spider.marca,
            model=model, image_path=page.screenshot_path,
        )
        accuracy = _compare_with_ground_truth(plans, ground_truth) if ground_truth else 0.0

        # Get cost from last tracker record
        last = tracker.records[-1] if tracker.records else None
        cost = last.cost_usd if last else 0.0
        cost_mb = last.cost_per_mb if last else 0.0
        latency = last.latency_ms if last else 0

        results.append({
            "model": model,
            "provider": last.provider if last else "unknown",
            "plans_found": len(plans),
            "accuracy_pct": accuracy,
            "cost_usd": round(cost, 6),
            "cost_per_mb": round(cost_mb, 6),
            "latency_s": round(latency / 1000, 1),
            "image_size_mb": round(image_size_mb, 3),
        })

    df = pd.DataFrame(results)

    # Export cost tracking
    if tracker.records:
        tracker.export_parquet()

    return df


def main() -> None:
    """CLI entry point for the evaluator."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(
        description="NetFury Multi-Model Evaluator",
    )
    parser.add_argument(
        "--isp", type=str, default=None,
        help="ISP to evaluate (default: from settings)",
    )
    parser.add_argument(
        "--ground-truth", type=str, default=None,
        help="Path to ground truth JSON file",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print(" NetFury Benchmark 360 - Multi-Model Evaluation")
    print("=" * 60 + "\n")

    df = evaluate_models(
        isp_key=args.isp,
        ground_truth_path=args.ground_truth,
    )

    if not df.empty:
        print("\n=== Results ===\n")
        print(df.to_string(index=False))
        print()

        # Save results
        output_path = Path("data/costs/evaluation_results.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}")

        # Cost summary
        tracker = CostTracker()
        summary = tracker.summary()
        if not summary.empty:
            print("\n=== Cost Summary ===\n")
            print(summary.to_string(index=False))
    else:
        print("No results generated.")


if __name__ == "__main__":
    main()
