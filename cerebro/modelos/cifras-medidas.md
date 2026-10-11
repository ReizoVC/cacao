---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [comparacion_modelos/resumen_ronda3.json, comparacion_modelos/resumen_gemma_q4_ronda3.json, comparacion_modelos/resumen_gemma_q5_llama_b11429.json, comparacion_modelos/resumen_wrench_b11429.json, comparacion_modelos/resumen_ui_mate_b11429.json, resultados_swa_y_recursos.md, comparacion_modelos/resumen_convivencia_completa_wsl.json, SRS.md]
---
# Cifras medidas (con su archivo de origen)

Todas usan 65 frases × 3 semillas y herramientas simuladas, salvo donde se indica. Los `resumen_*.json` están en
`comparacion_modelos/`.

## Modelos como cerebro

| Modelo / motor | Completas | Acciones distintas | 1.ª acción, mediana | tok/s | Pico de VRAM | Origen |
|---|---:|---:|---:|---:|---:|---|
| Gemma Q5 / 0.3.36 | 195 | 2 | 3,50 s | 35,0 | 12 756 | `resumen_ronda3.json` |
| Gemma Q4 / 0.3.36 | 195 | 3 | 3,42 s | 38,0 | 12 065 | `resumen_gemma_q4_ronda3.json` |
| Gemma Q5 / 0.3.36, swa_full=False | 195 | 2 | 3,32 s | 37,5 | 10 052 | `resultados_swa_y_recursos.md` |
| Gemma Q4 / 0.3.36, swa_full=False | 195 | 5 | 3,19 s | 42,1 | 9 553 | ídem |
| Gemma Q5 / b11429 | 195 | 4 | 3,91 s | 41,1 | 9 542 | `resumen_gemma_q5_llama_b11429.json` |
| Qwen 3.5 9B Q5 / 0.3.36 | 189 | 7 | 2,40 s | 51,0 | — | `resumen_ronda3.json` |
| Wrench 9B Q4 / b11429 | 184 | 9 | 2,11 s | 66,9 | 6 177 | `resumen_wrench_b11429.json` |
| UI-Mate 9B Q5 / b11429 | 184 | 11 | 2,64 s | 58,6 | 7 990 | `resumen_ui_mate_b11429.json` |

Notas:
- El pico de VRAM está en MiB e incluye lo que ya usaba la GPU.
- «Completas» sigue el criterio oficial de la ronda 3 (`complete_round2`).
- Todas estas cifras usan el contrato de pruebas, no el agente de producción ([[cierre-rapido-mensaje-final]]).

## Pila experimental en WSL

`resumen_convivencia_completa_wsl.json`: Gemma Q4 con visión, Qwen3-TTS y Whisper.
- **Correctos:** 3/3 en visión, TTS, Whisper y Gemma después de cada ciclo.
- **VRAM:** pico de 14 760 MiB con 1 551 libres; con el perfil lean, 14 431 y 1 880.
- **TTS caliente:** primer audio en 0,574 s.
- **Whisper caliente:** 0,323 s.

Recarga y RAM: [[wsl-dominio-cuda]].

## Producción histórica (SRS §4, sin volver a medir)

| Medida | Cifra | Origen citado por el SRS |
|---|---|---|
| Voz, de soltar la tecla a empezar a hablar | 4,0–6,2 s | `resultados_voz.md` §9 |
| Whisper large-v3-turbo int8, VRAM | 1,34 GB | `resultados_voz.md` §6 |
| Corte del atajo de emergencia | 15–25 ms generando | `resultados_fase5.md` |
| 65 frases con el prompt del 2026-10-06 | 195/195 en primera herramienta, 193/195 completas, 3,91 s de media | `resultados_pruebas_65_fecha.json` |

Esas mediciones son anteriores a las protecciones (9e2c1f1) y no se repitieron después ([[backlog]]).
