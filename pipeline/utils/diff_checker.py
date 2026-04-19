"""Utility to detect differences between HTML and image files.

Uses difflib for text comparison and SHA-256 hashing for images.
"""

import hashlib
import logging
from difflib import unified_diff
from pathlib import Path

logger = logging.getLogger(__name__)


def get_html_diff_chunks(new_html: str, old_html_path: str | Path) -> str | None:
    """Compare new HTML against a saved file and return the diff.

    Args:
        new_html: The current HTML content.
        old_html_path: Path to the previous HTML snapshot.

    Returns:
        Unified diff string if changes exist, None otherwise.
    """
    old_path = Path(old_html_path)
    if not old_path.exists():
        logger.info("Previous HTML snapshot not found at %s. Treating as new.", old_path)
        return new_html  # Treaty full HTML as a "change" if no previous exists

    try:
        old_html = old_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read previous HTML snapshot: %s", e)
        return new_html

    if new_html == old_html:
        return None

    # Generate unified diff
    diff = list(
        unified_diff(
            old_html.splitlines(keepends=True),
            new_html.splitlines(keepends=True),
            fromfile="previous",
            tofile="current",
            n=3,  # Context lines
        )
    )

    if not diff:
        return None

    return "".join(diff)


def has_image_changed(new_image_bytes: bytes, old_image_path: str | Path) -> bool:
    """Check if an image has changed using SHA-256 hashing.

    Args:
        new_image_bytes: Bytes of the current screenshot.
        old_image_path: Path to the previous screenshot.

    Returns:
        True if the image is different or previous doesn't exist.
    """
    old_path = Path(old_image_path)
    if not old_path.exists():
        logger.info("Previous screenshot not found at %s. Treating as changed.", old_path)
        return True

    try:
        old_image_bytes = old_path.read_bytes()
    except Exception as e:
        logger.warning("Failed to read previous screenshot: %s", e)
        return True

    new_hash = hashlib.sha256(new_image_bytes).hexdigest()
    old_hash = hashlib.sha256(old_image_bytes).hexdigest()

    return new_hash != old_hash
