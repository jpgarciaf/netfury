# NetFury — Benchmark 360

Pipeline automatizado de extraccion y estructuracion de datos de planes de Internet Fijo (ISP) en Ecuador. Desarrollado para el reto **Interact 2 Hack — Benchmark 360** de Netlife / Ecuanet.

Extrae datos de **8 ISPs** (Netlife, Ecuanet, Xtrim, Claro, CNT, Puntonet, Alfanet, Fibramax) y los estructura en un esquema de **30+ columnas** listo para analisis competitivo.

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) como gestor de dependencias
- Playwright (navegador headless para renderizar JS)
- Tesseract OCR (opcional, para estrategias OCR)

## Setup

```bash
# Instalar dependencias
uv sync

# Instalar navegadores de Playwright
uv run playwright install chromium
```

Variables de entorno opcionales (solo para estrategias LLM):

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...
```

---

## Comandos

### `benchmark-full` — Extraccion HTML con 30+ campos (RECOMENDADO)

Usa Playwright para renderizar cada sitio, interactua con tabs y sliders (Home/Pro/Pyme en Netlife, Futbol/Entretenimiento en Xtrim), y parsea el DOM con extractores ISP-especificos.

```bash
# Todos los ISPs
uv run python main.py benchmark-full

# Un ISP especifico
uv run python main.py benchmark-full --isp xtrim

# Usar HTML cacheado (sin re-scrapear)
uv run python main.py benchmark-full --cached
```

**Que hace:**
1. Carga cada pagina con Playwright (espera JS, scroll para lazy-loading)
2. Para ISPs interactivos (Netlife, Xtrim): hace click en tabs/botones y captura multiples snapshots del DOM
3. Parsea con extractores especificos por ISP (BeautifulSoup + CSS selectors / data-testid)
4. Valida contra esquema Pydantic de 30+ campos
5. Exporta a Parquet, CSV, JSON

**Archivos generados:**

```
data/processed/
  benchmark_industria.parquet   # Entregable principal del reto
  benchmark_industria.csv       # Para visualizacion rapida
  benchmark_industria.json      # Records completos
  benchmark_summary.json        # Resumen con field coverage
```

**Costo:** $0 (no usa APIs)
**Tiempo:** ~2-3 min para los 8 ISPs

---

### `benchmark-recursive` — Crawl recursivo desde homepage

Parte de la homepage de cada ISP y descubre paginas de planes automaticamente siguiendo links relevantes (BFS con filtros semanticos). Util para ISPs cuyas URLs de planes cambian frecuentemente.

```bash
# Todos los ISPs
uv run python main.py benchmark-recursive

# Un ISP con profundidad de crawl
uv run python main.py benchmark-recursive --isp claro --crawl-depth 2

# Opciones
uv run python main.py benchmark-recursive --isp alfanet --crawl-depth 3 --max-pages 15
```

**Que hace:**
1. Inicia desde la homepage de cada ISP (`ISP_URLS` en settings.py)
2. Crawler recursivo (BFS) sigue links con keywords relevantes: `plan`, `precio`, `tarifa`, `internet`, `hogar`, `fibra`
3. Filtra por mismo dominio, respeta profundidad maxima
4. Renderiza cada pagina descubierta con Playwright
5. Aplica los mismos parsers HTML de `benchmark-full` sobre cada pagina
6. Deduplica planes encontrados en multiples paginas

**Archivos generados:**

```
data/processed/
  benchmark_industria.parquet
  benchmark_industria.csv
  benchmark_industria.json
  benchmark_summary.json
data/raw/
  {isp}_rendered.html           # HTML cacheado de cada pagina descubierta
```

**Costo:** $0 (no usa APIs)
**Tiempo:** ~5-10 min (depende de la profundidad y cantidad de paginas)

---

### `benchmark-recursive-images` — Crawl + analisis de imagenes con LLM

Combina el crawl recursivo con descubrimiento de imagenes (banners, sliders, cards) y analisis por vision LLM. Captura datos que estan dentro de imagenes y no en el HTML.

```bash
# Un ISP
uv run python main.py benchmark-recursive-images --isp alfanet

