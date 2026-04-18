"""Abstract base spider for ISP website scraping.

Each ISP spider inherits from BaseSpider and implements
the scrape() method to return raw plan data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ScrapedPage:
    """Result of scraping an ISP page."""

    isp_key: str
    url: str
    html: str = ""
    screenshot_bytes: bytes = b""
    screenshot_path: str | None = None
    plans_html: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class BaseSpider(ABC):
    """Abstract base spider for ISP websites."""

    isp_key: str
    marca: str
    url: str

    @abstractmethod
    def scrape(self) -> ScrapedPage:
        """Scrape the ISP website and return raw data.

        Returns:
            ScrapedPage with HTML, screenshot, and extracted plan dicts.
        """
        ...

    @abstractmethod
    def get_plan_urls(self) -> list[str]:
        """Return URLs of pages containing plan information.

        Returns:
            List of URLs to scrape for plan data.
        """
        ...
