"""CLI para extraer JSON desde una URL de imagen usando la logica OCR actual."""

from __future__ import annotations

import argparse
from pathlib import Path

from ocr_url_json.service import extract_plans_json_string_from_url


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Extrae planes desde una URL de imagen y devuelve JSON.",
    )
    parser.add_argument("image_url", help="URL publica de la imagen a procesar")
    parser.add_argument(
        "--engine",
        default="tesseract",
        choices=["tesseract", "easyocr"],
        help="Motor OCR a usar",
    )
    parser.add_argument(
        "--isp",
        dest="isp_key",
        default=None,
        help="ISP a usar en el schema; si se omite, se intenta inferir desde la URL",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta opcional donde guardar el JSON",
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help="No validar robots.txt al descargar la imagen",
    )
    return parser


def main() -> None:
    """Run URL-to-JSON OCR extraction."""
    args = build_parser().parse_args()
    json_output = extract_plans_json_string_from_url(
        args.image_url,
        engine=args.engine,
        isp_key=args.isp_key,
        respect_robots=not args.ignore_robots,
    )

    if args.output:
        args.output.write_text(json_output, encoding="utf-8")
    else:
        print(json_output)


if __name__ == "__main__":
    main()
