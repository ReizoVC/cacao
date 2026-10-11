---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [resultados_swa_y_recursos.md, comparacion_modelos/ejecutar.py, modelo.py, config.json]
---
# swa_full=False para Gemma (llama-cpp-python)

**Estado:** recomendado, **no aplicado** en producción. Ni `modelo.py` ni `config.json` pasan `swa_full`.

## Contexto

Gemma 4 usa atención de ventana deslizante (SWA). Con llama-cpp-python 0.3.36 por defecto, la caché de SWA ocupa
más VRAM. El soporte de la prueba está en `comparacion_modelos/ejecutar.py` (`--swa-full false`), que inyecta
`swa_full` en el `modelo.py` del runtime aislado. Ese cambio está **sin commit** en el árbol de trabajo
([[backlog]]).

## Resultado medido (`resultados_swa_y_recursos.md`)

| | Q5 por defecto | Q5 con False | Q4 por defecto | Q4 con False |
|---|---:|---:|---:|---:|
| Completas (oficial) | 195 | 195 | 195 | 195 |
| Pico de VRAM | 12 756 | 10 052 | 12 065 | 9 553 MiB |
| Primera acción, mediana | 3,50 s | 3,32 s | 3,42 s | 3,19 s |
| tok/s | 35,0 | 37,5 | 38,0 | 42,1 |

Con las 30 frases nuevas: 90/90 en los dos modelos. No hay ronda de esas frases con el valor por defecto.

## Decisión propuesta

Aplicarlo en producción, previo permiso:
1. `modelo.py`: pasar `swa_full=config.get("swa_full")`;
2. `config.json`: `swa_full: false`;
3. volver a pasar las suites y las 65 frases.

## No hacer

- No atribuir las diferencias pequeñas de latencia solo a swa_full: las rondas no fueron simultáneas.
- No comparar el tiempo de carga de Q4 de esa ronda: se leyó desde otro disco.
