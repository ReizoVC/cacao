---
estado: sin verificar
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [REPORTE_TRABAJO_CACAO.md]
---
# Gemma 4 26B A4B (MoE con expertos en la CPU)

**Estado:** no probado. No hay ningún archivo de medición en el repositorio ni en `comparacion_modelos/`.

## Contexto y razonamiento (sin verificar)

`REPORTE_TRABAJO_CACAO.md` §10 (redactado por otra herramienta) argumenta lo siguiente:
- al ser MoE, podría correr descargando expertos a la CPU y la RAM;
- con 16 GB de RAM y la voz simultánea, el margen sería peor;
- la complejidad no se justifica para las tareas sencillas de Cacao.

Hay un dato que apoya la preocupación por la RAM: en la recarga del conjunto en WSL, la RAM de Windows llegó al
99,96 % con Gemma 12B Q4 (`resultados_swa_y_recursos.md`). Esto no es una medición de 26B.

## Decisión

No perseguirlo por ahora. Si se reabre, primero hay que medir con herramientas simuladas:
- RAM y VRAM;
- tok/s y primera acción;
- las 65 frases × 3.

## No hacer

No dar cifras de 26B: no existen.

Relacionadas: [[gemma-q4-por-ahora]], [[riesgos]].
