---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [config.json, modelo.py, guia_instalacion_agente.md, resultados_ram_mmap.json, resultados_ram_nommap.json]
---
# use_mmap = false

**Decisión vigente:** `config.json` → `"use_mmap": false`.

## Contexto

El equipo tiene 16 GB de RAM física. Con el GGUF mapeado (`use_mmap: true`), el archivo seguía ocupando RAM
física aunque las capas estuvieran en la GPU.

## Resultado medido

- **Nota de `config.json`:** con `false`, el modelo, ya copiado a la GPU, deja unos 1,3 GB de RAM física.
- **Guía de instalación, «Problemas comunes»:** con mmap, el conjunto de trabajo llegaba a ~8,6 GB, a la misma
  velocidad.
- **Detalle por tarea:** `resultados_ram_mmap.json` y `resultados_ram_nommap.json` (`medir_ram.py`).

## No hacer

- No volver a `use_mmap: true` para «cargar más rápido».
- En llama-server (WSL) el equivalente es `--load-mode none` o no usar mmap; las pruebas lo usaron
  ([[motor-llama-cpp]]).

Relacionadas: [[configuracion-vigente]], [[lecciones]].
