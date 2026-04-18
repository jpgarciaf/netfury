"""Enhanced HTML extractor using Playwright-rendered DOM.

Extracts all 30+ fields from ISP websites using ISP-specific parsers.
Uses Playwright to get fully rendered HTML (after JS execution),
then BeautifulSoup for structured parsing.

This file extends the extraction capability without modifying
existing extractors.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import sync_playwright

from extractors.guardrails import validate_and_build_plans
from schemas.plan import PlanISP
from settings import ISP_COMPANY_MAP, get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Playwright: get rendered HTML
# ---------------------------------------------------------------------------

def _get_rendered_html(url: str, *, wait_ms: int = 8000) -> str:
    """Fetch fully rendered HTML using Playwright.

    Args:
        url: Page URL.
        wait_ms: Extra wait after networkidle for JS rendering.

    Returns:
        Rendered HTML string.
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
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(wait_ms)
        # Scroll to trigger lazy loading
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)
        html = page.content()
        context.close()
        browser.close()
    return html


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_number(text: str) -> float | None:
    """Extract first numeric value from text."""
    if not text:
        return None
    cleaned = text.replace(",", ".").replace("\xa0", "")
    match = re.search(r"(\d+\.?\d*)", cleaned)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _price_sin_iva(price_con_iva: float) -> float:
    """Convert price con IVA (15%) to sin IVA."""
    return round(price_con_iva / 1.15, 2)


