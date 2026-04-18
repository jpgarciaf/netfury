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
        print("  pipeline  - Run extraction pipeline for ISPs")
        print("  evaluate  - Run multi-model evaluation")
        print()
        print("Examples:")
        print("  uv run python main.py pipeline --isp xtrim --strategy llm")
        print("  uv run python main.py pipeline --strategy llm")
        print("  uv run python main.py evaluate --isp xtrim")
        return

    command = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]  # Strip command for argparse

    if command == "pipeline":
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
