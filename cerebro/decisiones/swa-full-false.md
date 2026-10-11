---
estado: verificado
verificado_commit: d95855d
verificado_fecha: 2026-10-11
fuentes: [resultados_swa_y_recursos.md, comparacion_modelos/probar_swa_cache.py, comparacion_modelos/ejecutar.py, modelo.py, config.json, probar_carga_modelo.py]
---
# swa_full=False para Gemma (llama-cpp-python): revertido

**Estado:** **revertido para Gemma** (397d0a2): el perfil `gemma` no tiene la clave (valor por defecto de
llama-cpp-python). Desde 17bb46c, `swa_full: false` está **solo en el perfil `qwen9b`** (decisión del usuario,
2026-10-11), que hoy no es el activo ([[configuracion-vigente]]). `modelo.crear_llm` pasa
`swa_full=config.get("swa_full")`. Si con Qwen cambia algo, se mide en [[memoria-liberable]].

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

**Secuencia larga** (`probar_swa_cache.py A --casos 1-42`, dbb0e42; `datos/swa_cache/resumen_largo_A.json`):
**42/42**. Ventana deslizante de Gemma: 1 024. Cada caso reutiliza 3 930–3 932 tokens de un prompt de 3 965–3 976
(`kv_cache_seq_rm` aceptado siempre). Ni los casos que descartan más que la ventana fallan:

| Caso | Tokens previos | Prompt | Reutilizados | Descartados | Acierto |
|---|---:|---:|---:|---:|---|
| #19 | 5 461 | 3 967 | 3 931 | 1 530 | sí |
| #23 | 4 993 | 3 969 | 3 932 | 1 061 | sí |
| #26 | 4 224 | 3 971 | 3 930 | 294 | sí |
| #28 | 5 459 | 3 969 | 3 931 | 1 528 | sí |
| #42 | 4 399 | 3 970 | 3 932 | 467 | sí |

El resto (#1–42) también acierta. El control C en las 65 × 3 dio 194/195 ([[evaluacion-65-frases]]). **Los 7
fallos no se reproducen** con el mismo código y la misma configuración; la causa sigue abierta. No se probaron
arreglos.

## Qué falta

- Decidir si vuelve false (≈ 2,4 GiB menos de VRAM) con una prueba larga en producción. Lo decide el usuario.

Volver a probar false con Gemma: poner `"swa_full": false` en el perfil `gemma` de `config.json` (con permiso).

## No hacer

- No atribuir las diferencias pequeñas de latencia solo a swa_full: las rondas no fueron simultáneas.
- No comparar el tiempo de carga de Q4 de esa ronda: se leyó desde otro disco.
