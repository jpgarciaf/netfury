"""Tests for PlanISP and LLMCostRecord schemas."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from schemas.cost_tracking import LLMCostRecord
from schemas.plan import AdditionalService, PlanISP


def _make_plan(**overrides) -> PlanISP:
    """Helper to create a PlanISP with minimal required fields."""
    defaults = {
        "fecha": datetime(2026, 4, 18, 12, 0, 0),
        "empresa": "SETEL S.A.",
        "marca": "Xtrim",
        "nombre_plan": "Plan Hogar 300",
        "velocidad_download_mbps": 300.0,
        "precio_plan": 25.99,
    }
    defaults.update(overrides)
    return PlanISP(**defaults)


class TestPlanISP:
    """Tests for the PlanISP Pydantic V2 model."""

    def test_minimal_plan(self):
        plan = _make_plan()
        assert plan.anio == 2026
        assert plan.mes == 4
        assert plan.dia == 18

    def test_auto_compute_discount(self):
        plan = _make_plan(
            precio_plan=30.0,
            precio_plan_descuento=24.0,
        )
        assert plan.descuento == 20.0

    def test_auto_sync_pys_count(self):
        plan = _make_plan(
            pys_adicionales_detalle={
                "disney_plus": AdditionalService(
                    tipo_plan="disney_plus_basic",
                    meses=12,
                    categoria="streaming",
                ),
                "hbo_max": AdditionalService(
                    tipo_plan="hbo_max_standard",
                    meses=6,
                    categoria="streaming",
                ),
            },
        )
        assert plan.pys_adicionales == 2

    def test_snake_case_validation_passes(self):
        plan = _make_plan(
            pys_adicionales_detalle={
                "disney_plus": AdditionalService(
                    tipo_plan="dp", meses=9, categoria="streaming",
                ),
            },
        )
        assert "disney_plus" in plan.pys_adicionales_detalle

    def test_snake_case_validation_fails(self):
        with pytest.raises(Exception):
            _make_plan(
                pys_adicionales_detalle={
                    "Disney Plus": AdditionalService(
                        tipo_plan="dp", meses=9, categoria="streaming",
                    ),
                },
            )

    def test_negative_price_rejected(self):
        with pytest.raises(Exception):
            _make_plan(precio_plan=-10.0)

    def test_discount_over_100_rejected(self):
        with pytest.raises(Exception):
            _make_plan(descuento=150.0)

    def test_json_schema_has_30_fields(self):
        schema = PlanISP.model_json_schema()
        props = schema.get("properties", {})
        assert len(props) >= 30

    def test_plan_to_dict(self):
        plan = _make_plan()
        d = plan.model_dump()
        assert isinstance(d, dict)
        assert d["nombre_plan"] == "Plan Hogar 300"


class TestLLMCostRecord:
    """Tests for the LLMCostRecord model."""

    def test_cost_per_mb_calculation(self):
        rec = LLMCostRecord(
            timestamp=datetime.now(),
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            isp="xtrim",
            image_size_bytes=1_048_576,  # exactly 1 MB
            input_tokens=2000,
            output_tokens=500,
            cost_usd=0.0135,
            latency_ms=3200,
            extraction_success=True,
            fields_extracted=28,
            fields_total=30,
        )
        assert rec.image_size_mb == 1.0
        assert rec.cost_per_mb == 0.0135

    def test_zero_image_size(self):
        rec = LLMCostRecord(
            timestamp=datetime.now(),
            provider="local",
            model="ocr-tesseract",
            isp="xtrim",
            image_size_bytes=0,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            latency_ms=500,
            extraction_success=False,
            fields_extracted=0,
            fields_total=30,
        )
        assert rec.cost_per_mb == 0.0
        assert rec.field_coverage_pct == 0.0

    def test_field_coverage(self):
        rec = LLMCostRecord(
            timestamp=datetime.now(),
            provider="openai",
            model="gpt-4o",
            isp="claro",
            image_size_bytes=500_000,
            input_tokens=1000,
            output_tokens=300,
            cost_usd=0.005,
            latency_ms=2000,
            extraction_success=True,
            fields_extracted=24,
            fields_total=30,
        )
        assert rec.field_coverage_pct == 80.0
