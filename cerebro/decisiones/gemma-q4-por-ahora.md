---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [config.json, comparacion_modelos/resumen_gemma_q4_ronda3.json, comparacion_modelos/resumen_ronda3.json, resultados_swa_y_recursos.md, comparacion_modelos/motor_llama_cpp_b11429.json]
---
# Gemma Q4 «por ahora»: solo en la pila experimental

**Estado:**
- **Producción:** Gemma 4 12B **Q5_K_M** (`config.json`).
- **Pila experimental en WSL:** Gemma UD-Q4_K_XL ([[wsl-dominio-cuda]]).
- **Cambio de producción a Q4:** no está aprobado.

## Contexto

Q4 libera disco y VRAM para que quepan la voz nueva y Whisper.

## Resultado medido (llama-cpp-python 0.3.36, ronda 3, 65 frases × 3)

| | Q5 | Q4 | Origen |
|---|---:|---:|---|
| Completas (criterio oficial) | 195/195 | 195/195 | `resumen_ronda3.json`, `resumen_gemma_q4_ronda3.json` |
| Acciones distintas a lo pedido | 2 | 3 | ídem |
| tok/s | 35,0 | 38,0 | ídem |
| Pico de VRAM | 12 756 MiB | 12 065 MiB | ídem |
| Con swa_full=False: pico / tok/s | 10 052 / 37,5 | 9 553 / 42,1 | `resultados_swa_y_recursos.md` |
| Con swa_full=False, 30 frases nuevas: correcciones de la protección | 5 | 9 | ídem |
| Tamaño del archivo | 8 413 576 000 B | 7 366 423 360 B | tamaño en disco |

Con llama.cpp b11429, Q4 usó 8 482 MiB en texto y 8 956 MiB con visión (`motor_llama_cpp_b11429.json`).

## Decisión

- Q4 en la pila experimental.
- Q5 en producción hasta cumplir [[criterio-de-cambio]].
- Falta la evaluación a ciegas de la conversación Q5 frente a Q4 (`resultados_ciegas_q4.md`, sin puntuar).

## No hacer

- No cambiar `config.json` a Q4 sin permiso y sin volver a pasar las 65 frases con el prompt de producción.
- No presentar «195/195» como prueba de igual calidad: Q4 acumula más marcas de auditoría.

Relacionadas: [[swa-full-false]], [[cifras-medidas]].
