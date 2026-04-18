"""Singleton cost tracker for LLM API calls.

Records every LLM call with tokens, cost, image size, and latency.
Exports accumulated records to a Parquet file for analysis.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from schemas.cost_tracking import LLMCostRecord
from settings import LLM_PRICING


class CostTracker:
    """Accumulates LLM cost records and exports to Parquet."""

    _instance: CostTracker | None = None
    _records: list[LLMCostRecord]

    def __new__(cls) -> CostTracker:
        """Singleton pattern -- one tracker per process."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._records = []
        return cls._instance

    def record(
        self,
        *,
        provider: str,
        model: str,
        isp: str,
        image_size_bytes: int,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        extraction_success: bool,
        fields_extracted: int,
        fields_total: int,
        plans_extracted: int = 0,
        image_path: str | None = None,
    ) -> LLMCostRecord:
        """Record a single LLM API call with cost calculation.

        Args:
            provider: LLM provider name.
            model: Model identifier.
            isp: ISP being extracted.
            image_size_bytes: Size of the input image.
            input_tokens: Tokens consumed for input.
            output_tokens: Tokens consumed for output.
            latency_ms: Call latency in milliseconds.
            extraction_success: Whether extraction was valid.
            fields_extracted: Non-null fields in output.
            fields_total: Total schema fields.
            plans_extracted: Number of plans found.
            image_path: Optional path to the screenshot.

        Returns:
            The created LLMCostRecord.
        """
        cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

        entry = LLMCostRecord(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            isp=isp,
            image_path=image_path,
            image_size_bytes=image_size_bytes,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            extraction_success=extraction_success,
            fields_extracted=fields_extracted,
            fields_total=fields_total,
            plans_extracted=plans_extracted,
        )
        self._records.append(entry)
        return entry

    @staticmethod
    def _calculate_cost(
        model: str, input_tokens: int, output_tokens: int,
    ) -> float:
        """Calculate USD cost from token counts and pricing table.

        Args:
            model: Model identifier to look up pricing.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Cost in USD.
        """
        pricing = LLM_PRICING.get(model, {"input": 0.0, "output": 0.0})
        cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
        )
        return round(cost, 8)

    @property
    def records(self) -> list[LLMCostRecord]:
        """Return all accumulated records."""
        return list(self._records)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert all records to a Pandas DataFrame."""
        if not self._records:
            return pd.DataFrame()
        return pd.DataFrame([r.model_dump() for r in self._records])

    def export_parquet(
        self, path: str = "data/costs/cost_tracking.parquet",
    ) -> Path:
        """Export records to a Parquet file.

        Args:
            path: Output file path.

        Returns:
            Path to the written file.
        """
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        df = self.to_dataframe()
        if not df.empty:
            df.to_parquet(output, index=False)
        return output

    def summary(self) -> pd.DataFrame:
        """Generate a summary table grouped by model.

        Returns:
            DataFrame with columns: model, total_cost, avg_cost_per_mb,
            avg_latency_ms, avg_accuracy, total_calls.
        """
        df = self.to_dataframe()
        if df.empty:
            return df

        return (
            df.groupby("model")
            .agg(
                total_cost=("cost_usd", "sum"),
                avg_cost_per_mb=("cost_per_mb", "mean"),
                avg_latency_ms=("latency_ms", "mean"),
                avg_field_coverage=("field_coverage_pct", "mean"),
                total_calls=("model", "count"),
                success_rate=(
                    "extraction_success",
                    lambda x: round(x.mean() * 100, 1),
                ),
            )
            .round(6)
            .reset_index()
            .sort_values("avg_cost_per_mb")
        )

    def reset(self) -> None:
        """Clear all accumulated records."""
        self._records.clear()
