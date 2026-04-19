"""Daily worker for ISP differential scraping.

Snapshot -> Check -> Process -> Rotate
"""

import logging
import shutil
import re
import argparse
from pathlib import Path
from datetime import datetime

from scraper.crawler import RecursiveCrawler, CrawlConfig
from scraper.spiders.generic import GenericSpider
from pipeline.utils.diff_checker import get_html_diff_chunks, has_image_changed
from extractors.llm_extractor import extract_plans_from_diff, extract_plans_from_image
from pipeline.parquet_writer import write_parquet
from settings import ISP_URLS, get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_daily_worker(isp_keys: list[str] | None = None, model: str | None = None):
    """Run the daily snapshot and differential extraction.

    Args:
        isp_keys: List of ISPs to process.
        model: LLM model to use for extraction.
    """
    settings = get_settings()
    model = model or settings.llm_model
    isps = isp_keys or list(ISP_URLS.keys())

    current_dir = Path("data/raw/current")
    previous_dir = Path("data/raw/previous")

    # Ensure directories exist
    current_dir.mkdir(parents=True, exist_ok=True)
    previous_dir.mkdir(parents=True, exist_ok=True)

    all_extracted_plans = []

    for isp_key in isps:
        logger.info("--- Processing %s ---", isp_key)
        urls = ISP_URLS.get(isp_key, [])
        if not urls:
            logger.warning("No URLs found for %s", isp_key)
            continue

        if isinstance(urls, str):
            urls = [urls]

        # 1. Sync & Snapshot
        # Discovery with RecursiveCrawler
        crawler = RecursiveCrawler(CrawlConfig(max_depth=1, max_pages=3))
        results = crawler.crawl(urls)

        # High-res screenshot with GenericSpider
        spider = GenericSpider(isp_key, isp_key.capitalize(), urls)
        page = spider.scrape_with_screenshot(output_dir=str(current_dir))

        # 2. Check (Difference Detection)
        # We'll check the main page HTML and the screenshot
        main_url = urls[0]
        safe_filename = re.sub(r"[^a-z0-9]", "_", main_url.lower())[:100] + ".html"
        current_html_path = current_dir / safe_filename
        previous_html_path = previous_dir / safe_filename
        current_image_path = current_dir / f"{isp_key}_screenshot.png"
        previous_image_path = previous_dir / f"{isp_key}_screenshot.png"

        # Read current HTML
        current_html = ""
        if current_html_path.exists():
            current_html = current_html_path.read_text(encoding="utf-8")

        diff_text = get_html_diff_chunks(current_html, previous_html_path)
        image_changed = has_image_changed(page.screenshot_bytes or b"", previous_image_path)

        # 3. Process (Differential Scraping)
        if diff_text and len(diff_text) > 50:  # Threshold for "real" change
            logger.info("Text differences detected for %s. Triggering LLM extraction from diff.", isp_key)
            plans, errors = extract_plans_from_diff(
                diff_text, isp_key, isp_key.capitalize(), model
            )
            all_extracted_plans.extend(plans)
        elif image_changed:
            logger.info("Visual changes detected for %s. Triggering full LLM image extraction.", isp_key)
            plans, errors = extract_plans_from_image(
                page.screenshot_bytes, isp_key, isp_key.capitalize(), model,
                image_path=str(current_image_path)
            )
            all_extracted_plans.extend(plans)
        else:
            logger.info("No changes detected for %s. Skipping LLM processing.", isp_key)

    # Save results if any
    if all_extracted_plans:
        output_path = "data/processed/benchmark_industria.parquet"
        write_parquet(all_extracted_plans, output_path)
        logger.info("Saved %d plans to %s", len(all_extracted_plans), output_path)

    # 4. Rotate (Move current to previous)
    # We do this after processing all ISPs
    logger.info("Rotating snapshots to historical archive.")
    for f in current_dir.glob("*"):
        shutil.copy2(f, previous_dir / f.name)

    # Cost tracking export
    from llm.cost_tracker import CostTracker
    CostTracker().export_parquet()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily worker pipeline.")
    parser.add_argument("--isp", type=str, help="ISP to process (optional)")
    parser.add_argument("--model", type=str, help="LLM model override")
    args = parser.parse_args()

    isp_keys = [args.isp] if args.isp else None
    run_daily_worker(isp_keys=isp_keys, model=args.model)
