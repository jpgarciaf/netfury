# Indice Maestro Para Rory

Fecha de corte: 2026-04-18
Proyecto: NetFury / Benchmark 360
Estado general: funcional en backend, parcial en extraccion multi-estrategia, incompleto en dashboard y cierre de producto

## 1. Proposito del proyecto

NetFury es un proyecto para extraer, normalizar, comparar y exportar informacion de planes de internet de ISPs competidores en Ecuador.

El foco tecnico actual esta en:

- scraping y captura de HTML / screenshot
- extraccion estructurada de planes via HTML, OCR y LLM vision
- validacion con esquema Pydantic de 30+ campos
- exportacion a formatos entregables (`parquet`, `csv`, `json`)
- evaluacion comparativa de modelos por costo, latencia y cobertura

## 2. Estado ejecutivo

### Ya implementado

- CLI principal con comandos de benchmark, pipeline y evaluacion
- configuracion central de 8 ISPs objetivo
- spider generico con soporte para HTML y screenshot
- extractor avanzado `full_html` con parsers por ISP
- extractor por OCR
- extractor por LLM vision con multiples proveedores
- guardrails para parseo, sanitizacion y validacion
- esquema principal `PlanISP` con 30+ columnas
- exportacion de resultados a `data/processed/`
- tracking de costo y latencia de llamadas LLM
- pruebas automatizadas de esquemas y costos

### En progreso

- cobertura completa y estable para todos los ISPs
- validacion real contra ground truth por proveedor
- consolidacion de resultados de varias corridas
- limpieza de documentacion desactualizada

### Pendiente o muy basico

- dashboard web utilizable
- visualizaciones y filtros
- presentacion final de producto
- estrategia de historico / monitoreo recurrente

## 3. Evidencia concreta del avance

### Salud tecnica

- `uv run pytest -q` pasa con `12 passed`
- existe salida procesada en `data/processed/`
- existe tracking de costos en `data/costs/`

### Resultado procesado detectado

Archivo: `data/processed/benchmark_summary.json`

Hallazgos de la corrida detectada:

- fecha de extraccion: `2026-04-18`
- estrategia: `full_html`
- planes extraidos: `3`
- ISPs procesados en esa corrida: `1`
- ISPs con datos: `1`
- cobertura promedio de campos: `61.1%`
- campos posibles: `30`

Nota: este resultado refleja una corrida puntual, no el maximo potencial total del proyecto.

## 4. Arquitectura actual

### Entrada principal

- `main.py`

Comandos disponibles:

- `benchmark-full`: extrae 30+ campos usando HTML renderizado y parsers por ISP
- `benchmark`: benchmark base
- `pipeline`: corre el pipeline por un ISP o todos
- `evaluate`: compara modelos OCR/LLM

### Configuracion

- `settings.py`

Responsabilidades:

- carga de variables de entorno
- modelo LLM por defecto
- lista de modelos de evaluacion
- tabla de precios por modelo
- mapeo de empresa legal por ISP
- URLs objetivo por ISP

ISPs configurados:

- `netlife`
- `ecuanet`
- `claro`
- `cnt`
- `xtrim`
- `puntonet`
- `alfanet`
- `fibramax`

### Scraping

- `scraper/spiders/__init__.py`
- `scraper/spiders/generic.py`
- `scraper/base_spider.py`
- `scraper/utils/http_client.py`
- `scraper/utils/screenshot.py`

Capacidades:

- uso de URLs especificas por proveedor
- fallback entre varias URLs
- descarga HTML
- captura screenshot para OCR/LLM

### Extraccion

#### 4.1 HTML clasico

- `extractors/html_extractor.py`

Uso: extraer planes desde HTML sin depender de vision.

#### 4.2 HTML avanzado renderizado

- `extractors/full_html_extractor.py`

Uso: estrategia mas fuerte del proyecto actual para llenar 30+ campos usando Playwright y parsers por ISP.

Parsers especificos detectados para:

- `xtrim`
- `netlife`
- `ecuanet`
- `alfanet`
- `fibramax`
- `claro`
- `cnt`
- `puntonet`

#### 4.3 OCR

- `extractors/ocr_extractor.py`

Uso: extraer texto desde screenshots cuando la pagina no expone bien la info en HTML.

#### 4.4 LLM vision

- `extractors/llm_extractor.py`
- `extractors/prompt_templates.py`

Uso: enviar screenshots a modelos vision y devolver JSON estructurado.

Proveedores / modelos contemplados:

- Anthropic
- OpenAI
- Google
- modelos locales

### Guardrails y validacion

- `extractors/guardrails.py`

Responsabilidades:

- sanitizar entrada
- parsear respuestas JSON del LLM
- truncar respuestas absurdas
- inyectar campos obligatorios
- validar contra `PlanISP`

### Esquema de datos

- `schemas/plan.py`
- `schemas/cost_tracking.py`

`PlanISP` es el contrato central del proyecto. Contiene:

- datos temporales
- razon social y marca
- nombre de plan
- velocidad download / upload
- precios base y variantes
- descuentos
- costo de instalacion
- comparticion
- productos y servicios adicionales
- contrato
- tecnologia
- cobertura geografica
- terminos y beneficios publicitados

### Pipeline y exportacion

- `pipeline/runner.py`
- `pipeline/benchmark.py`
- `pipeline/benchmark_full.py`
- `pipeline/parquet_writer.py`
- `pipeline/evaluator.py`

Responsabilidades:

- orquestar scraping + extraccion
- correr por uno o varios ISPs
- exportar salidas procesadas
- comparar OCR vs LLMs
- medir costo por imagen, latencia y cobertura