def _to_snake_case(name: str) -> str:
    """Convert string to snake_case (must start with letter)."""
    s = name.lower().strip()
    s = re.sub(r"[+]", "_plus", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    # Ensure starts with a letter (snake_case requirement)
    if s and not s[0].isalpha():
        s = "svc_" + s
    return s


def _get_text(el: Tag | None) -> str:
    """Safely get text from a BS4 element."""
    return el.get_text(strip=True) if el else ""


# ---------------------------------------------------------------------------
# ISP-specific parsers
# ---------------------------------------------------------------------------

def _parse_xtrim(html: str) -> list[dict]:
    """Parse Xtrim plan cards from rendered HTML.

    Xtrim uses Next.js with data-testid attributes on plan elements.
    """
    soup = BeautifulSoup(html, "lxml")
    plans: list[dict] = []

    cards = soup.find_all(attrs={"data-testid": "plan-card-wrapper"})
    if not cards:
        # Fallback: try finding by class pattern
        cards = soup.find_all("div", class_=re.compile(r"rounded-2xl.*shadow"))

    for card in cards:
        plan: dict = {"tecnologia": "fibra_optica"}

        # Speed
        speed_el = card.find(attrs={"data-testid": "plan-card-speed-value"})
        if speed_el:
            speed = _extract_number(_get_text(speed_el))
            if speed:
                plan["velocidad_download_mbps"] = speed

        # Plan name
        name_el = card.find(attrs={"data-testid": "plan-card-name"})
        if name_el:
            plan["nombre_plan"] = _get_text(name_el)

        # Price
        amount_el = card.find(attrs={"data-testid": "plan-card-amount"})
        if amount_el:
            price_text = _get_text(amount_el).replace("*", "")
            price = _extract_number(price_text)
            if price:
                plan["precio_plan"] = price

        # Tax info — if "+ imp." means price is sin IVA already
        tax_el = card.find(attrs={"data-testid": "plan-card-tax"})
        if tax_el and "imp" in _get_text(tax_el).lower():
            pass  # Price is already sin IVA

        # Promo / free invoices
        promo_el = card.find(attrs={"data-testid": "plan-card-promo-label"})
        if promo_el:
            promo_text = _get_text(promo_el).lower()
            if "factura" in promo_text and "gratis" in promo_text:
                match = re.search(r"(\w+)\s+factura", promo_text)
                ordinal_map = {
                    "primera": 1, "segunda": 2, "tercera": 3,
                    "cuarta": 4, "quinta": 5,
                }
                if match:
                    plan["facturas_gratis"] = ordinal_map.get(match.group(1), 1)

        # Benefits
        benefits = []
        benefit_items = card.find_all(attrs={"data-testid": re.compile(r"benefit-item")})
        for item in benefit_items:
            text = _get_text(item)
            if text:
                benefits.append(text)

        # Additional services (apps)
        pys_detalle: dict = {}
        apps_container = card.find(attrs={"data-testid": "apps-container"})
        if apps_container:
            app_items = apps_container.find_all(
                attrs={"data-testid": re.compile(r"app-item")},
            )
            for app in app_items:
                app_text = _get_text(app).strip()
                if not app_text:
                    continue
                # Classify the service
                text_lower = app_text.lower()
                if "disney" in text_lower:
                    key = "disney_plus"
                    categoria = "streaming"
                    tipo = "disney_plus_premium" if "premium" in text_lower else "disney_plus_basic"
                elif "zapping" in text_lower:
                    key = "zapping"
                    categoria = "streaming"
                    tipo = "zapping_basico"
                elif "liga" in text_lower or "ecuabet" in text_lower:
                    key = "liga_ecuabet"
                    categoria = "streaming"
                    tipo = "liga_ecuabet"
                elif "instalaci" in text_lower:
                    if "gratis" in text_lower:
                        plan["costo_instalacion"] = 0.0
                    benefits.append(app_text)
                    continue
                elif "router" in text_lower:
                    benefits.append(app_text)
                    continue
                else:
                    key = _to_snake_case(app_text)
                    categoria = "otros"
                    tipo = _to_snake_case(app_text)

                pys_detalle[key] = {
                    "tipo_plan": tipo,
                    "meses": None,
                    "categoria": categoria,
                }

        if pys_detalle:
            plan["pys_adicionales_detalle"] = pys_detalle
            plan["pys_adicionales"] = len(pys_detalle)

        if benefits:
            plan["beneficios_publicitados"] = "; ".join(benefits)

        # Legal text
        legal_el = card.find(attrs={"data-testid": "plan-card-legal"})
        if legal_el:
            plan["terminos_condiciones"] = _get_text(legal_el)

        # Only add if we have meaningful data
        if plan.get("nombre_plan") or plan.get("velocidad_download_mbps"):
            plan.setdefault("nombre_plan", f"Plan {plan.get('velocidad_download_mbps', 0):.0f} Mbps")
            plans.append(plan)

    return plans


def _parse_netlife(html: str) -> list[dict]:
    """Parse Netlife plan cards from rendered HTML.

    Netlife uses a WordPress/Elementor setup with custom CSS classes.
    """
    soup = BeautifulSoup(html, "lxml")
    plans: list[dict] = []

    # Find plan detail blocks (blockDES1, blockDES2, blockDES3)
    detail_blocks = soup.find_all(
        "div", class_="contenedorPlanes2025",
    )

    # Also find carousel cards for pricing
    carousel_cards = soup.find_all("figure", id=re.compile(r"plan\d+"))

    for idx, card in enumerate(carousel_cards):
        plan: dict = {"tecnologia": "fibra_optica", "comparticion": "2:1"}

        # Speed from nombrePlan
        speed_div = card.find("div", class_="nombrePlan")
        if speed_div:
            speed_text = _get_text(speed_div)
            speed = _extract_number(re.sub(r"[^\d]", " ", speed_text).strip())
            if speed:
                plan["velocidad_download_mbps"] = speed

        # Promotional speed (if there's a "nuevaVel" span)
        nueva_vel = card.find("span", class_="nuevaVel")
        if nueva_vel:
            promo_speed = _extract_number(_get_text(nueva_vel))
            if promo_speed:
                plan["velocidad_download_mbps"] = promo_speed

        # Price without IVA
        valor_el = card.find("span", class_="valor")
        if valor_el:
            full_text = _get_text(valor_el).replace("$", "")
            # Combine integer + centavo
            centavo = valor_el.find("span", class_="centavoValor")
            if centavo:
                int_text = valor_el.get_text().split(".")[0].replace("$", "").strip()
                dec_text = _get_text(centavo)
                try:
                    price_sin_iva = float(f"{_extract_number(int_text)}.{dec_text}")
                    plan["precio_plan"] = price_sin_iva
                except (ValueError, TypeError):
                    price = _extract_number(full_text)
                    if price:
                        plan["precio_plan"] = price
            else:
                price = _extract_number(full_text)
                if price:
                    plan["precio_plan"] = price

        # Price with IVA
        valor_iva = card.find("span", class_="valorIva")
        if valor_iva:
            iva_text = _get_text(valor_iva)
            centavo_iva = valor_iva.find("span", class_="centavoValor")
            if centavo_iva:
                parts = iva_text.split("$")
                if len(parts) > 1:
                    num_part = parts[-1]
                    price_iva = _extract_number(num_part)
                    if price_iva:
                        dec = _get_text(centavo_iva)
                        try:
                            plan["precio_plan_tarjeta"] = float(
                                f"{int(price_iva)}.{dec}",
                            )
                        except ValueError:
                            pass

        # Discount info
        desc_div = card.find("div", class_="desDescuento")
        if desc_div:
            desc_text = _get_text(desc_div)
            # Extract discount percentage
            pct_match = re.search(r"(\d+)%", desc_text)
            if pct_match:
                plan["descuento"] = float(pct_match.group(1))
            # Extract months
            meses_match = re.search(r"(\d+)\s*primera", desc_text)
            if meses_match:
                plan["meses_descuento"] = int(meses_match.group(1))
            elif "6 primeras" in desc_text.lower():
                plan["meses_descuento"] = 6

            # Payment method
            if "tarjeta" in desc_text.lower():
                plan["terminos_condiciones"] = (
                    plan.get("terminos_condiciones", "")
                    + "Descuento aplica con tarjeta de crédito. "
                )

        # Detailed block features
        if idx < len(detail_blocks):
            block = detail_blocks[idx]

            # Features list
            features = block.find_all("div", class_="caractersticasPlan")
            benefits = []
            for feat_div in features:
                items = feat_div.find_all("li")
                for li in items:
                    text = _get_text(li)
                    if not text:
                        continue
                    text_lower = text.lower()

                    if "compartición" in text_lower or "comparticion" in text_lower:
                        ratio_match = re.search(r"(\d+:\d+)", text)
                        if ratio_match:
                            plan["comparticion"] = ratio_match.group(1)

                    elif "velocidad mínima" in text_lower and "carga" not in text_lower:
                        pass  # Minimum download speed

                    elif "velocidad máxima" in text_lower and "carga" in text_lower:
                        upload = _extract_number(text)
                        if upload:
                            plan["velocidad_upload_mbps"] = upload

                    elif "velocidad mínima" in text_lower and "carga" in text_lower:
                        pass  # Minimum upload speed

                    elif "xgpon" in text_lower or "fibra" in text_lower:
                        plan["tecnologia"] = "fibra_optica"

                    elif "servicio" in text_lower and "digital" in text_lower:
                        num = _extract_number(text)
                        if num:
                            plan["pys_adicionales"] = int(num)

                    else:
                        benefits.append(text)

            # Final price without promotion
            final_price = block.find("span", class_="precioFinalPlan")
            if final_price:
                fp_text = _get_text(final_price)
                fp_match = re.search(r"\$(\d+)\.?\s*(\d{2})", fp_text.replace(",", "."))
                if fp_match:
                    price_iva = float(f"{fp_match.group(1)}.{fp_match.group(2)}")
                    plan["precio_plan"] = _price_sin_iva(price_iva)

            # Digital service options — collect unique services from all combos
            pys_detalle: dict = {}
            serv_boxes = block.find_all("div", class_="servBox")
            for serv in serv_boxes:
                radio = serv.find("input", {"type": "radio"})
                if radio:
                    serv_value = radio.get("value", "")
                    if serv_value:
                        for svc_name in serv_value.split("+"):
                            svc_name = svc_name.strip()
                            if not svc_name:
                                continue
                            key = _to_snake_case(svc_name)
                            if key in pys_detalle:
                                continue  # Skip duplicates
                            svc_lower = svc_name.lower()
                            if "paramount" in svc_lower:
                                cat = "streaming"
                            elif "play" in svc_lower:
                                cat = "streaming"
                            elif "extender" in svc_lower:
                                cat = "conectividad"
                            elif "defense" in svc_lower:
                                cat = "seguridad"
                            elif "assistance" in svc_lower:
                                cat = "soporte"
                            else:
                                cat = "otros"
                            pys_detalle[key] = {
                                "tipo_plan": _to_snake_case(svc_name),
                                "meses": None,
                                "categoria": cat,
                            }

            if pys_detalle:
                plan["pys_adicionales_detalle"] = pys_detalle
                plan["pys_adicionales"] = max(
                    plan.get("pys_adicionales", 0), len(pys_detalle),
                )

            if benefits:
                plan["beneficios_publicitados"] = "; ".join(benefits)

        # Plan name
        speed = plan.get("velocidad_download_mbps", 0)
        titulo = card.find("div", class_="tituloPlanDes")
        if titulo:
            plan["nombre_plan"] = _get_text(titulo)
        else:
            plan["nombre_plan"] = f"Plan {speed:.0f} Mbps"

        if plan.get("velocidad_download_mbps"):
            plans.append(plan)

    return plans


def _parse_ecuanet(html: str) -> list[dict]:
    """Parse Ecuanet plan cards from rendered HTML.

    Ecuanet uses WordPress + Elementor price-table widgets.
    Actual prices are in the feature list items, not in the price-table header.
    """
    soup = BeautifulSoup(html, "lxml")
    plans: list[dict] = []

    tables = soup.find_all("div", class_="elementor-price-table")

    # Find installation cost from the page
    costo_instalacion = None
    for p_tag in soup.find_all(["p", "span", "div"]):
        text = _get_text(p_tag)
        if "instalaci" in text.lower() and "$" in text:
            price = _extract_number(text.split("$")[-1])
            if price and price > 50:
                costo_instalacion = price
                break

    for table in tables:
        plan: dict = {
            "tecnologia": "fibra_optica",
            "comparticion": "2:1",
        }
        if costo_instalacion:
            plan["costo_instalacion"] = costo_instalacion

        # Plan name / speed from heading
        heading = table.find("h3", class_="elementor-price-table__heading")
        if heading:
            heading_text = _get_text(heading)
            speed = _extract_number(heading_text)
            if speed:
                plan["velocidad_download_mbps"] = speed
                plan["nombre_plan"] = f"Plan {speed:.0f} Mbps"
            else:
                plan["nombre_plan"] = heading_text

        # Header price (promotional display price, con IVA)
        integer_part = table.find(
            "span", class_="elementor-price-table__integer-part",
        )
        fractional_part = table.find(
            "span", class_="elementor-price-table__fractional-part",
        )
        if integer_part:
            int_val = _get_text(integer_part)
            dec_val = _get_text(fractional_part).replace("*", "") if fractional_part else "00"
            try:
                header_price = float(f"{int_val}.{dec_val}")
                # Use as promotional price (con IVA)
                plan["precio_plan_descuento"] = _price_sin_iva(header_price)
            except ValueError:
                pass

        # Period text
        period = table.find("span", class_="elementor-price-table__period")
        if period:
            period_text = _get_text(period)
            if period_text:
                plan["terminos_condiciones"] = period_text

        # Features list — real prices and details are here
        features = table.find_all("li")
        benefits = []
        for li in features:
            text = _get_text(li)
            if not text:
                continue
            text_lower = text.lower()

            # Promotional price (con IVA)
            if ("promocion" in text_lower or "promo" in text_lower) and "$" in text:
                price_match = re.search(r"\$(\d+[.,]\d{2})", text)
                if price_match:
                    promo_price = float(price_match.group(1).replace(",", "."))
                    plan["precio_plan_descuento"] = _price_sin_iva(promo_price)

            # Discount percentage
            elif "descuento" in text_lower or "dcto" in text_lower:
                pct = re.search(r"(\d+)%", text)
                if pct:
                    plan["descuento"] = float(pct.group(1))
                meses = re.search(r"(\d+)\s*primera", text)
                if meses:
                    plan["meses_descuento"] = int(meses.group(1))

            # Final price / Normal price (con IVA)
            elif "$" in text and (
                "final" in text_lower
                or "normal" in text_lower
                or "sin promoci" in text_lower
            ):
                price_match = re.search(r"\$(\d+[.,]\d{2})", text)
                if price_match:
                    final_price = float(price_match.group(1).replace(",", "."))
                    plan["precio_plan"] = _price_sin_iva(final_price)

            # Comparticion
            elif "compartici" in text_lower:
                ratio = re.search(r"(\d+:\d+)", text)
                if ratio:
                    plan["comparticion"] = ratio.group(1)

            # Speed details
            elif "velocidad máxima" in text_lower or "velocidad maxima" in text_lower:
                spd = _extract_number(text)
                if spd:
                    if "carga" in text_lower or "subida" in text_lower:
                        plan["velocidad_upload_mbps"] = spd

            elif "velocidad mínima" in text_lower or "velocidad minima" in text_lower:
                pass  # Minimum guaranteed speed

            elif "$" in text and "precio" in text_lower:
                # Generic price line — use as base price if not yet set
                price_match = re.search(r"\$(\d+[.,]\d{2})", text)
                if price_match and "precio_plan" not in plan:
                    base_price = float(price_match.group(1).replace(",", "."))
                    plan["precio_plan"] = _price_sin_iva(base_price)

            else:
                if len(text) > 3:
                    benefits.append(text)

        # If no precio_plan found but we have descuento price, use header
        if "precio_plan" not in plan and "precio_plan_descuento" in plan:
            plan["precio_plan"] = plan["precio_plan_descuento"]

        if benefits:
            plan["beneficios_publicitados"] = "; ".join(benefits)

        # Ribbon / popular badge
        ribbon = table.find("div", class_="elementor-price-table__ribbon-inner")
        if ribbon:
            plan["beneficios_publicitados"] = (
                f"[{_get_text(ribbon)}] "
                + plan.get("beneficios_publicitados", "")
            )

        if plan.get("velocidad_download_mbps") and plan.get("precio_plan"):
            plans.append(plan)

    return plans


def _parse_alfanet(html: str) -> list[dict]:
    """Parse Alfanet plan cards from rendered HTML.

    Alfanet uses Odoo with less structured HTML.
    Prices use commas as decimal separators: $21,74 +IVA.
    """
    soup = BeautifulSoup(html, "lxml")
    plans: list[dict] = []

    # Alfanet uses comma decimals: $21,74
    price_pattern = re.compile(r"\$\s*(\d+[.,]\d{2})")
    speed_pattern = re.compile(r"(\d+)\s*(Mbps|megas|MEGAS|MB)", re.IGNORECASE)

    all_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in all_text.split("\n") if l.strip()]

    prices = []
    speeds = []
    plan_names = []
    seen_speeds = set()

    for line in lines:
        # Prices — look for $XX,XX or $XX.XX
        if price_pattern.search(line):
            match = price_pattern.search(line)
            if match:
                val = float(match.group(1).replace(",", "."))
                if 5 < val < 200:
                    prices.append(val)

        # Speeds from text (e.g. "1000 Mbps")
        spd_match = speed_pattern.search(line)
        if spd_match:
            spd = float(spd_match.group(1))
            if spd >= 50 and spd not in seen_speeds:
                speeds.append(spd)
                seen_speeds.add(spd)

        # Plan names
        line_lower = line.lower()
        if "plan" in line_lower and len(line) < 80:
            if "hogar" in line_lower or "gamer" in line_lower or "negocio" in line_lower:
                plan_names.append(line)

    # Speeds from styled spans (Alfanet renders "1000" in large font + "Megas" separately)
    for span in soup.find_all("span", style=True):
        style = span.get("style", "")
        if "font-size" in style:
            text = _get_text(span)
            if text.isdigit():
                spd = float(text)
                if spd >= 50 and spd not in seen_speeds:
                    # Check if "Megas" is nearby (next sibling or parent)
                    next_text = ""
                    for sib in span.next_siblings:
                        next_text = _get_text(sib) if hasattr(sib, "get_text") else str(sib)
                        if next_text.strip():
                            break
                    parent_text = _get_text(span.parent) if span.parent else ""
                    if ("mega" in next_text.lower()
                            or "mbps" in next_text.lower()
                            or "mega" in parent_text.lower()
                            or "mbps" in parent_text.lower()):
                        speeds.append(spd)
                        seen_speeds.add(spd)

    # Pair speeds with prices
    n = min(len(prices), len(speeds))
    for i in range(n):
        plan: dict = {
            "tecnologia": "fibra_optica",
            "velocidad_download_mbps": speeds[i],
            "precio_plan": prices[i],
            "nombre_plan": plan_names[i] if i < len(plan_names) else f"Plan {speeds[i]:.0f} Mbps",
        }
        plans.append(plan)

    return plans


