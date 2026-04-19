# Resumen Ejecutivo Para Rory

Fecha de corte: 2026-04-18
Proyecto: NetFury / Benchmark 360

## Sintesis

NetFury es un proyecto para extraer, estructurar y comparar planes de internet de ISPs en Ecuador. El backend ya es funcional y tiene una base técnica sólida; lo pendiente no es arrancar de cero, sino consolidar cobertura por proveedor, métricas de calidad y una capa de demo más convincente.

## Lo que ya existe

- CLI operativa para benchmark, pipeline y evaluación
- scraping con HTML y screenshots
- extracción por HTML, OCR y LLM vision
- esquema Pydantic de 30+ campos para normalizar resultados
- exportación a `parquet`, `csv` y `json`
- tracking de costos y latencia de modelos
- pruebas automatizadas pasando

## Valor real hoy

El valor principal del proyecto está en el pipeline de datos:

- captura de páginas de ISPs
- extracción estructurada
- validación del contrato de datos
- benchmarking técnico entre estrategias y modelos

La interfaz web todavía no representa el estado más fuerte del sistema.

## Estado por frentes

Backend y pipeline:
- funcional y con buena base

Extracción por proveedor:
- avanzada, pero todavía no consolidada de forma uniforme para todos los ISPs

Evaluación:
- existe soporte, pero falta robustecer ground truth y matriz comparativa por proveedor

Dashboard:
- básico, aún en modo esqueleto

Documentación:
- parcialmente desalineada con el código real

## Evidencia concreta

- `uv run pytest -q` pasa
- existe procesamiento real en `data/processed/benchmark_summary.json`
- existe tracking de costos en `data/costs/cost_tracking.parquet`
- hay 8 ISPs configurados: `netlife`, `ecuanet`, `claro`, `cnt`, `xtrim`, `puntonet`, `alfanet`, `fibramax`

## Riesgos abiertos

- los checklists en `docs/TASKS_SCRAPER.md` y `docs/TASKS_WEB.md` no reflejan bien el estado real
- el dashboard puede dar una falsa impresión de inmadurez si se usa como referencia principal
- falta una matriz consolidada de éxito, precisión y estabilidad por ISP
- el set de ground truth todavía no parece completo
- `netfury` aparece como posible `gitlink` o submódulo, lo que puede complicar integración

## Prioridad recomendada

1. consolidar cobertura y estabilidad por ISP
2. fortalecer evaluación con ground truth
3. alinear documentación con el código real
4. cerrar una demo o dashboard convincente para presentación

## Lectura inicial recomendada

1. `main.py`
2. `settings.py`
3. `pipeline/benchmark_full.py`
4. `pipeline/runner.py`
5. `extractors/full_html_extractor.py`
6. `schemas/plan.py`
7. `pipeline/evaluator.py`

## Frase de estado

NetFury ya tiene backend funcional y benchmarking real; el siguiente salto es consolidar precisión, cobertura, evidencia comparativa y una presentación final creíble.

