"""HTML-based extraction strategy using BeautifulSoup.

Free, fast, but fragile -- depends on HTML structure of each ISP.
Falls back gracefully when selectors don't match.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from extractors.guardrails import validate_and_build_plans
from schemas.plan import PlanISP

logger = logging.getLogger(__name__)


def _extract_number(text: str) -> float | None:
    """Extract the first numeric value from text.

    Args:
        text: String potentially containing a number.

    Returns:
        Float value or None if no number found.
    """
    if not text:
        return None
    match = re.search(r"(\d+[.,]?\d*)", text.replace(",", "."))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def extract_plans_from_html(
    html: str,
    isp_key: str,
    *,
    selectors: dict | None = None,
) -> tuple[list[PlanISP], list[str]]:
    """Extract ISP plans from HTML using CSS selectors.

    Args:
        html: Raw HTML content.
        isp_key: ISP identifier.
        selectors: Optional custom CSS selectors for this ISP.
            Expected keys: plan_cards, name, speed, price.

    Returns:
        Tuple of (valid PlanISP list, error messages).
    """
    soup = BeautifulSoup(html, "lxml")
    now = datetime.now()

    # Default selectors (work for many ISPs with card-based layouts)
    sel = selectors or _get_default_selectors(isp_key)

    cards = soup.select(sel.get("plan_cards", ".plan-card, .card, .plan"))
    if not cards:
        logger.info("No plan cards found for %s with HTML selectors", isp_key)
        return [], ["No plan cards found in HTML"]

    raw_plans: list[dict] = []
    for card in cards:
        plan_data: dict = {}

        # Plan name
        name_el = card.select_one(sel.get("name", "h2, h3, .plan-name, .title"))
        if name_el:
            plan_data["nombre_plan"] = name_el.get_text(strip=True)

        # Speed
        speed_el = card.select_one(sel.get("speed", ".speed, .velocidad, .mbps"))
        if speed_el:
            speed = _extract_number(speed_el.get_text())
            if speed:
                plan_data["velocidad_download_mbps"] = speed

        # Price
        price_el = card.select_one(sel.get("price", ".price, .precio, .amount"))
        if price_el:
            price = _extract_number(price_el.get_text())
            if price:
                plan_data["precio_plan"] = price

        # Only add if we have at least name or speed+price
        if plan_data.get("nombre_plan") or (
            plan_data.get("velocidad_download_mbps")
            and plan_data.get("precio_plan")
        ):
            # Ensure required fields have defaults
            plan_data.setdefault("nombre_plan", "Plan sin nombre")
            plan_data.setdefault("velocidad_download_mbps", 0)
            plan_data.setdefault("precio_plan", 0)
            raw_plans.append(plan_data)

    plans, errors = validate_and_build_plans(raw_plans, isp_key, now)
    logger.info("HTML extracted %d plans from %s", len(plans), isp_key)
    return plans, errors


def _get_default_selectors(isp_key: str) -> dict[str, str]:
    """Get CSS selectors customized per ISP.

    Args:
        isp_key: ISP identifier.

    Returns:
        Dict with CSS selector strings.
    """
    selectors: dict[str, dict[str, str]] = {
        "xtrim": {
            "plan_cards": ".plan-card, .card, [class*='plan']",
            "name": "h2, h3, .plan-name, .card-title",
            "speed": ".speed, .mbps, [class*='velocidad'], [class*='speed']",
            "price": ".price, .precio, [class*='price'], [class*='precio']",
        },
        "netlife": {
            "plan_cards": ".plan, .card, [class*='plan']",
            "name": "h2, h3, .plan-title",
            "speed": "[class*='speed'], [class*='megas'], [class*='mbps']",
            "price": "[class*='price'], [class*='precio'], .amount",
        },
        "cnt": {
            "plan_cards": ".plan-item, .card, [class*='plan']",
            "name": "h3, h4, .plan-name",
            "speed": "[class*='velocidad'], [class*='mbps']",
            "price": "[class*='precio'], [class*='price']",
        },
    }
    return selectors.get(isp_key, selectors["xtrim"])
