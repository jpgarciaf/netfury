# NEXT STEPS - NetFury / Benchmark 360

Horizonte: 24-48 horas
Objetivo: pasar de sistema funcional a demo ganadora para hackathon

---

## 0. Principio clave

No construir mas features.

Prioridad:

- consolidar
- demostrar
- explicar valor de negocio

---

## 1. PRIORIDAD CRITICA - Cobertura real por ISP (Dia 1)

### Objetivo

Tener datos funcionales para los 8 ISPs.

### Acciones

- correr:
  `uv run python main.py benchmark-full`

- validar por ISP:
  - `netlife`
  - `claro`
  - `xtrim`
  - `cnt`
  - `ecuanet`
  - `puntonet`
  - `alfanet`
  - `fibramax`

### Output esperado

- minimo 20-40 registros reales en parquet
- archivo:
  `data/processed/benchmark_industria.parquet`

### Validaciones rapidas

- hay velocidad?
- hay precio?
- hay nombre de plan?
- hay duplicados?

---

## 2. PRIORIDAD ALTA - Calidad de datos (Dia 1)

### Objetivo

Subir precision percibida (>90%)

### Acciones

- revisar campos criticos:
  - `precio_plan`
  - `velocidad_download_mbps`
  - `nombre_plan`
  - `descuento`

- limpiar:
  - nulls
  - valores absurdos
  - duplicados

- ajustar parsers en:
  `extractors/full_html_extractor.py`

---

## 3. PRIORIDAD ALTA - Normalizacion (Dia 1)

### Objetivo

Cumplir con el diccionario del reto

### Acciones

- asegurar:
  `pys_adicionales` en snake_case

Ejemplo:

- `Disney Plus` -> `disney_plus`

- validar estructura JSON:
  `{ servicio: { tipo_plan, meses, categoria } }`

---

## 4. PRIORIDAD MEDIA - Evaluacion simple (Dia 2)

### Objetivo

Demostrar inteligencia, no solo extraccion

### Crear

- tabla comparativa:
  - `$/Mbps`
  - ranking de planes
  - ISP mas competitivo

### Output

- notebook o script simple

---

## 5. PRIORIDAD MEDIA - Demo visible (Dia 2)

### Opcion A (rapida)

Notebook:

- lectura de parquet
- graficos simples

### Opcion B

Mejorar Flask:

- tabla de planes
- filtro por ISP

---

## 6. PRIORIDAD CRITICA - Pitch (Dia 2)

### Mensaje central

No decir:
`hicimos scraping`

Decir:
`construimos un sensor competitivo del mercado ISP en tiempo casi real`

---

## 7. Slide minimo (estructura)

1. Problema:
   mercado ISP = datos dispersos y lentos

2. Solucion:
   pipeline automatico + IA

3. Arquitectura:
   HTML + OCR + LLM + validacion

4. Resultado:
   datos estructurados + comparables

5. Impacto:
   decisiones en <24h

---

## 8. Riesgos a evitar

- mostrar dashboard vacio
- enfocarse demasiado en codigo
- no demostrar datos reales
- no explicar impacto en negocio

---

## 9. Definicion de exito

El proyecto esta listo si:

- hay parquet con datos reales
- hay comparacion entre ISPs
- hay narrativa clara de negocio
- hay demo, aunque simple

---

## 10. Regla final

Backend ya esta.

Ahora el trabajo es:
convertirlo en evidencia + historia.

