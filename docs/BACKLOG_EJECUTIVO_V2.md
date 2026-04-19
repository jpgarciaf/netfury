# Backlog Ejecutivo V2

Fecha de corte: 2026-04-18
Objetivo: traducir el mapeo entre NetFury y Benchmark 360 V2 en acciones inmediatas de implementacion.

## Lectura rapida

La adecuacion recomendada no es reemplazar NetFury.

Es hacer visible la logica V2 sobre la base ya existente:

- mantener el motor actual
- formalizar la capa de contrato
- cristalizar la capa analitica
- reforzar notebook y dashboard como demo

## Tabla ejecutiva

| Archivo real | Equivalente V2 | Prioridad | Accion concreta |
|---|---|---|---|
| `schemas/plan.py` | `base_plan_fields_v2` | Baja | No tocar la logica. Documentar explicitamente este modulo como la base estructural oficial del benchmark |
| `extractors/guardrails.py` + `pipeline/runner.py` + validaciones | `integration_contract_v2` | Media-Alta | Crear `pipeline/integration_contract.py` para centralizar normalizacion, enriquecimiento y validacion |
| `pipeline/evaluator.py` parcial | `derived_variables_v2` | Critica | Crear `pipeline/derived_metrics.py` con metricas competitivas y scores de negocio |
| `scraper/` + `extractors/` | `scraper_v2` | Baja | No simplificar. Documentar la capa actual como captura multiestrategia avanzada |
| `notebooks/benchmark_industria_notebook.ipynb` | `notebook_v2` | Alta | Reestructurar el notebook como pipeline V2 explicito: carga -> contrato -> derivadas -> comparativa -> exportacion |
| `data/processed/*.parquet/csv/json` | `sample_dataset_v2` | Baja | Declarar estos archivos como dataset oficial del benchmark para demo y evidencia |
| `web/app.py` + templates | `dashboard_v2` | Alta | Simplificar la web y enfocar en tabla de planes, ranking CPM y filtro por ISP |

## Detalle por capa

### 1. Base estructural

Archivo real:

- `schemas/plan.py`

Equivalente V2:

- `base_plan_fields_v2`

Lectura:

Esta capa ya esta resuelta. El trabajo pendiente no es tecnico, sino de naming y documentacion.

Accion:

- referenciar `PlanISP` como contrato estructural oficial en docs y pitch

## 2. Contrato de integracion

Archivos reales:

- `extractors/guardrails.py`
- `pipeline/runner.py`
- validaciones Pydantic de `schemas/plan.py`

Equivalente V2:

- `integration_contract_v2`

Problema actual:

La logica existe, pero esta distribuida. Eso dificulta:

- demo
- debugging
- explicacion arquitectonica

Accion recomendada:

Crear un archivo nuevo:

- `pipeline/integration_contract.py`

Contenido sugerido:

```python
def normalize_plan(raw_data): ...
def validate_plan(plan): ...
def enrich_plan(plan): ...
```

Resultado esperado:

- una capa visible entre captura y analitica
- mejor trazabilidad
- mejor narrativa V2

## 3. Variables derivadas

Archivo real de partida:

- `pipeline/evaluator.py` parcial

Equivalente V2:

- `derived_variables_v2`

Estado:

Es el mayor gap del proyecto.

No porque falte capacidad tecnica, sino porque aun no existe una capa formal que convierta datos en lectura competitiva reutilizable.

Accion critica:

Crear:

- `pipeline/derived_metrics.py`

Contenido minimo sugerido:

```python
def costo_por_mbps(plan): ...
def valor_relativo(plan, mercado): ...
def score_promocional(plan): ...
def score_valor_agregado(plan): ...
def score_friccion_comercial(plan): ...
def presion_competitiva_segmento(df): ...
```

Resultado esperado:

- pasar de exportar datos a producir inteligencia competitiva
- fortalecer notebook, dashboard y pitch

## 4. Captura

Archivos reales:

- `scraper/`
- `extractors/`

Equivalente V2:

- `scraper_v2`

Estado:

La infraestructura actual ya es mas rica que la V2 simplificada.

Accion:

- no reducir complejidad
- documentarla como captura multiestrategia avanzada

## 5. Notebook

Archivo real:

- `notebooks/benchmark_industria_notebook.ipynb`

Equivalente V2:

- `notebook_v2`

Accion:

Reorganizar el flujo explicito del notebook en este orden:

1. cargar datos
2. aplicar integration contract
3. aplicar derived metrics
4. mostrar comparativa
5. exportar parquet

Resultado esperado:

- demo clara para jurado
- trazabilidad tecnica
- evidencia end-to-end

## 6. Dataset muestra

Archivos reales:

- `data/processed/benchmark_industria.parquet`
- `data/processed/benchmark_industria.csv`
- `data/processed/benchmark_industria.json`
- `data/processed/benchmark_summary.json`

Equivalente V2:

- `sample_dataset_v2`

Accion:

- documentarlos como dataset oficial del benchmark
- usarlos como evidencia central en pitch y notebook

## 7. Dashboard

Archivos reales:

- `web/app.py`
- `web/templates/index.html`
- `web/static/`

Equivalente V2:

- `dashboard_v2`

Estado:

Alta oportunidad, pero no hace falta rediseño grande para generar impacto.

Accion:

Implementar solo tres vistas clave:

- tabla de planes
- ranking CPM
- filtro por ISP

Resultado esperado:

- demo simple pero potente
- lectura de negocio inmediata

## Priorizacion por impacto

### 1. Critico

- `pipeline/derived_metrics.py`

### 2. Muy alto

- notebook V2 explicito

### 3. Alto

- dashboard minimo centrado en insight

### 4. Medio

- formalizar `integration_contract.py`

### 5. Bajo

- renaming y documentacion estructural

## Traduccion ejecutiva

Antes:

> scraping -> datos -> exportacion

Despues:

> scraping -> contrato -> metricas -> insight -> decision

## Sintesis final

El mayor gap del proyecto ya no es tecnico.

Es este:

> no tener totalmente formalizada la capa que convierte datos en decisiones

La prioridad inmediata es cristalizar esa capa analitica y usarla como base para notebook, dashboard y demo final.

