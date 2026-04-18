"""Playwright-based screenshot capture for ISP websites.

Takes full-page screenshots of ISP plan pages for vision-based
extraction by LLMs or OCR.
"""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

from settings import get_settings

logger = logging.getLogger(__name__)


def capture_screenshot(
    url: str,
    output_path: str | None = None,
    *,
    full_page: bool = True,
    wait_ms: int = 3000,
) -> bytes:
    """Capture a screenshot of a web page using Playwright.

    Args:
        url: The URL to screenshot.
        output_path: Optional file path to save the screenshot.
        full_page: If True, capture the full scrollable page.
        wait_ms: Milliseconds to wait after page load for JS rendering.

    Returns:
        Screenshot as PNG bytes.
    """
    cfg = get_settings()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--ignore-certificate-errors",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            viewport={
                "width": cfg.screenshot_width,
                "height": cfg.screenshot_height,
            },
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.0 Safari/605.1.15"
            ),
        )
        page = context.new_page()

        logger.info("Navigating to %s", url)
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Extra wait for dynamic content (JS frameworks, lazy loading)
        if wait_ms > 0:
            page.wait_for_timeout(wait_ms)

        # Additional wait for JS-heavy sites
        page.wait_for_timeout(5000)

        # Scroll to load lazy content
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        screenshot_bytes = page.screenshot(full_page=full_page, type="png")
        context.close()
        browser.close()

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(screenshot_bytes)
        logger.info(
            "Screenshot saved: %s (%.1f KB)",
            output_path, len(screenshot_bytes) / 1024,
        )

    return screenshot_bytes
