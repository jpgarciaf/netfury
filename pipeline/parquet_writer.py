"""Write validated PlanISP records to Parquet format.

Produces the 'benchmark_industria' Parquet file required by the challenge.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from schemas.plan import PlanISP

logger = logging.getLogger(__name__)


def plans_to_dataframe(plans: list[PlanISP]) -> pd.DataFrame:
    """Convert a list of PlanISP objects to a Pandas DataFrame.

    Handles nested dicts (pys_adicionales_detalle) by converting
    AdditionalService objects to plain dicts for JSON serialization.

    Args:
        plans: List of validated PlanISP objects.

    Returns:
        DataFrame with one row per plan.
    """
    rows = []
    for plan in plans:
        row = plan.model_dump()
        # Convert AdditionalService objects to dicts for Parquet
        if row.get("pys_adicionales_detalle"):
            detail = {}
            for k, v in row["pys_adicionales_detalle"].items():
                if hasattr(v, "model_dump"):
                    detail[k] = v.model_dump()
                elif isinstance(v, dict):
                    detail[k] = v
                else:
                    detail[k] = str(v)
            row["pys_adicionales_detalle"] = detail
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty and "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def write_parquet(
    plans: list[PlanISP],
    path: str = "data/processed/benchmark_industria.parquet",
) -> Path:
    """Write plans to a Parquet file.

    Args:
        plans: List of validated PlanISP objects.
        path: Output file path.

    Returns:
        Path to the written Parquet file.
    """
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    df = plans_to_dataframe(plans)

    # Convert dict columns to JSON strings for Parquet compatibility
    if "pys_adicionales_detalle" in df.columns:
        import json
        df["pys_adicionales_detalle"] = df["pys_adicionales_detalle"].apply(
            lambda x: json.dumps(x, ensure_ascii=False) if x else "{}"
        )

    # Convert list columns to JSON strings
    for col in ["sectores", "parroquia", "canton", "provincia"]:
        if col in df.columns:
            import json
            df[col] = df[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False)
                if isinstance(x, list) else "[]"
            )

    df.to_parquet(output, index=False, engine="pyarrow")
    logger.info(
        "Wrote %d plans to %s (%.1f KB)",
        len(plans), output, output.stat().st_size / 1024,
    )
    return output