def _parse_fibramax(html: str) -> list[dict]:
    """Parse Fibramax plan cards from rendered HTML.

    Fibramax uses WordPress + Elementor. Plan data is often in images,
    but some text is extractable.
    """
    soup = BeautifulSoup(html, "lxml")
    plans: list[dict] = []

    all_text = soup.get_text(separator="\n")
    price_pattern = re.compile(r"\$\s*(\d+[.,]\d{2})")
    speed_pattern = re.compile(r"(\d+)\s*(Mbps|megas|MEGAS|MEGA)", re.IGNORECASE)

    prices = []
    speeds = []
    plan_names = []

    lines = [l.strip() for l in all_text.split("\n") if l.strip()]
    for line in lines:
        price_match = price_pattern.search(line)
        if price_match:
            val = float(price_match.group(1).replace(",", "."))
            if 10 < val < 200:  # Reasonable ISP price range
                prices.append(val)

        spd_match = speed_pattern.search(line)
        if spd_match:
            spd = float(spd_match.group(1))
            if spd >= 50:  # Reasonable speed
                speeds.append(spd)

        if "plan" in line.lower() and "hogar" in line.lower():
            plan_names.append(line.strip())

    # Try elementor widgets
    headings = soup.find_all(
        "h2", class_=re.compile(r"elementor-heading"),
    )
    for h in headings:
        text = _get_text(h)
        spd_match = speed_pattern.search(text)
        if spd_match:
            spd = float(spd_match.group(1))
            if spd not in speeds and spd >= 50:
                speeds.append(spd)

    n = min(len(prices), len(speeds))
    for i in range(n):
        plan: dict = {
            "tecnologia": "fibra_optica",
            "velocidad_download_mbps": speeds[i],
            "precio_plan": prices[i],
            "nombre_plan": plan_names[i] if i < len(plan_names) else f"Plan {speeds[i]:.0f} Mbps",
        }
        plans.append(plan)

    return plans


