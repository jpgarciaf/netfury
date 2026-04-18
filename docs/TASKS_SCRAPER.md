# Tareas - Modulo Scraper

## Fase 1: Investigacion y Configuracion
- [ ] Identificar los ISPs objetivo del mercado (CNT, Netlife, Claro, Movistar, etc.)
- [ ] Analizar la estructura de las paginas web de cada ISP (URLs, HTML, carga dinamica)
- [ ] Definir el modelo de datos: campos a extraer (plan, velocidad, precio, promociones, tipo de conexion)
- [ ] Configurar entorno de desarrollo (venv, dependencias, .env)

## Fase 2: Desarrollo de Spiders
- [ ] Crear spider base con interfaz comun para todos los ISPs
- [ ] Implementar spider para ISP #1 (definir cual)
- [ ] Implementar spider para ISP #2
- [ ] Implementar spider para ISP #3
- [ ] Implementar spider para ISP #4
- [ ] Manejar paginas con renderizado JavaScript (Selenium/Playwright)

## Fase 3: Procesamiento de Datos
- [ ] Implementar limpieza y normalizacion de datos extraidos
- [ ] Estandarizar formatos de precios y velocidades entre proveedores
- [ ] Exportar datos a CSV/JSON en `data/`
- [ ] Implementar validacion de datos (detectar valores faltantes o anomalos)

## Fase 4: Automatizacion y Robustez
- [ ] Agregar manejo de errores y reintentos en los spiders
- [ ] Implementar rotacion de user-agents y delays entre peticiones
- [ ] Agregar logging para monitorear ejecuciones
- [ ] Programar ejecucion periodica (cron o scheduler)

## Fase 5: Analisis
- [ ] Comparar precios por velocidad equivalente entre proveedores
- [ ] Calcular relacion precio/velocidad (costo por Mbps)
- [ ] Detectar cambios de precios respecto a ejecuciones anteriores
- [ ] Generar resumen estadistico de los datos recopilados
