"""HTTP client with robots.txt compliance, delays, and UA rotation.

Provides a safe, throttled HTTP client for scraping ISP websites
while respecting their terms of service.
"""

from __future__ import annotations

import random
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from settings import get_settings

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
    "Gecko/20100101 Firefox/128.0",
]

_robots_cache: dict[str, RobotFileParser] = {}


def _get_random_ua() -> str:
    """Return a random user-agent string."""
    return random.choice(_USER_AGENTS)


def _check_robots(url: str) -> bool:
    """Check if the URL is allowed by the site's robots.txt.

    Args:
        url: The full URL to check.

    Returns:
        True if the URL is allowed (or robots.txt is unreachable).
    """
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    if base not in _robots_cache:
        rp = RobotFileParser()
        rp.set_url(f"{base}/robots.txt")
        try:
            rp.read()
        except Exception:
            return True
        _robots_cache[base] = rp

    return _robots_cache[base].can_fetch("*", url)


def _apply_delay() -> None:
    """Sleep for a random duration within configured bounds."""
    cfg = get_settings()
    delay = random.uniform(cfg.scrape_delay_min, cfg.scrape_delay_max)
    time.sleep(delay)


def fetch_html(url: str, *, respect_robots: bool = True) -> str:
    """Fetch a URL and return its HTML content.

    Args:
        url: The URL to fetch.
        respect_robots: If True, check robots.txt before fetching.

    Returns:
        The HTML content as a string.

    Raises:
        PermissionError: If robots.txt disallows the URL.
        httpx.HTTPStatusError: If the HTTP response is an error.
    """
    if respect_robots and not _check_robots(url):
        raise PermissionError(f"Blocked by robots.txt: {url}")

    _apply_delay()

    headers = {"User-Agent": _get_random_ua()}
    with httpx.Client(
        timeout=30.0, follow_redirects=True, headers=headers,
        verify=False,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def fetch_bytes(url: str, *, respect_robots: bool = True) -> bytes:
    """Fetch a URL and return raw bytes (for images, etc.).

    Args:
        url: The URL to fetch.
        respect_robots: If True, check robots.txt before fetching.

    Returns:
        The response content as bytes.
    """
    if respect_robots and not _check_robots(url):
        raise PermissionError(f"Blocked by robots.txt: {url}")

    _apply_delay()

    headers = {"User-Agent": _get_random_ua()}
    with httpx.Client(
        timeout=30.0, follow_redirects=True, headers=headers,
        verify=False,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content
