---
estado: verificado
verificado_commit: d4b36dd
verificado_fecha: 2026-10-10
fuentes: [resultados_swa_y_recursos.md, comparacion_modelos/ejecutar.py, modelo.py, config.json, probar_carga_modelo.py]
---
# swa_full=False para Gemma (llama-cpp-python)

**Estado:** **preparado en producción, sin aplicar ni medir.** Desde eb5a9c4, `config.json` tiene
`"swa_full": false` y `modelo.crear_llm` pasa `swa_full=config.get("swa_full")`; sin la clave queda el valor por
defecto de llama-cpp-python. Cacao no se reinició: el valor se aplica **en el próximo arranque**, también en el
automático al iniciar sesión.

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

1. Reiniciar Cacao y medir la VRAM real con Whisper y la visión cargados. **No medido.**
2. Pasar las 65 frases × 3 semillas con el prompt de producción ([[evaluacion-65-frases]]).
3. No está comprobado en producción cómo interactúa con la visión (el handler multimodal reevalúa todo el prompt)
   ni con el calentamiento de `voz.py`.

Volver atrás: quitar la clave o poner `null` en `config.json`.

## No hacer

- No atribuir las diferencias pequeñas de latencia solo a swa_full: las rondas no fueron simultáneas.
- No comparar el tiempo de carga de Q4 de esa ronda: se leyó desde otro disco.
