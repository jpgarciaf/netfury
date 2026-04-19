"""Recursive URL crawler with depth control and cycle prevention.

Starts from seed URLs and discovers additional plan-related pages
by following links, using BFS with configurable depth, domain
filtering, and keyword-based URL relevance.

Uses Playwright-rendered HTML to handle JavaScript-heavy sites.
"""

from __future__ import annotations

import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from settings import get_settings

logger = logging.getLogger(__name__)

# Keywords that indicate a URL is likely related to ISP plans/pricing
_DEFAULT_URL_KEYWORDS = re.compile(
    r"plan|hogar|internet|precio|tarifa|fibra|residencial|producto|servicio"
    r"|home|pricing|package",
    re.IGNORECASE,
)


@dataclass
class CrawlConfig:
    """Configuration for the recursive crawler.

    Attributes:
        max_depth: Maximum link-follow depth from seed URL.
        max_pages: Maximum total pages to visit per crawl.
        url_pattern: Regex for filtering relevant URLs.
        same_domain_only: If True, only follow links on the same domain.
        wait_ms: Extra milliseconds to wait for JS rendering.
    """

    max_depth: int = 2
    max_pages: int = 10
    url_pattern: re.Pattern = field(default_factory=lambda: _DEFAULT_URL_KEYWORDS)
    same_domain_only: bool = True
    wait_ms: int = 8000


@dataclass
class CrawlResult:
    """Result from crawling a single page.

    Attributes:
        url: The URL that was crawled.
        html: Fully rendered HTML content.
        depth: Depth at which this page was discovered.
        discovered_urls: Links found on this page.
    """

    url: str
    html: str
    depth: int
    discovered_urls: list[str] = field(default_factory=list)


def _normalize_url(url: str) -> str:
    """Normalize URL for deduplication.

    Strips fragments, trailing slashes, and lowercases.
    """
    parsed = urlparse(url)
    # Rebuild without fragment, normalized
    normalized = parsed._replace(
        fragment="",
        path=parsed.path.rstrip("/") or "/",
    ).geturl()
    return normalized.lower()


def _get_domain(url: str) -> str:
    """Extract domain from URL."""
    return urlparse(url).netloc.lower()


def _extract_links(html: str, page_url: str) -> list[str]:
    """Extract all links from HTML, resolving relative URLs.

    Args:
        html: Rendered HTML content.
        page_url: URL of the page (for resolving relative links).

    Returns:
        List of absolute URLs found in <a href> tags.
    """
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(page_url, href)
        links.append(absolute)
    return links


class RecursiveCrawler:
    """BFS crawler that discovers plan-related pages from seed URLs.

    Usage:
        config = CrawlConfig(max_depth=2, max_pages=10)
        crawler = RecursiveCrawler(config)
        results = crawler.crawl(["https://www.xtrim.com.ec/"])
    """

    def __init__(self, config: CrawlConfig | None = None) -> None:
        self._config = config or CrawlConfig()
        self._visited: set[str] = set()

    def crawl(self, seed_urls: list[str]) -> list[CrawlResult]:
        """Crawl starting from seed URLs using BFS.

        Args:
            seed_urls: Initial URLs to start crawling from.

        Returns:
            List of CrawlResult for each visited page.
        """
        from extractors.full_html_extractor import _get_rendered_html

        cfg = self._config
        results: list[CrawlResult] = []
        queue: deque[tuple[str, int]] = deque()
        self._visited.clear()

        # Determine allowed domains from seed URLs
        allowed_domains = {_get_domain(u) for u in seed_urls}

        # Seed the queue
        for url in seed_urls:
            norm = _normalize_url(url)
            if norm not in self._visited:
                self._visited.add(norm)
                queue.append((url, 0))

        while queue and len(results) < cfg.max_pages:
            url, depth = queue.popleft()

            logger.info(
                "Crawling [depth=%d/%d, pages=%d/%d]: %s",
                depth, cfg.max_depth, len(results) + 1, cfg.max_pages, url,
            )

            # Fetch rendered HTML
            try:
                html = _get_rendered_html(url, wait_ms=cfg.wait_ms)
            except Exception as e:
                logger.warning("Failed to crawl %s: %s", url, e)
                continue

            if not html or len(html) < 500:
                logger.warning("Empty or too small page: %s", url)
                continue

            # Extract links for discovery
            raw_links = _extract_links(html, url)
            discovered: list[str] = []

            for link in raw_links:
                norm_link = _normalize_url(link)

                # Skip already visited
                if norm_link in self._visited:
                    continue

                # Domain filter
                if cfg.same_domain_only:
                    link_domain = _get_domain(link)
                    if link_domain not in allowed_domains:
                        continue

                # Keyword relevance filter
                if cfg.url_pattern and not cfg.url_pattern.search(link):
                    continue

                discovered.append(link)

                # Only enqueue if within depth limit
                if depth + 1 <= cfg.max_depth:
                    self._visited.add(norm_link)
                    queue.append((link, depth + 1))

            results.append(CrawlResult(
                url=url,
                html=html,
                depth=depth,
                discovered_urls=discovered,
            ))

            # Respect delay between requests
            settings = get_settings()
            import random
            delay = random.uniform(
                settings.scrape_delay_min, settings.scrape_delay_max,
            )
            if queue:  # Only delay if more pages to crawl
                time.sleep(delay)

        logger.info(
            "Crawl complete: %d pages visited, %d total URLs discovered",
            len(results),
            sum(len(r.discovered_urls) for r in results),
        )
        return results
