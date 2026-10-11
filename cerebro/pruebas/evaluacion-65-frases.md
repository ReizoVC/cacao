---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [pruebas.json, evaluar_pruebas.py, benchmark_gramatica.py, comparacion_modelos/criterios.py, comparacion_modelos/integracion.py, SRS.md]
---
# Evaluación con las 65 frases

## Qué es

- **`pruebas.json`:** 65 frases reales con `id`, `tipo`, `esperado` (primera herramienta aceptable) y `requiere`
  (herramientas que deben aparecer). Semillas 11, 22 y 33, es decir, 195 casos.
- **Uso:** es la regresión de comportamiento del modelo. Hay que pasarla cada vez que cambian el prompt, el esquema,
  las herramientas o el modelo.

## Cómo correrla (producción, herramientas simuladas)

```
set SIN_REALES=1
set CONFIRMAR=s
.venv\Scripts\python evaluar_pruebas.py 11 22 33
```

- **Herramientas:** `benchmark_gramatica.py` toma de `agente_minimo.py` el esquema, el prompt y el bucle (con
  `ast`), con herramientas simuladas y ventanas fijas (`VENTANAS_SIM`).
- **`SIN_REALES=1`:** simula también `listar_carpeta`, `leer_archivo` y `ver_pantalla`. **Sin él, leen el PC real.**
- **`CONFIRMAR=s`:** deja avanzar las simuladas que piden confirmación.
- **Opciones:**
  - `TIPOS=…` filtra por tipo;
  - `SALIDA=archivo.json` cambia la salida (por defecto `resultados_pruebas.json`, que Git ignora).
- **Carga Gemma:** GPU libre.

## Criterios

- **Producción (`evaluar_pruebas.py`):** primera herramienta (`primer_paso_ok` con `VERIFICACION`) y tarea
  completa.
- **Comparación de modelos (`comparacion_modelos/criterios.py` + `integracion.complete_round2`):** también comprueba
  argumentos y efectos. Por ejemplo, el volumen en el valor pedido o el archivo correcto movido. Solo cubre los id
  1–65.

## Baseline con el prompt de producción

Del SRS §4.4, con origen en `resultados_pruebas_65_fecha.json` (2026-10-06):
- primera herramienta: 195/195;
- tareas completas: 193/195;
- media: 3,91 s.

Es **anterior** a las protecciones (9e2c1f1). No hay una pasada posterior con el prompt de producción ([[backlog]]).

Las rondas 2 y 3 (195/195 para Gemma Q5) usan el contrato de pruebas de `integracion.py`, no el de producción
([[cierre-rapido-mensaje-final]], [[comparacion-modelos]]).

## Conjunto nuevo

`comparacion_modelos/pruebas_nuevas_30.json` tiene 30 frases de generalización (id 101–130, semillas 44, 55 y 66).
**No está en Git** y `criterios.py` no las cubre.
