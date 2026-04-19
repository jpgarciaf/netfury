"""Banner image discovery and download from ISP websites.

Finds promotional images (plan cards, pricing banners) in rendered
HTML and downloads them individually for per-image LLM analysis.

Applies heuristics to filter out logos, icons, and tracking pixels.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from scraper.utils.http_client import fetch_bytes

logger = logging.getLogger(__name__)

# Keywords indicating an image is related to plans/pricing
_RELEVANCE_KEYWORDS = re.compile(
    r"plan|precio|tarifa|promo|banner|hero|oferta|velocidad|mbps|megas"
    r"|hogar|internet|fibra|card|slider|carousel",
    re.IGNORECASE,
)

# URL patterns to skip (logos, social icons, tracking)
_SKIP_PATTERNS = re.compile(
    r"logo|favicon|icon|social|facebook|twitter|instagram|linkedin"
    r"|whatsapp|youtube|tracking|pixel|analytics|badge|avatar"
    r"|sprite|arrow|chevron|close|search|menu|hamburger",
    re.IGNORECASE,
)

# Image extensions
_IMAGE_EXTENSIONS = re.compile(
    r"\.(jpg|jpeg|png|webp|gif|svg|avif)(\?|$)",
    re.IGNORECASE,
)


@dataclass
class DiscoveredImage:
    """An image discovered in an ISP page, ready for LLM analysis.

    Attributes:
        url: Absolute URL of the image.
        alt_text: Alt text from the img tag.
        context_text: Surrounding text from parent elements.
        image_bytes: Downloaded image content.
        width: Image width from HTML attributes (if available).
        height: Image height from HTML attributes (if available).
    """

    url: str
    alt_text: str
    context_text: str
    image_bytes: bytes
    width: int | None = None
    height: int | None = None


def _get_element_context(element: Tag, max_chars: int = 200) -> str:
    """Extract text context from parent elements.

    Args:
        element: The img tag.
        max_chars: Maximum characters to collect.

    Returns:
        Text from parent/sibling elements.
    """
    texts = []
    # Check parent and grandparent for text
    for parent in [element.parent, element.parent.parent if element.parent else None]:
        if parent and hasattr(parent, "get_text"):
            text = parent.get_text(separator=" ", strip=True)
            if text and len(text) > 3:
                texts.append(text[:max_chars])
                break
    return " ".join(texts)[:max_chars]


def _get_int_attr(element: Tag, attr: str) -> int | None:
    """Safely extract an integer attribute from an HTML element."""
    val = element.get(attr)
    if val:
        try:
            return int(str(val).replace("px", ""))
        except (ValueError, TypeError):
            return None
    return None


def _is_relevant_image(
    img: Tag,
    src: str,
    context: str,
) -> bool:
    """Determine if an image is likely related to ISP plan/pricing.

    Uses heuristics on src URL, alt text, CSS classes, and context.
    """
    # Skip known non-content patterns
    if _SKIP_PATTERNS.search(src):
        return False

    # Check size constraints from HTML attributes
    width = _get_int_attr(img, "width")
    height = _get_int_attr(img, "height")
    if width is not None and width < 80:
        return False
    if height is not None and height < 40:
        return False

    # Check relevance signals
    alt = img.get("alt", "")
    classes = " ".join(img.get("class", []))
    parent_classes = ""
    if img.parent:
        parent_classes = " ".join(img.parent.get("class", []))

    searchable = f"{src} {alt} {classes} {parent_classes} {context}"
    return bool(_RELEVANCE_KEYWORDS.search(searchable))


class ImageDiscoverer:
    """Discovers and downloads relevant banner images from ISP pages.

    Usage:
        discoverer = ImageDiscoverer()
        images = discoverer.discover_images(html, "https://www.xtrim.com.ec/")
    """

    def discover_images(
        self,
        html: str,
        page_url: str,
        *,
        max_images: int = 15,
    ) -> list[DiscoveredImage]:
        """Find and download relevant images from rendered HTML.

        Args:
            html: Fully rendered HTML content.
            page_url: URL of the page (for resolving relative URLs).
            max_images: Maximum images to return.

        Returns:
            List of DiscoveredImage objects with downloaded bytes.
        """
        soup = BeautifulSoup(html, "lxml")
        candidates: list[tuple[str, str, str, int | None, int | None]] = []
        seen_urls: set[str] = set()

        # 1. Standard <img> tags
        for img in soup.find_all("img", src=True):
            src = urljoin(page_url, img["src"])
            if src in seen_urls:
                continue
            if not _IMAGE_EXTENSIONS.search(src):
                continue

            context = _get_element_context(img)
            if _is_relevant_image(img, src, context):
                seen_urls.add(src)
                candidates.append((
                    src,
                    img.get("alt", ""),
                    context,
                    _get_int_attr(img, "width"),
                    _get_int_attr(img, "height"),
                ))

        # 2. <picture> / <source> tags
        for source in soup.find_all("source", srcset=True):
            srcset = source["srcset"].split(",")[0].strip().split(" ")[0]
            src = urljoin(page_url, srcset)
            if src in seen_urls:
                continue
            if not _IMAGE_EXTENSIONS.search(src):
                continue

            parent_img = source.find_parent("picture")
            context = _get_element_context(source)
            if parent_img:
                context = _get_element_context(parent_img)

            if _is_relevant_image(source, src, context):
                seen_urls.add(src)
                candidates.append((src, "", context, None, None))

        # 3. CSS background-image on plan-related containers
        for el in soup.find_all(style=re.compile(r"background-image")):
            style = el.get("style", "")
            bg_match = re.search(r"url\(['\"]?([^'\"]+?)['\"]?\)", style)
            if bg_match:
                src = urljoin(page_url, bg_match.group(1))
                if src in seen_urls:
                    continue
                if not _IMAGE_EXTENSIONS.search(src):
                    continue

                context = _get_element_context(el)
                if _RELEVANCE_KEYWORDS.search(f"{src} {context}"):
                    seen_urls.add(src)
                    candidates.append((src, "", context, None, None))

        # Download images (up to max_images)
        results: list[DiscoveredImage] = []
        for src, alt, context, w, h in candidates[:max_images * 2]:
            if len(results) >= max_images:
                break
            try:
                image_bytes = fetch_bytes(src, respect_robots=False)
                # Skip very small files (likely icons/placeholders)
                if len(image_bytes) < 2000:
                    continue
                results.append(DiscoveredImage(
                    url=src,
                    alt_text=alt,
                    context_text=context,
                    image_bytes=image_bytes,
                    width=w,
                    height=h,
                ))
            except Exception as e:
                logger.debug("Failed to download %s: %s", src, e)

        logger.info(
            "Discovered %d relevant images from %s (of %d candidates)",
            len(results), page_url, len(candidates),
        )
        return results