def _parse_claro(html: str) -> list[dict]:
    """Parse Claro plan cards from rendered HTML."""
    soup = BeautifulSoup(html, "lxml")
    plans: list[dict] = []

    all_text = soup.get_text(separator="\n")
    price_pattern = re.compile(r"\$\s*(\d+[.,]\d{2})")
    speed_pattern = re.compile(r"(\d+)\s*(Mbps|megas|MEGAS)", re.IGNORECASE)

    prices = []
    speeds = []

    for line in all_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        price_match = price_pattern.search(line)
        if price_match:
            val = float(price_match.group(1).replace(",", "."))
            if 10 < val < 200:
                prices.append(val)

        spd_match = speed_pattern.search(line)
        if spd_match:
            spd = float(spd_match.group(1))
            if spd >= 50:
                speeds.append(spd)

    n = min(len(prices), len(speeds))
    for i in range(n):
        plans.append({
            "tecnologia": "fibra_optica",
            "velocidad_download_mbps": speeds[i],
            "precio_plan": prices[i],
            "nombre_plan": f"Plan {speeds[i]:.0f} Mbps",
        })

    return plans


def _parse_cnt(html: str) -> list[dict]:
    """Parse CNT plan cards from rendered HTML."""
    return _parse_claro(html)  # Same generic approach


