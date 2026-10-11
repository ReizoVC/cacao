---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [comparacion_modelos/resumen_wrench_b11429.json, comparacion_modelos/resumen_ui_mate_b11429.json, comparacion_modelos/resumen_gemma_q5_llama_b11429.json]
---
# Wrench 9B y UI-Mate 9B como cerebro

**Decisión:** descartados como cerebro general. UI-Mate solo podría usarse como especialista visual aislado y
supervisado.

## Contexto

Son ajustes especializados de Qwen3.5-9B (herramientas e interfaz gráfica), más rápidos y ligeros que Gemma.

## Resultado medido (llama.cpp b11429, 65 frases × 3)

| | Gemma Q5 | Wrench Q4_K_M | UI-Mate Q5_K_M |
|---|---:|---:|---:|
| Completas | 195/195 | 184/195 | 184/195 |
| Primera herramienta | 192 | 179 | 188 |
| Confirmaciones falsas | 0 | 1 | 1 |
| Acciones distintas | 4 | 9 | 11 |
| tok/s | 41,1 | 66,9 | 58,6 |
| Pico de VRAM | 9 542 MiB | 6 177 MiB | 7 990 MiB |

Además, UI-Mate:
- acertó 2/5 en visión con el protocolo nativo;
- inició acciones en una pregunta de conversación (`conversation_with_actions: 1`).

Orígenes: `resumen_wrench_b11429.json`, `resumen_ui_mate_b11429.json` y `resumen_gemma_q5_llama_b11429.json`.

## No hacer

- No proponerlos como cerebro por su velocidad: fallan más y hacen más cosas no pedidas.
- No usar UI-Mate como ejecutor general sin supervisión.

Relacionadas: [[qwen-como-cerebro]], [[cifras-medidas]].