# Con opciones
uv run python main.py benchmark-recursive-images --isp alfanet --crawl-depth 2 --max-images 15 --model gpt-4o-mini
```

**Que hace:**
1. Crawl recursivo (igual que `benchmark-recursive`)
2. Extraccion HTML gratuita de cada pagina descubierta
3. Descubrimiento de imagenes relevantes: `<img>`, `<picture>`, CSS `background-image`
4. Filtrado por heuristica: tamano minimo, keywords de relevancia, exclusion de logos/iconos
5. Envio de cada imagen al LLM (GPT-4o, Claude, Gemini) con prompt estructurado
6. Control de presupuesto: maximo de llamadas, tokens y costo USD configurable
7. Merge y deduplicacion de planes HTML + LLM

**Archivos generados:**

```
data/processed/
  benchmark_industria.parquet
  benchmark_industria.csv
  benchmark_industria.json
  benchmark_summary.json
data/costs/
  cost_tracking.parquet         # Detalle de cada llamada LLM (tokens, costo, latencia)
```

**Costo:** Variable (depende del modelo y cantidad de imagenes)
**Tiempo:** ~5-15 min

---

### `benchmark` — Benchmark basico (OCR / LLM sobre screenshot)

Pipeline original: toma un screenshot full-page y extrae datos con OCR local o LLM vision.

```bash
# OCR gratuito (Tesseract)
uv run python main.py benchmark --strategy ocr

# LLM vision
uv run python main.py benchmark --strategy llm --model gpt-4o

# HTML parsing basico
uv run python main.py benchmark --strategy html

# Todas las estrategias combinadas
uv run python main.py benchmark --strategy all
```

**Archivos generados:**

```
data/processed/
  benchmark_industria.parquet
  benchmark_industria.csv
  benchmark_industria.json
  benchmark_summary.json
data/raw/
  {isp}_screenshot.png          # Screenshots full-page
data/costs/
  cost_tracking.parquet         # Si usa estrategia LLM
