---
estado: verificado
verificado_commit: d95855d
verificado_fecha: 2026-10-11
fuentes: [comparacion_modelos/resumen_convivencia_gemma_q4_qwen3_tts.json, comparacion_modelos/resumen_optimizacion_qwen3_tts.json, comparacion_modelos/resumen_convivencia_completa_wsl.json, config.json]
---
# Qwen3-TTS 0.6B con vLLM-Omni (voz experimental)

**Estado:**
- **Producción:** sigue con **Piper** (`config.voz.piper_voz`).
- **Experimental:** Qwen3-TTS-12Hz-0.6B-Base con vLLM-Omni 0.30.0 en WSL, con el perfil «lean» (talker 0,145,
  code2wav 0,07).

## Alternativas y resultados

| Camino | Resultado | Origen |
|---|---|---|
| PyTorch junto a Gemma Q4 | 23,7 s para 6,16 s de audio (RTF 3,84). Descartado | `resumen_convivencia_gemma_q4_qwen3_tts.json` |
| Fragmentación manual | Primer audio a 16,7 s, total de 29,7 s y una pausa de ~9,3 s. Descartada | `resumen_optimizacion_qwen3_tts.json` |
| FlashAttention 2 compilado localmente | Sin rueda compatible; se canceló la compilación | ídem |
| vLLM-Omni, perfil Cacao 0,16/0,08 | Primer audio caliente en 0,604 s, RTF 0,249, pico de 5 250 MiB | ídem |
| Perfil lean 0,145/0,07, pila completa | Pico conjunto de 14 431 MiB, 1 880 libres | `resumen_convivencia_completa_wsl.json` |

## Detalles operativos

- `VLLM_USE_FLASHINFER_SAMPLER=0`: el JIT de FlashInfer no encontraba `curand.h` (dato del informe de otra
  herramienta, **sin verificar**).
- El primer audio tras arrancar es lento, entre 9 y 21 s según la prueba. Hace falta calentar antes de anunciar que
  la voz está lista.
- Los perfiles y scripts están en `.comparacion-runtime/` (ignorado por Git; ver [[mapa-archivos]]).

## No hacer

- No sustituir Piper sin el lanzador supervisado y una prueba prolongada ([[backlog]]).
- No ejecutar vLLM sobre NTFS desde Windows: el camino acreditado es WSL ([[wsl-dominio-cuda]]).
