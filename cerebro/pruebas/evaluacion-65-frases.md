---
estado: verificado
verificado_commit: e3dfe04
verificado_fecha: 2026-10-11
fuentes: [pruebas.json, evaluar_pruebas.py, benchmark_gramatica.py, comparacion_modelos/probar_swa_cache.py, comparacion_modelos/criterios.py, comparacion_modelos/integracion.py, SRS.md]
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

Es **anterior** a las protecciones (9e2c1f1).

**Pasada del 2026-10-11** (Fase 1, sin `swa_full`; `probar_swa_cache.py C --casos todos --semillas 11 22 33`,
origen `comparacion_modelos/datos/swa_cache/resumen_65x3_C.json`, ignorado por Git):
- primera herramienta: 195/195; tareas completas: 194/195 (65, 64 y 65);
- media por tarea: 4,65–4,79 s; VRAM pico 13 095 MiB;
- frente a la base: #44 pasa en las semillas 11 y 33 (antes no enfocaba); #56 falla en la 22 (`listar_controles`
  con `id_ventana` 0 sin listar ventanas; termina diciendo que no pudo).

**Pasadas con perfiles** (`probar_swa_cache.py`, `--semillas 11 22 33`, datos en `datos/swa_cache/`):

| Perfil y código | Archivo | Completas (11 / 22 / 33) | VRAM pico |
|---|---|---:|---:|
| `qwen9b`, 17bb46c (cierre rápido sin validar) | `resumen_qwen65x3_A.json` + `resumen_qwen65x3s2233_A.json` | 58 / 58 / 57 = 173 | 8 213 MiB |
| `qwen9b`, d95855d (sin cierre rápido) | `resumen_qwen65x3cierre_A.json` | 59 / 61 / 62 = 182 | 8 214 MiB |
| `gemma`, d95855d (`mensaje_final` validado, blindajes) | `resumen_gemma65x3cierre_C.json` | 65 / 65 / 65 = **195** | 12 940 MiB |

Con Gemma, ningún `mensaje_final` se descartó y ningún `forzar` se ignoró (registro de la corrida); #56 s22 ya pasa.
Clasificación de Qwen en [[resultado-qwen9b-2026-10-11]].

Las rondas 2 y 3 (195/195 para Gemma Q5) usan el contrato de pruebas de `integracion.py`, no el de producción
([[cierre-rapido-mensaje-final]], [[comparacion-modelos]]).

## Conjunto nuevo

`comparacion_modelos/pruebas_nuevas_30.json` tiene 30 frases de generalización (id 101–130, semillas 44, 55 y 66).
**No está en Git** y `criterios.py` no las cubre.