```

---

### `pipeline` — Extraccion individual

```bash
uv run python main.py pipeline --isp xtrim --strategy llm
uv run python main.py pipeline --isp netlife --strategy html
```

### `evaluate` — Evaluacion multi-modelo

```bash
uv run python main.py evaluate --isp xtrim
```

---

## Dashboard Estrategico

Genera 4 visualizaciones de alto impacto para el equipo de Marketing:

```bash
uv run python notebooks/dashboard_estrategico.py
```

**Archivos generados en `data/visualizations/`:**

| Archivo | Contenido |
|---|---|
| `01_valor_por_mega.png` | Valor promedio y minimo por Mbps por ISP + scatter precio vs velocidad |
| `02_posicionamiento_competitivo.png` | Mapa de posicionamiento: velocidad vs costo/Mbps por plan |
| `03_mapa_ecuador.png` | Mapa de Ecuador: market share Netlife + lider por provincia |
| `04_analisis_estrategico.png` | Heatmap streaming, rango precios, distribucion velocidades, scorecard |

---

## Estructura del Proyecto

```
netfury/
├── main.py                     # CLI entry point
├── settings.py                 # Configuracion (API keys, URLs, precios LLM)
├── pyproject.toml              # Dependencias (uv)
│
├── scraper/                    # Web scraping
│   ├── spiders/                # GenericSpider + URLs por ISP
│   ├── utils/
│   │   ├── http_client.py      # HTTP con robots.txt, delays, UA rotation
│   │   └── screenshot.py       # Playwright screenshots
│   ├── crawler.py              # Crawl recursivo BFS
│   ├── image_discoverer.py     # Descubrimiento de imagenes v1
│   └── image_discoverer_v2.py  # v2 con interaccion de sliders/tabs
│
├── extractors/                 # Estrategias de extraccion
│   ├── full_html_extractor.py  # Parsers HTML ISP-especificos (30+ campos)
│   ├── html_extractor.py       # Parser HTML basico
│   ├── ocr_extractor.py        # OCR v1 (screenshot completo)
│   ├── ocr_v2_extractor.py     # OCR v2 (por imagen individual)
│   ├── llm_extractor.py        # LLM vision (Claude, GPT-4o, Gemini)
│   ├── image_extractor.py      # LLM vision por imagen individual
│   ├── guardrails.py           # Sanitizacion, validacion, anti-prompt-injection
│   └── prompt_image.py         # Prompt template para LLM vision
│
├── pipeline/                   # Orquestacion
│   ├── benchmark_full.py       # HTML interactivo (30+ campos)
│   ├── benchmark_recursive.py  # Crawl recursivo + HTML
│   ├── benchmark_recursive_images.py  # Crawl + HTML + LLM imagenes
│   ├── benchmark.py            # Benchmark basico (OCR/LLM screenshot)
│   ├── runner.py               # Pipeline individual
│   ├── evaluator.py            # Evaluacion multi-modelo
│   └── parquet_writer.py       # Export Parquet/DataFrame
│
├── llm/                        # Clientes LLM
│   ├── cost_tracker.py         # Tracking de costos por llamada
│   └── budget.py               # Control de presupuesto (calls, tokens, USD)
│
├── schemas/
│   └── plan.py                 # PlanISP Pydantic model (30+ campos)
│
├── notebooks/
│   ├── benchmark_industria_notebook.ipynb
│   └── dashboard_estrategico.py
│
├── data/
│   ├── raw/                    # HTML renderizado, screenshots, imagenes
│   ├── processed/              # Parquet, CSV, JSON (entregables)
│   ├── costs/                  # Tracking de costos LLM
│   └── visualizations/         # Graficos del dashboard
│
└── tests/
```

## Esquema de datos (30+ columnas)

| Campo | Tipo | Descripcion |
|---|---|---|
| `fecha` | datetime | Fecha y hora de extraccion |
| `anio`, `mes`, `dia` | int | Componentes de fecha |
| `empresa` | str | Razon social (Superintendencia de Companias) |
| `marca` | str | Marca comercial del ISP |
| `nombre_plan` | str | Nombre del plan |
| `velocidad_download_mbps` | float | Velocidad de descarga (Mbps) |
| `velocidad_upload_mbps` | float | Velocidad de subida (Mbps) |
| `precio_plan` | float | Precio sin IVA, sin descuento |
| `precio_plan_tarjeta` | float | Precio con tarjeta de credito |
| `precio_plan_debito` | float | Precio con debito |
| `precio_plan_efectivo` | float | Precio en efectivo |
| `precio_plan_descuento` | float | Precio con descuento mensual |
| `descuento` | float | Porcentaje de descuento |
| `meses_descuento` | int | Meses que aplica el descuento |
| `costo_instalacion` | float | Costo de instalacion (con IVA) |
| `comparticion` | str | Ratio de comparticion (ej: "2:1") |
| `pys_adicionales` | int | Cantidad de servicios adicionales |
| `pys_adicionales_detalle` | dict | Detalle en snake_case con tipo_plan, meses, categoria |
| `meses_contrato` | int | Permanencia minima |
| `facturas_gratis` | int | Facturas que no se cobran |
| `tecnologia` | str | fibra_optica, fttp, cobre, etc. |
| `sectores` | list | Sectores con beneficio extra |
| `parroquia` | list | Parroquias |
| `canton` | list | Cantones |
| `provincia` | list | Provincias |
| `factura_anterior` | bool | Requiere factura de otro ISP |
| `terminos_condiciones` | str | Texto legal |
| `beneficios_publicitados` | str | Caracteristicas publicitadas |

## ISPs soportados

| ISP | Empresa | URL | Parser |
|---|---|---|---|
| Netlife | MEGADATOS S.A. | netlifeinternet.ec | Especifico (cards flip + tabs) |
| Ecuanet | MEGADATOS S.A. | ecuanet.ec | Especifico (Elementor price tables) |
| Xtrim | SETEL S.A. | xtrim.com.ec | Especifico (Next.js data-testid + tabs) |
| Claro | CONECEL S.A. | claro.com.ec | Generico (regex) |
| CNT | CNT EP | cnt.gob.ec | Generico (regex) |
| Puntonet | PUNTONET S.A. | celerity.ec | Generico (regex) |
| Alfanet | ALFANET S.A. | alfanet.ec | Especifico (Odoo) |
| Fibramax | FIBRAMAX S.A. | fibramax.ec | Especifico (Elementor) |

## Compliance

- Respeta `robots.txt` en requests HTTP (verificacion automatica antes de cada fetch)
- Delays aleatorios entre requests (2-5 segundos configurable)
- User-Agent rotation (4 agentes desktop/mobile)
- Control de presupuesto LLM con limites de calls, tokens y USD
- Sanitizacion de inputs contra prompt injection
- Validacion Pydantic V2 de todos los datos extraidos
