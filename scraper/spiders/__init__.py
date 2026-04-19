"""ISP spiders for scraping plan data from competitor websites."""

from __future__ import annotations

from scraper.spiders.generic import GenericSpider
from settings import ISP_URLS

# Plan page URLs (may differ from homepage)
ISP_PLAN_URLS: dict[str, list[str]] = {
    "netlife": [
        "https://netlifeinternet.ec/",
        "https://www.netlife.ec/planes-hogar/",
        "https://www.netlife.ec",
    ],
    "ecuanet": [
        "https://www.ecuanet.ec/planes-internet-fibra-optica-hogar/",
        "https://www.ecuanet.ec",
    ],
    "claro": [
        "https://www.claro.com.ec/personas/internet/internet-fijo/",
        "https://www.claro.com.ec",
    ],
    "cnt": [
        "https://www.cnt.gob.ec/internet-hogar/",
        "https://www.cnt.gob.ec",
    ],
    "xtrim": [
        "https://www.xtrim.com.ec/",
    ],
    "puntonet": [
        "https://puntonet.ec/planes-hogar/",
        "https://puntonet.ec",
    ],
    "alfanet": [
        "https://www.alfanet.ec/planes",
        "https://www.alfanet.ec",
    ],
    "fibramax": [
        "https://www.fibramax.ec/planes",
        "https://www.fibramax.ec",
    ],
}


def get_spider(isp_key: str) -> GenericSpider:
    """Get a spider instance for the given ISP.

    Args:
        isp_key: ISP identifier (e.g., "xtrim").

    Returns:
        A configured GenericSpider instance.
    """
    urls = ISP_PLAN_URLS.get(isp_key, [ISP_URLS.get(isp_key, "")])
    marca = isp_key.capitalize()
    if isp_key == "cnt":
        marca = "CNT"

    return GenericSpider(
        isp_key=isp_key,
        marca=marca,
        urls=urls,
    )
