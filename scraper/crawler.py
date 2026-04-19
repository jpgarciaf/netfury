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
import unicodedata
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

_POSITIVE_LINK_HINTS: dict[str, float] = {
    "internet fijo": 8.0,
    "internet hogar": 8.0,
    "planes hogar": 7.0,
    "fibra optica": 7.0,
    "planes de internet": 7.0,
    "internet": 4.0,
    "hogar": 4.0,
    "fibra": 4.0,
    "fijo": 4.0,
    "plan": 3.0,
    "planes": 3.0,
    "precio": 3.0,
    "tarifa": 2.5,
    "residencial": 2.5,
    "home": 2.5,
    "pricing": 2.0,
    "package": 1.5,
}

_NEGATIVE_LINK_HINTS: dict[str, float] = {
    "movil": -8.0,
    "celular": -8.0,
    "celulares": -8.0,
    "pospago": -8.0,
    "prepago": -8.0,
    "recarga": -7.0,
    "chip": -7.0,
    "equipo": -6.0,
    "equipos": -6.0,
    "smartphone": -7.0,
    "laptop": -6.0,
    "laptops": -6.0,
    "tablet": -6.0,
    "watch": -5.0,
    "smart car": -6.0,
    "iot": -4.0,
    "empresas": -6.0,
    "negocios": -6.0,
    "corporativo": -6.0,
    "soporte": -6.0,
    "ayuda": -5.0,
    "factura": -5.0,
    "tramite": -5.0,
    "tv": -4.0,
    "television": -4.0,
    "streaming": -5.0,
    "satelital": -5.0,
    "telefonia": -6.0,
    "entretenimiento": -5.0,
    "promociones": -5.0,
    "promocion": -5.0,
    "full claro": -4.0,
    "blog": -4.0,
    "noticias": -4.0,
    "trabaja": -4.0,
    "empleo": -4.0,
    "terminos": -3.0,
    "privacidad": -3.0,
}

_SKIPPED_LINK_SUFFIXES = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
    ".mp4", ".zip", ".rar",
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
    min_relevance_score: float = 4.0


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


@dataclass
class LinkCandidate:
    """A discovered link plus semantic metadata used for prioritization."""

    url: str
    anchor_text: str
    context_text: str
    score: float


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


def _get_site_key(url: str) -> str:
    """Collapse sibling subdomains to the same site key.

    This lightweight heuristic uses the last three labels, which works for
    domains such as `www.claro.com.ec` and `catalogo.claro.com.ec`.
    """
    domain = _get_domain(url)
    parts = [part for part in domain.split(".") if part]
    if len(parts) >= 3:
        return ".".join(parts[-3:])
    return domain


def _normalize_semantic_text(*parts: str) -> str:
    """Normalize text for lightweight semantic matching."""
    joined = " ".join(p for p in parts if p)
    ascii_text = unicodedata.normalize("NFKD", joined).encode(
        "ascii", "ignore",
    ).decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _score_link(url: str, anchor_text: str, context_text: str) -> float:
    """Score a link by semantic proximity to fixed-home internet plans."""
    parsed = urlparse(url)
    url_text = re.sub(r"[/_\-]+", " ", f"{parsed.path} {parsed.query}")
    combined = _normalize_semantic_text(url_text, anchor_text, context_text)

    score = 0.0
    for hint, weight in _POSITIVE_LINK_HINTS.items():
        if hint in combined:
            score += weight

    for hint, weight in _NEGATIVE_LINK_HINTS.items():
        if hint in combined:
            score += weight

    if "internet" in combined and any(
        token in combined for token in ("hogar", "fijo", "fibra", "residencial")
    ):
        score += 4.0

    if anchor_text.strip():
        score += 0.25

    if parsed.path and parsed.path != "/":
        score += 0.1

    return score


def _extract_links(html: str, page_url: str) -> list[LinkCandidate]:
    """Extract all links from HTML, resolving relative URLs and scoring them.

    Args:
        html: Rendered HTML content.
        page_url: URL of the page (for resolving relative links).

    Returns:
        List of candidate links found in <a href> tags.
    """
    soup = BeautifulSoup(html, "lxml")
    links: list[LinkCandidate] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        absolute = urljoin(page_url, href)
        if urlparse(absolute).path.lower().endswith(_SKIPPED_LINK_SUFFIXES):
            continue

        anchor_text = " ".join(filter(None, [
            anchor.get_text(" ", strip=True),
            anchor.get("title", ""),
            anchor.get("aria-label", ""),
        ]))

        parent_text = ""
        if anchor.parent:
            parent_text = anchor.parent.get_text(" ", strip=True)
        if parent_text == anchor_text and anchor.parent and anchor.parent.parent:
            parent_text = anchor.parent.parent.get_text(" ", strip=True)

        context_text = parent_text[:240]
        links.append(LinkCandidate(
            url=absolute,
            anchor_text=anchor_text,
            context_text=context_text,
            score=_score_link(absolute, anchor_text, context_text),
        ))
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
        allowed_domains = {_get_site_key(u) for u in seed_urls}

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
            raw_links = sorted(
                _extract_links(html, url),
                key=lambda candidate: candidate.score,
                reverse=True,
            )
            discovered: list[str] = []

            for candidate in raw_links:
                link = candidate.url
                norm_link = _normalize_url(link)

                # Skip already visited
                if norm_link in self._visited:
                    continue

                # Domain filter
                if cfg.same_domain_only:
                    link_domain = _get_site_key(link)
                    if link_domain not in allowed_domains:
                        continue

                # Keyword relevance filter
                link_text = " ".join((
                    candidate.url,
                    candidate.anchor_text,
                    candidate.context_text,
                ))
                if cfg.url_pattern and not cfg.url_pattern.search(link_text):
                    continue

                if candidate.score < cfg.min_relevance_score:
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