def _parse_puntonet(html: str) -> list[dict]:
    """Parse Puntonet plan cards from rendered HTML."""
    return _parse_claro(html)  # Same generic approach


# ---------------------------------------------------------------------------
# Parser registry
# ---------------------------------------------------------------------------

_PARSERS: dict[str, callable] = {
    "xtrim": _parse_xtrim,
    "netlife": _parse_netlife,
    "ecuanet": _parse_ecuanet,
    "alfanet": _parse_alfanet,
    "fibramax": _parse_fibramax,
    "claro": _parse_claro,
    "cnt": _parse_cnt,
    "puntonet": _parse_puntonet,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_plans_full_html(
    urls: list[str],
    isp_key: str,
    *,
    html_override: str | None = None,
) -> tuple[list[PlanISP], list[str]]:
    """Extract all plan fields from rendered HTML for a given ISP.

    Args:
        urls: List of URLs to try (first success wins).
        isp_key: ISP identifier (e.g., "xtrim").
        html_override: Pre-fetched HTML (skips Playwright if provided).

    Returns:
        Tuple of (valid PlanISP list, error messages).
    """
    now = datetime.now()
    start_ms = int(time.time() * 1000)

    # Get HTML
    html = html_override
    if not html:
        for url in urls:
            try:
                logger.info("Fetching rendered HTML: %s", url)
                html = _get_rendered_html(url)
                if html and len(html) > 1000:
                    break
            except Exception as e:
                logger.warning("Failed to render %s: %s", url, e)

    if not html or len(html) < 500:
        return [], ["Could not fetch rendered HTML"]

    # Parse with ISP-specific parser
    parser = _PARSERS.get(isp_key, _parse_claro)
    try:
        raw_plans = parser(html)
    except Exception as e:
        logger.error("Parser failed for %s: %s", isp_key, e)
        return [], [f"Parser error: {e}"]

    latency_ms = int(time.time() * 1000) - start_ms

    # Validate and build
    plans, errors = validate_and_build_plans(raw_plans, isp_key, now)

    logger.info(
        "Full HTML: %d plans from %s (%.1fs, FREE)",
        len(plans), isp_key, latency_ms / 1000,
    )
    return plans, errors
