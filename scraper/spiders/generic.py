"""Generic spider that works for any ISP.

Uses HTTP client for HTML and Playwright for screenshots.
Tries multiple URLs per ISP until one works.
"""

from __future__ import annotations

import logging
from pathlib import Path

from scraper.base_spider import BaseSpider, ScrapedPage
from scraper.utils.http_client import fetch_html

logger = logging.getLogger(__name__)


class GenericSpider(BaseSpider):
    """Generic spider that scrapes HTML and takes screenshots."""

    def __init__(
        self,
        isp_key: str,
        marca: str,
        urls: list[str],
    ) -> None:
        self.isp_key = isp_key
        self.marca = marca
        self.url = urls[0] if urls else ""
        self._urls = urls

    def get_plan_urls(self) -> list[str]:
        """Return configured URLs for this ISP."""
        return list(self._urls)

    def scrape(self) -> ScrapedPage:
        """Scrape HTML from the ISP website.

        Tries each configured URL until one succeeds.

        Returns:
            ScrapedPage with HTML content.
        """
        html = ""
        used_url = ""
        errors: list[str] = []

        for url in self._urls:
            try:
                logger.info("Fetching %s for %s", url, self.isp_key)
                html = fetch_html(url)
                used_url = url
                break
            except Exception as e:
                msg = f"Failed to fetch {url}: {e}"
                logger.warning(msg)
                errors.append(msg)

        return ScrapedPage(
            isp_key=self.isp_key,
            url=used_url,
            html=html,
            errors=errors,
        )

    def scrape_with_screenshot(
        self,
        output_dir: str = "data/raw/current",
    ) -> ScrapedPage:
        """Scrape HTML and take a screenshot.

        Args:
            output_dir: Directory to save screenshots.

        Returns:
            ScrapedPage with HTML and screenshot.
        """
        from scraper.utils.screenshot import capture_screenshot

        page = self.scrape()

        # Take screenshot of the first working URL
        url = page.url or (self._urls[0] if self._urls else "")
        if url:
            screenshot_path = (
                f"{output_dir}/{self.isp_key}_screenshot.png"
            )
            try:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                screenshot_bytes = capture_screenshot(
                    url, output_path=screenshot_path,
                )
                page.screenshot_bytes = screenshot_bytes
                page.screenshot_path = screenshot_path
            except Exception as e:
                msg = f"Screenshot failed for {url}: {e}"
                logger.warning(msg)
                page.errors.append(msg)

        return page
