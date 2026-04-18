"""Pydantic V2 schema for LLM cost tracking records.

Each record represents a single LLM API call for image extraction,
with calculated cost metrics including cost per megabyte.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, computed_field


class LLMCostRecord(BaseModel):
    """A single LLM API call record with cost and performance metrics."""

    timestamp: datetime = Field(
        description="When the API call was made",
    )
    provider: str = Field(
        description="LLM provider: anthropic, openai, google, local",
    )
    model: str = Field(
        description="Model identifier, e.g. 'claude-sonnet-4-20250514'",
    )
    isp: str = Field(
        description="ISP being extracted, e.g. 'xtrim'",
    )

    # --- Image metrics ---
    image_path: str | None = Field(
        default=None,
        description="Path to the screenshot file",
    )
    image_size_bytes: int = Field(
        ge=0,
        description="Raw image file size in bytes",
    )

    # --- Token usage ---
    input_tokens: int = Field(
        ge=0, description="Input tokens consumed",
    )
    output_tokens: int = Field(
        ge=0, description="Output tokens consumed",
    )

    # --- Cost ---
    cost_usd: float = Field(
        ge=0, description="Total cost in USD for this call",
    )

    # --- Performance ---
    latency_ms: int = Field(
        ge=0, description="Wall-clock latency in milliseconds",
    )

    # --- Quality ---
    extraction_success: bool = Field(
        description="Whether extraction produced valid Pydantic output",
    )
    fields_extracted: int = Field(
        ge=0,
        description="Number of non-null fields in the extracted plan",
    )
    fields_total: int = Field(
        ge=0,
        description="Total number of fields in the PlanISP schema",
    )
    plans_extracted: int = Field(
        default=0, ge=0,
        description="Number of plans successfully extracted from page",
    )

    # --- Computed fields ---

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_size_mb(self) -> float:
        """Image size in megabytes."""
        return round(self.image_size_bytes / 1_048_576, 4)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cost_per_mb(self) -> float:
        """Cost in USD per megabyte of image processed."""
        if self.image_size_bytes == 0:
            return 0.0
        return round(self.cost_usd / self.image_size_mb, 6)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def field_coverage_pct(self) -> float:
        """Percentage of fields successfully extracted."""
        if self.fields_total == 0:
            return 0.0
        return round(self.fields_extracted / self.fields_total * 100, 1)
