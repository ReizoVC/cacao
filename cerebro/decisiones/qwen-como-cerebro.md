---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [comparacion_modelos/resumen_ronda3.json, clasificacion_fallos_qwen.md, comparacion_modelos/ronda3_protocolo.md]
---
# Qwen 3.5 9B como cerebro

**Decisión:** descartado como modelo principal. El Qwen Q4 se borró del disco.

## Contexto

Es más rápido que Gemma. Los primeros resultados tenían defectos de integración:
- plantilla de chat;
- modo de pensamiento;
- JSON con caracteres de control;
- UTF-8.

Se corrigieron en la ronda 2 ([[cierre-rapido-mensaje-final]]).

## Criterio fijado antes de la ronda 3 (`ronda3_protocolo.md`)

- ≥ 192/195 tareas completas;
- 0 respuestas vacías;
- 0 confirmaciones falsas finales;
- 0 acciones distintas a lo pedido.

## Resultado medido (`resumen_ronda3.json`, llama-cpp-python 0.3.36)

| | Gemma Q5 | Qwen Q5 |
|---|---:|---:|
| Completas | 195 | 189 |
| Primera herramienta | 192 | 182 |
| Acciones distintas | 2 | 7 |
| Mediana de la primera acción | 3,50 s | 2,40 s |
| tok/s | 35,0 | 51,0 |

`qwen_pass: false`. Los siete casos están clasificados en `clasificacion_fallos_qwen.md`:
- 2 caminos funcionales;
- 1 aclaración;
- 4 fallos operativos.

## No hacer

- No reabrir Qwen por velocidad sin un criterio nuevo fijado de antemano.
- No asumir que iguala a Gemma en español: la evaluación ciega (`resultados_ciegas.md`) sigue sin puntuar.