### Dashboard web

- `web/app.py`
- `web/templates/index.html`
- `web/static/css/style.css`
- `web/static/js/main.js`

Estado:

- Flask base montado
- landing minima
- sin dashboard funcional aun

## 5. Archivos clave para que Rory entre rapido

### Si Rory necesita entender el flujo completo

- `main.py`
- `pipeline/runner.py`
- `pipeline/benchmark_full.py`
- `settings.py`

### Si Rory necesita mejorar extraccion

- `extractors/full_html_extractor.py`
- `extractors/html_extractor.py`
- `extractors/ocr_extractor.py`
- `extractors/llm_extractor.py`
- `extractors/guardrails.py`

### Si Rory necesita revisar el contrato de datos

- `schemas/plan.py`
- `tests/test_schemas.py`

### Si Rory necesita revisar scraping

- `scraper/spiders/__init__.py`
- `scraper/spiders/generic.py`
- `scraper/utils/screenshot.py`

### Si Rory necesita revisar costos / benchmarking

- `llm/cost_tracker.py`
- `pipeline/evaluator.py`
- `data/costs/cost_tracking.parquet`

### Si Rory necesita revisar la capa de presentacion

- `web/app.py`
- `web/templates/index.html`

## 6. Entregables y artefactos existentes

### Datos de entrada / evidencia

- `data/raw/*_rendered.html`
- `data/raw/*_screenshot.png`

### Datos procesados

- `data/processed/benchmark_industria.parquet`
- `data/processed/benchmark_industria.csv`
- `data/processed/benchmark_industria.json`
- `data/processed/benchmark_summary.json`

### Costos y evaluacion

- `data/costs/cost_tracking.parquet`
- `data/costs/evaluation_results.csv` cuando se ejecuta `evaluate`

## 7. Comandos utiles

Instalacion:

```bash
uv sync
```

Pruebas:

```bash
uv run pytest -q
```

Benchmark completo:

```bash
uv run python main.py benchmark-full
uv run python main.py benchmark-full --isp xtrim
uv run python main.py benchmark-full --cached
```

Pipeline general:

```bash
uv run python main.py pipeline --isp xtrim --strategy llm
uv run python main.py pipeline --strategy all
```

Evaluacion de modelos:

```bash
uv run python main.py evaluate --isp xtrim
uv run python main.py evaluate --isp xtrim --ground-truth data/raw/xtrim_gt.json
```

Dashboard web:

```bash
uv run python web/app.py
```

## 8. Riesgos, huecos y observaciones importantes

### 8.1 Documentacion no sincronizada

Los archivos `docs/TASKS_SCRAPER.md` y `docs/TASKS_WEB.md` muestran muchas tareas como pendientes, pero el codigo real esta bastante mas avanzado. Rory no deberia usar esos checklists como fuente principal de verdad.

### 8.2 Dashboard incompleto

La parte web existe solo como esqueleto. El valor real del proyecto hoy esta en pipeline, extraccion y benchmarking, no en experiencia de usuario final.

### 8.3 Cobertura real por ISP aun no consolidada

Aunque hay 8 ISPs configurados y parsers para varios, no hay una matriz consolidada de exito / precision / estabilidad por cada proveedor en este documento. Eso sigue siendo una tarea importante.

### 8.4 Ground truth y accuracy

El evaluador soporta ground truth, pero no se observa todavia un conjunto robusto y generalizado de archivos ground truth por ISP dentro del repo principal.

### 8.5 Riesgo de git / estructura

En el estado actual del repo, `netfury` aparece agregado como `gitlink` o submodulo, no como carpeta normal del proyecto principal. Eso puede complicar handoff, versionado o integracion si no fue intencional.

## 9. Lectura estrategica del estado del proyecto

La situacion actual no es la de un prototipo vacio. Ya existe una base tecnica seria con:

- modelo de datos claro
- multiples estrategias de extraccion
- benchmarking
- persistencia de resultados
- pruebas

Lo que falta es convertir esa base en un entregable mas completo, consistente y demostrable:

- mejorar cobertura por proveedor
- consolidar resultados
- cerrar dashboard o reporte final
- alinear documentacion con codigo

## 10. Recomendaciones inmediatas para Rory

Si Rory va a continuar el trabajo, el mejor orden de lectura es:

1. `main.py`
2. `settings.py`
3. `pipeline/benchmark_full.py`
4. `pipeline/runner.py`
5. `extractors/full_html_extractor.py`
6. `schemas/plan.py`
7. `pipeline/evaluator.py`

Luego, segun el objetivo:

- si quiere mejorar precision: trabajar en `extractors/`
- si quiere comparar modelos: trabajar en `pipeline/evaluator.py` y `llm/`
- si quiere preparar demo: trabajar en `web/` y consumir `data/processed/`
- si quiere robustez de entrega: consolidar ground truth, metricas y documentacion

## 11. Sintesis corta para copiarle a Rory

NetFury es un benchmark de extraccion de planes ISP en Ecuador. El backend ya esta funcional: tiene CLI, scraping con HTML y screenshots, extraccion por HTML/OCR/LLM, validacion con un esquema Pydantic de 30+ campos, exportacion a parquet/csv/json y evaluacion de modelos por costo y latencia. Hay pruebas pasando y al menos una corrida real guardada en `data/processed/benchmark_summary.json`. El estado mas debil esta en dashboard web, consolidacion de cobertura por ISP y documentacion actualizada. El valor actual del proyecto esta en el pipeline de datos, no en la interfaz final.

