# Prompt De Contexto Para Rory

```text
Contexto de proyecto para continuidad técnica

Estoy trabajando en un proyecto llamado NetFury / Benchmark 360. Necesito que tomes este contexto como handoff técnico y continúes desde aquí sin asumir que la documentación de tareas refleja el estado real del código.

Resumen ejecutivo:
- El proyecto busca extraer, normalizar, comparar y exportar información de planes de internet de ISPs en Ecuador.
- El backend está funcional y bastante más avanzado que la documentación de tareas.
- El dashboard web sigue en estado básico y no representa todavía el valor principal del proyecto.
- El valor actual está en scraping, extracción estructurada, benchmarking, validación y exportación de datos.

Estado actual:
- Hay CLI principal con comandos benchmark, pipeline y evaluate.
- Hay scraping con HTML y screenshots.
- Hay extracción por HTML clásico, HTML renderizado, OCR y LLM vision.
- Existe validación con esquema Pydantic de 30+ campos.
- Hay exportación a parquet, csv y json.
- Hay tracking de costo y latencia de llamadas LLM.
- Las pruebas pasan con `uv run pytest -q`.
- Existe al menos una corrida procesada en `data/processed/benchmark_summary.json`.
- El dashboard Flask existe, pero es solo un esqueleto base.

Arquitectura que debes priorizar para leer:
1. `main.py`
2. `settings.py`
3. `pipeline/benchmark_full.py`
4. `pipeline/runner.py`
5. `extractors/full_html_extractor.py`
6. `schemas/plan.py`
7. `pipeline/evaluator.py`

Archivos clave por área:

Flujo general:
- `main.py`
- `pipeline/runner.py`
- `pipeline/benchmark_full.py`
- `settings.py`

Extracción:
- `extractors/full_html_extractor.py`
- `extractors/html_extractor.py`
- `extractors/ocr_extractor.py`
- `extractors/llm_extractor.py`
- `extractors/guardrails.py`

Contrato de datos:
- `schemas/plan.py`
- `tests/test_schemas.py`

Scraping:
- `scraper/spiders/__init__.py`
- `scraper/spiders/generic.py`
- `scraper/utils/screenshot.py`

Costos / benchmarking:
- `llm/cost_tracker.py`
- `pipeline/evaluator.py`
- `data/costs/cost_tracking.parquet`

Web:
- `web/app.py`
- `web/templates/index.html`

ISPs configurados:
- netlife
- ecuanet
- claro
- cnt
- xtrim
- puntonet
- alfanet
- fibramax

Comandos útiles:
- `uv sync`
- `uv run pytest -q`
- `uv run python main.py benchmark-full`
- `uv run python main.py benchmark-full --isp xtrim`
- `uv run python main.py benchmark-full --cached`
- `uv run python main.py pipeline --isp xtrim --strategy llm`
- `uv run python main.py pipeline --strategy all`
- `uv run python main.py evaluate --isp xtrim`
- `uv run python main.py evaluate --isp xtrim --ground-truth data/raw/xtrim_gt.json`
- `uv run python web/app.py`

Advertencias importantes:
- No uses `docs/TASKS_SCRAPER.md` ni `docs/TASKS_WEB.md` como fuente principal de verdad. El código está más avanzado que esos checklists.
- El dashboard está incompleto.
- La cobertura real por ISP todavía no está consolidada en una matriz clara de éxito, precisión y estabilidad.
- El sistema soporta ground truth, pero no parece existir todavía un set robusto por ISP.
- Hay un posible riesgo estructural de git porque `netfury` aparece como gitlink o submódulo y eso puede complicar handoff o integración.

Lectura estratégica:
Esto no es un prototipo vacío. Ya existe una base técnica seria con:
- modelo de datos claro
- múltiples estrategias de extracción
- benchmarking
- persistencia de resultados
- pruebas

Lo que falta:
- mejorar cobertura por proveedor
- consolidar resultados
- cerrar dashboard o reporte final
- alinear documentación con código

Tu tarea inicial:
1. Revisar la arquitectura real del proyecto en los archivos priorizados.
2. Confirmar cuál es el estado efectivo del pipeline actual.
3. Identificar el cuello de botella más importante entre:
   - precisión de extracción
   - cobertura por ISP
   - evaluación con ground truth
   - dashboard/demo final
4. Proponer el siguiente plan de trabajo en orden de impacto.
5. No asumir que la interfaz web es la prioridad principal salvo que el objetivo sea demo de jurado.

Si necesitas sintetizar el estado en una frase:
NetFury ya tiene backend funcional y benchmarking real; lo pendiente no es construir desde cero, sino consolidar cobertura, métricas, documentación y una capa de demo convincente.
```

