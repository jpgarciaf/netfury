# Mapeo NetFury vs Benchmark 360 V2

Fecha de corte: 2026-04-18
Objetivo: contrastar la arquitectura operativa real de NetFury con la arquitectura canonica propuesta en Benchmark 360 V2.

## Lectura corta

NetFury actual y Benchmark 360 V2 no se contradicen.

La diferencia principal es esta:

- NetFury actual describe el sistema como existe en el repo
- Benchmark 360 V2 describe el sistema como deberia leerse, integrarse y presentarse

Formula recomendada:

- NetFury real = motor operativo
- Benchmark 360 V2 = mapa funcional del motor

## Tabla maestra

| Capa V2 | Equivalente real en NetFury | Funcion en NetFury | Estado actual | Recomendacion |
|---|---|---|---|---|
| `benchmark360_base_plan_fields_v2_*` | `schemas/plan.py`, parte de `settings.py` | Define el contrato del plan y el universo de campos | Fuerte | Mantener `PlanISP` como fuente de verdad y documentarlo como "Base Plan Fields V2" |
| `benchmark360_integration_contract_v2_*` | `extractors/guardrails.py`, validaciones Pydantic, `pipeline/runner.py`, `pipeline/benchmark_full.py` | Normaliza, valida e inyecta campos obligatorios | Fuerte pero distribuido | Consolidar el lenguaje y documentarlo como "Integration Contract V2" |
| `benchmark360_derived_variables_v2_*` | Parcialmente en `pipeline/evaluator.py`, analisis ad hoc en CSV/summary, comparativas manuales | Hoy mide cobertura, costo y resultados; no tiene aun una capa formal de derivadas competitivas del mercado | Medio | Crear modulo derivado dedicado para CPM, valor relativo, presion competitiva y scores |
| `benchmark360_scraper_v2_*` | `scraper/spiders/`, `scraper/base_spider.py`, `scraper/utils/`, `extractors/full_html_extractor.py`, OCR, LLM vision | Captura HTML, screenshots y extrae con varias estrategias | Mas avanzado que la V2 propuesta | No simplificarlo; presentar la V2 como vista ordenada de una capa de captura mas rica |
| `benchmark_industria_notebook_*` | `notebooks/benchmark_industria_notebook.ipynb` | Soporte para analisis y entregable tecnico | Existe, pero puede reforzarse como demo end-to-end | Reorientarlo a la secuencia V2: captura -> contrato -> derivadas -> parquet -> insight |
| `benchmark_industria_sample_*.csv` | `data/processed/benchmark_industria.csv`, `benchmark_industria.parquet`, `benchmark_industria.json`, `benchmark_summary.json` | Materializa evidencia exportable del sistema | Fuerte | Declarar el CSV y parquet actuales como sample dataset oficial del benchmark |
| `benchmark360_dashboard_v2_*.jsx` | `web/app.py`, `web/templates/index.html`, `web/static/` | Capa de demo web | Debil | Tratar la V2 como el dashboard objetivo; priorizar tabla, ranking CPM y filtros antes que diseño complejo |

## Contraste conceptual

### 1. Estructura base

### V2

La V2 separa de forma explicita el esquema base del resto del sistema.

### NetFury real

NetFury ya hace eso en la practica con `schemas/plan.py`, pero de forma menos narrada y menos aislada como modulo de presentacion.

### Lectura

No hace falta reemplazar nada.
Hace falta nombrarlo mejor.

## 2. Contrato de integracion

### V2

La V2 vuelve visible una capa intermedia entre scraping y analitica.

### NetFury real

Esa capa ya existe repartida entre:

- `extractors/guardrails.py`
- `validate_and_build_plans()`
- validaciones de `PlanISP`
- exportadores del pipeline

### Lectura

Aqui esta uno de los mejores puntos de adecuacion:
conviene declarar formalmente esta capa como el "Integration Contract V2" del proyecto.

## 3. Variables derivadas

### V2

La V2 explicita la inteligencia competitiva con variables derivadas.

### NetFury real

NetFury ya puede calcular comparativas, pero todavia no tiene un modulo canonico con nombres de negocio como:

