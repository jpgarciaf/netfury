"""Pydantic V2 schema for ISP internet plans -- 30+ columns.

This is the core data model for Benchmark 360. Every extraction strategy
(HTML, OCR, LLM vision) must produce data conforming to this schema.
The output Parquet file uses this schema for validation.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class AdditionalService(BaseModel):
    """A single additional product/service bundled with an ISP plan.

    Keys in the parent dict must be snake_case (e.g., "disney_plus").
    """

    tipo_plan: str = Field(
        description="Nombre exacto del plan de la plataforma, "
        "e.g. 'disney_plus_premium'",
    )
    meses: int | None = Field(
        default=None,
        ge=0,
        description="Meses de duracion del beneficio",
    )
    categoria: str = Field(
        description="Categoria del servicio: streaming, seguridad, "
        "educacion, entretenimiento, etc.",
    )


class PlanISP(BaseModel):
    """Schema for a single ISP internet plan.

    All monetary values are in USD sin IVA unless stated otherwise.
    Contains 30+ fields as required by the Benchmark 360 challenge.
    """

    # --- Temporal ---
    fecha: datetime = Field(
        description="Fecha y hora exacta de extraccion de datos",
    )
    anio: int = Field(default=0, description="Anio de la fecha")
    mes: int = Field(default=0, ge=1, le=12, description="Mes de la fecha")
    dia: int = Field(default=0, ge=1, le=31, description="Dia de la fecha")

    # --- Company ---
    empresa: str = Field(
        description="Razon social registrada en Superintendencia de Companias",
    )
    marca: str = Field(
        description="Marca comercial: Netlife, Ecuanet, Claro, CNT, "
        "Xtrim, Puntonet, Alfanet, Fibramax",
    )

    # --- Plan identity ---
    nombre_plan: str = Field(description="Nombre del plan de internet")

    # --- Speeds ---
    velocidad_download_mbps: float = Field(
        ge=0, description="Velocidad de descarga en Mbps",
    )
    velocidad_upload_mbps: float | None = Field(
        default=None, ge=0, description="Velocidad de subida en Mbps",
    )

    # --- Pricing (sin IVA, sin descuento mensual) ---
    precio_plan: float = Field(
        ge=0,
        description="Precio principal sin IVA, sin descuentos mensuales",
    )
    precio_plan_tarjeta: float | None = Field(
        default=None, ge=0,
        description="Precio sin IVA si paga con tarjeta de credito",
    )
    precio_plan_debito: float | None = Field(
        default=None, ge=0,
        description="Precio sin IVA si paga con debito/cuenta",
    )
    precio_plan_efectivo: float | None = Field(
        default=None, ge=0,
        description="Precio sin IVA si paga en efectivo",
    )

    # --- Discounts ---
    precio_plan_descuento: float | None = Field(
        default=None, ge=0,
        description="Precio con descuento mensual (sin IVA)",
    )
    descuento: float | None = Field(
        default=None, ge=0, le=100,
        description="Porcentaje descuento: "
        "(precio_plan - precio_plan_descuento) / precio_plan * 100",
    )
    meses_descuento: int | None = Field(
        default=None, ge=0,
        description="Meses durante los que aplica el descuento",
    )

    # --- Installation ---
    costo_instalacion: float | None = Field(
        default=None, ge=0,
        description="Costo total de instalacion CON IVA",
    )
    comparticion: str | None = Field(
        default=None,
        description="Ratio de comparticion del servicio, e.g. '1:1', '2:1'",
    )

    # --- Additional services ---
    pys_adicionales: int = Field(
        default=0, ge=0,
        description="Cantidad de productos y servicios adicionales",
    )
    pys_adicionales_detalle: dict[str, AdditionalService] = Field(
        default_factory=dict,
        description="Dict con keys en snake_case. Cada value tiene "
        "tipo_plan, meses, categoria",
    )

    # --- Contract ---
    meses_contrato: int | None = Field(
        default=None, ge=0,
        description="Meses minimos de contrato",
    )
    facturas_gratis: int | None = Field(
        default=None, ge=0,
        description="Cantidad de facturas que no debe pagar el cliente",
    )

    # --- Technology ---
    tecnologia: str | None = Field(
        default=None,
        description="Tipo de tecnologia: fibra_optica, fttp, cobre, etc.",
    )

    # --- Geographic ---
    sectores: list[str] = Field(
        default_factory=list,
        description="Sectores geograficos con beneficio extra",
    )
    parroquia: list[str] = Field(
        default_factory=list,
        description="Parroquias con beneficio extra",
    )
    canton: list[str] = Field(
        default_factory=list,
        description="Cantones con beneficio extra",
    )
    provincia: list[str] = Field(
        default_factory=list,
        description="Provincias con beneficio extra",
    )

    # --- Miscellaneous ---
    factura_anterior: bool | None = Field(
        default=None,
        description="Requiere presentar factura del ISP actual",
    )
    terminos_condiciones: str | None = Field(
        default=None,
        description="Terminos y condiciones del plan",
    )
    beneficios_publicitados: str | None = Field(
        default=None,
        description="Caracteristicas publicitadas: 'alta velocidad', etc.",
    )

    # --- Validators ---

    @model_validator(mode="after")
    def _compute_date_parts(self) -> PlanISP:
        """Auto-fill anio, mes, dia from fecha."""
        self.anio = self.fecha.year
        self.mes = self.fecha.month
        self.dia = self.fecha.day
        return self

    @model_validator(mode="after")
    def _compute_discount_pct(self) -> PlanISP:
        """Auto-compute descuento % if both prices are present."""
        if (
            self.precio_plan_descuento is not None
            and self.precio_plan > 0
            and self.descuento is None
        ):
            self.descuento = round(
                (self.precio_plan - self.precio_plan_descuento)
                / self.precio_plan
                * 100,
                2,
            )
        return self

    @model_validator(mode="after")
    def _sync_pys_count(self) -> PlanISP:
        """Keep pys_adicionales in sync with pys_adicionales_detalle."""
        if self.pys_adicionales_detalle and self.pys_adicionales == 0:
            self.pys_adicionales = len(self.pys_adicionales_detalle)
        return self

    @field_validator("pys_adicionales_detalle")
    @classmethod
    def _validate_snake_case_keys(
        cls, v: dict[str, AdditionalService],
    ) -> dict[str, AdditionalService]:
        """Ensure all keys in additional services dict are snake_case."""
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for key in v:
            if not pattern.match(key):
                raise ValueError(
                    f"Key '{key}' in pys_adicionales_detalle must be "
                    f"snake_case (lowercase, underscores only)"
                )
        return v
