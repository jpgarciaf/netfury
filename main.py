"""NetFury - Benchmark 360 CLI entry point.

Usage:
    uv run python main.py pipeline --isp xtrim --strategy llm
    uv run python main.py evaluate --isp xtrim
    uv run python main.py evaluate --isp xtrim --ground-truth data/raw/xtrim_gt.json
"""

from __future__ import annotations

import sys


def main() -> None:
    """Route to pipeline or evaluator based on CLI args."""
    if len(sys.argv) < 2:
        print("NetFury - Benchmark 360")
        print()
        print("Commands:")
        print("  benchmark-full - Extract ALL ISPs with 30+ fields (enhanced HTML)")
        print("  benchmark-recursive - Extract from homepage using recursive crawl")
        print("  benchmark-recursive-images - Recursive crawl plus image analysis")
        print("  benchmark      - Extract ALL ISPs (basic OCR/LLM)")
        print("  pipeline       - Run extraction pipeline for single/all ISPs")
        print("  evaluate       - Run multi-model evaluation")
        print()
        print("Examples:")
        print("  uv run python main.py benchmark-full")
        print("  uv run python main.py benchmark-full --isp xtrim")
        print("  uv run python main.py benchmark-recursive --isp claro --crawl-depth 2")
        print("  uv run python main.py benchmark-recursive-images --isp alfanet")
        print("  uv run python main.py benchmark-full --cached")
        print("  uv run python main.py benchmark --strategy llm --model gpt-4o")
        print("  uv run python main.py pipeline --isp xtrim --strategy llm")
        print("  uv run python main.py evaluate --isp xtrim")
        return

    command = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]  # Strip command for argparse

    if command == "benchmark-full":
        from pipeline.benchmark_full import main as run_benchmark_full
        run_benchmark_full()
    elif command == "benchmark-recursive":
        from pipeline.benchmark_recursive import main as run_benchmark_recursive
        run_benchmark_recursive()
    elif command == "benchmark-recursive-images":
        from pipeline.benchmark_recursive_images import main as run_benchmark_recursive_images
        run_benchmark_recursive_images()
    elif command == "benchmark":
        from pipeline.benchmark import main as run_benchmark
        run_benchmark()
    elif command == "pipeline":
        from pipeline.runner import main as run_pipeline
        run_pipeline()
    elif command == "evaluate":
        from pipeline.evaluator import main as run_evaluator
        run_evaluator()
    else:
        print(f"Unknown command: {command}")
        print("Use 'pipeline' or 'evaluate'")


if __name__ == "__main__":
    main()