- `costo_por_mbps`
- `valor_relativo`
- `score_promocional`
- `score_valor_agregado`
- `score_friccion_comercial`
- `presion_competitiva_segmento`

### Lectura

Este es el mayor hueco entre lo operativo y lo presentacional.
No porque falte capacidad tecnica, sino porque falta cristalizarla como capa analitica formal.

## 4. Captura

### V2

La V2 presenta un scraper mas simple y narrativamente limpio.

### NetFury real

La capa de captura actual es mas potente:

- HTML clasico
- HTML renderizado
- OCR
- LLM vision
- screenshots
- spiders por ISP

### Lectura

No conviene degradar NetFury a un scraper V2 mas basico.
Conviene decir que la V2 representa una vista ordenada de una infraestructura de captura que ya es mas avanzada.

## 5. Notebook

### V2

El notebook es pieza central del entregable tecnico.

### NetFury real

El notebook existe, pero la narrativa del repo hoy esta mas concentrada en el backend que en la explicacion end-to-end.

### Lectura

Conviene reforzar el notebook como puente entre:

- ejecucion tecnica
- evidencia
- demo para jurado

## 6. Dataset muestra

### V2

La V2 hace del sample dataset un artefacto formal.

### NetFury real

Ese artefacto ya existe de hecho en:

- `data/processed/benchmark_industria.csv`
- `data/processed/benchmark_industria.parquet`
- `data/processed/benchmark_industria.json`
- `data/processed/benchmark_summary.json`

### Lectura

El cambio aqui es mas semantico que tecnico:
hay que presentar esos archivos como evidencia consolidada del sistema.

## 7. Dashboard

### V2

Propone un dashboard de valor competitivo, no solo de visualizacion basica.

### NetFury real

La capa `web/` esta en fase inicial y no refleja aun el nivel del backend.

### Lectura

La V2 ayuda a definir exactamente que dashboard necesita el proyecto:

- tabla de planes
- ranking CPM
- comparacion por operador
- filtros
- lectura de presion competitiva

## Adecuacion recomendada

No hacer sustitucion.
Hacer reinterpretacion.

### Capa 1

Mantener NetFury actual como fuente de verdad operativa:

- `main.py`
- `pipeline/`
- `extractors/`
- `schemas/`
- `scraper/`
- `llm/`
- `web/`

### Capa 2

Usar Benchmark 360 V2 como marco canonico de lectura:

1. estructura base
2. contrato de integracion
3. derivadas analiticas
4. captura
5. notebook
6. dataset muestra
7. dashboard

### Capa 3

Declarar explicitamente en documentacion y pitch:

> La V2 no reemplaza el sistema actual.
> Lo reordena para hacerlo legible como producto integral de benchmark competitivo.

## Que gana el proyecto con esta adecuacion

### 1. Claridad

El repo deja de verse solo como conjunto de modulos tecnicos y empieza a leerse como sistema completo.

### 2. Mejor continuidad

Permite dividir trabajo por capas concretas:

- contrato
- derivadas
- notebook
- dashboard

### 3. Mejor pitch

La narrativa deja de ser "extraemos planes" y pasa a ser "medimos el mercado".

### 4. Mejor demo

La capa analitica y visual se vuelve parte explicita del producto, no un agregado final.

## Estado recomendado por capa

| Capa | Estado |
|---|---|
| Base estructural | Resuelta |
| Contrato de integracion | Resuelta pero dispersa |
| Derivadas analiticas | Parcial |
| Captura | Fuerte |
| Notebook | Parcial |
| Dataset muestra | Resuelto |
| Dashboard | Debil |

## Sintesis final

La mejor forma de unir ambas visiones es esta:

> NetFury ya contiene el sistema operativo real del benchmark.
> Benchmark 360 V2 ofrece la forma modular, canonica y presentable de explicarlo, extenderlo y demostrarlo.

Conclusion operativa:

- no reemplazar la arquitectura actual
- si adoptar la V2 como indice rector
- priorizar especialmente dos adaptaciones:
  - formalizar derivadas analiticas
  - alinear notebook y dashboard con esa logica V2

