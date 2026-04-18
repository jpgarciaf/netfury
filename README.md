# NetFury - Comparador de Precios ISP

Herramienta de web scraping y analisis de datos para comparar precios de proveedores de internet (ISP) en el mercado.

## Modulos

### 1. Scraper (`scraper/`)
Modulo de web scraping que recopila datos de precios, planes y caracteristicas de los principales proveedores de internet.

### 2. Web Dashboard (`web/`)
Aplicacion web que muestra los resultados del analisis de precios de forma visual e interactiva.

## Estructura del Proyecto

```
netfury/
├── scraper/            # Modulo de web scraping
│   ├── spiders/        # Spiders por cada ISP
│   ├── utils/          # Utilidades (parseo, limpieza de datos)
│   ├── __init__.py
│   └── main.py         # Punto de entrada del scraper
├── web/                # Modulo del dashboard web
│   ├── templates/      # Templates HTML (Jinja2)
│   ├── static/         # Archivos estaticos (CSS, JS)
│   ├── __init__.py
│   └── app.py          # Punto de entrada de la app web
├── data/               # Datos recopilados (CSV, JSON)
├── docs/               # Documentacion y tareas
│   ├── TASKS_SCRAPER.md
│   └── TASKS_WEB.md
├── pyproject.toml      # Dependencias y config del proyecto (uv)
├── uv.lock             # Lockfile de dependencias
└── README.md
```

## Setup

```bash
uv sync
```
