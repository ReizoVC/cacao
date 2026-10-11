---
estado: verificado
verificado_commit: dd51ba6
verificado_fecha: 2026-10-11
fuentes: [resultados_swa_y_recursos.md, comparacion_modelos/probar_swa_cache.py, comparacion_modelos/ejecutar.py, modelo.py, config.json, probar_carga_modelo.py]
---
# swa_full=False para Gemma (llama-cpp-python): revertido

**Estado:** **revertido en producción** (397d0a2): `config.json` ya no tiene la clave y queda el valor por defecto
de llama-cpp-python. `modelo.crear_llm` sigue pasando `swa_full=config.get("swa_full")`.

**Por qué se revirtió:** con false, las 65 frases en producción dieron 35/42 en la semilla 11 (base 42/42,
`resultados_pruebas_65_fase1_parcial.log`). El banco validó false vaciando la caché antes de cada caso
(`ejecutar.py:286-287`); producción no la vacía.

**Causa sin confirmar.** `comparacion_modelos/probar_swa_cache.py` (dd51ba6), con los 7 casos fallidos en orden
(`datos/swa_cache/brazo_*.json`):

| Brazo | Aciertos | Tiempo | VRAM cargado / pico |
|---|---:|---:|---:|
| A: false, sin vaciar | 7/7 | 24,4 s | 9 892 / 9 978 MiB |
| B: false, vaciando | 7/7 | 36,9 s | 9 814 / 9 869 MiB |
| C: por defecto, sin vaciar | 7/7 | 23,8 s | 12 278 / 12 339 MiB |

A no reprodujo los fallos: la hipótesis «false + prefijo reutilizado» no queda demostrada. Vaciar cuesta ≈ +1,8 s
por tarea. Arranque real con false: 787 → 9 819 MiB (`resultados_arranque_fase1.json`).

## Contexto

Gemma 4 usa atención de ventana deslizante (SWA). Con llama-cpp-python 0.3.36 por defecto, la caché de SWA ocupa
más VRAM. En el banco, `comparacion_modelos/ejecutar.py --swa-full false` inyecta `swa_full` en el `modelo.py` del
runtime aislado (en Git desde cabf3ed).

## Resultado medido en el banco (`resultados_swa_y_recursos.md`)

| | Q5 por defecto | Q5 con False | Q4 por defecto | Q4 con False |
|---|---:|---:|---:|---:|
| Completas (oficial) | 195 | 195 | 195 | 195 |
| Pico de VRAM | 12 756 | 10 052 | 12 065 | 9 553 MiB |
| Primera acción, mediana | 3,50 s | 3,32 s | 3,42 s | 3,19 s |
| tok/s | 35,0 | 37,5 | 38,0 | 42,1 |

Con las 30 frases nuevas: 90/90 en los dos modelos. No hay ronda de esas frases con el valor por defecto.

## Qué falta (con permiso)

1. Explicar los 7 fallos: A con 7 casos no basta; quizá hace falta la secuencia previa entera (#1–25).
2. Pasar las 65 frases × 3 con producción restaurada ([[evaluacion-65-frases]]).

Volver a probar false: poner `"swa_full": false` en `config.json` (con permiso).

## No hacer

- No atribuir las diferencias pequeñas de latencia solo a swa_full: las rondas no fueron simultáneas.
- No comparar el tiempo de carga de Q4 de esa ronda: se leyó desde otro disco.
