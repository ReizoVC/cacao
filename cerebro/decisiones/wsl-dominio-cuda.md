---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [resultados_comparacion_modelos.md, comparacion_modelos/resumen_convivencia_wsl.json, comparacion_modelos/resumen_convivencia_completa_wsl.json, resultados_swa_y_recursos.md, config.json]
---
# Arquitectura experimental en WSL (un solo dominio CUDA)

**Estado de la decisión:** candidata experimental. Producción sigue en Windows con llama-cpp-python
([[configuracion-vigente]]).

## Contexto

Qwen3-TTS solo es rápido con vLLM-Omni, que corre en Linux ([[qwen3-tts-vllm-omni]]). Por eso hacía falta que
Gemma, el TTS y Whisper convivieran en la misma GPU de 16 GB.

## Alternativas probadas

1. **Gemma en Windows y TTS en WSL.** Cabe en memoria, pero el servidor Windows de Gemma dejó de aceptar
   conexiones después de iniciar CUDA en WSL. No quedó acreditada (`resultados_comparacion_modelos.md`, sección
   «Streaming real con vLLM-Omni»).
2. **Todo en un único WSL:** llama.cpp b11429 con Gemma Q4, vLLM-Omni y faster-whisper. Es estable.

## Resultado medido

| Prueba | Cifra | Archivo |
|---|---|---|
| Gemma + TTS en WSL | 12/12 respuestas, 6/6 audios; pico de 13 162 MiB, 3 149 libres | `resumen_convivencia_wsl.json` |
| Gemma + visión + TTS + Whisper | 3/3 en cada servicio; pico de 14 760 MiB, 1 551 libres | `resumen_convivencia_completa_wsl.json` |
| Recarga completa | 374,3 s hasta los tres listos; RAM de Windows al 99,96 %; 1,15 GiB de swap en WSL | `resultados_swa_y_recursos.md` |

En esa recarga, el TTS ocupa ≈259 s de los 374,3. Los modelos se leen desde `/mnt/d` y `/mnt/c` (9P).

## Decisión

- Mantener un único dominio CUDA en WSL para la integración experimental.
- Producción no cambia hasta que exista un lanzador supervisado y una prueba prolongada (recuperación, suspensión,
  modo juego) ([[backlog]]).

## No hacer

- No mezclar motores CUDA de Windows y de WSL para la integración.
- No dar por buena la convivencia porque «cabe»: hay que medir los picos con visión, voz y transcripción
  simultáneas.
- No estimar la mejora de carga con otro disco sin medirla.
- No integrar sin calentamiento: el primer audio del TTS tarda de 9 a 21 s según la prueba.

Relacionadas: [[gemma-q4-por-ahora]], [[motor-llama-cpp]], [[riesgos]].
