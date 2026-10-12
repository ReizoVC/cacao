---
estado: verificado
verificado_commit: c297bcb
verificado_fecha: 2026-10-11
fuentes: [config.json, comparacion_modelos/resumen_convivencia_completa_wsl.json, comparacion_modelos/resumen_optimizacion_qwen3_tts.json]
---
# No reducir Whisper ni el contexto para ganar VRAM

**Decisión:**
- Mantener faster-whisper `large-v3-turbo` `int8_float16` y `n_ctx` = 16 384.
- Si falta VRAM, recortar primero las reservas del TTS experimental.

## Contexto

En la pila completa en WSL el margen era de unos 1,5 GiB ([[wsl-dominio-cuda]]). Se plantearon tres caminos:
1. bajar Whisper;
2. reducir el contexto;
3. recortar la reserva de vLLM-Omni.

## Resultado medido

- **Contexto 16 384 → 8 192**, con Gemma Q4 + mmproj, flash attention y KV q8_0: solo **81 MiB** menos (8 040
  frente a 7 959 MiB de incremento). Origen: `resumen_convivencia_completa_wsl.json`, `comparacion_contexto`.
- **Perfil de TTS ajustado** (talker 0,145, code2wav 0,07): pico conjunto de 14 431 MiB y 1 880 libres, frente a
  14 760 y 1 551 con el perfil original, sin tocar Whisper. Origen: `resumen_convivencia_completa_wsl.json`,
  `ajuste_qwen3_tts`.
- **Whisper:** usa unos 1,34 GB (SRS RNF-12, `resultados_voz.md`). No se probó un modelo más pequeño en la pila
  completa.

## No hacer

- No bajar Whisper de modelo ni de precisión sin pedido expreso del usuario.
- No reducir `n_ctx`: el ahorro es marginal y se pierde la mitad del historial útil.
- No bajar más la reserva del TTS sin una prueba prolongada: el talker quedó con 2 416 tokens KV para un máximo de
  2 048, una concurrencia de 1,18 (`resumen_convivencia_completa_wsl.json`, `perfil_ajustado`).

Relacionadas: [[qwen3-tts-vllm-omni]], [[configuracion-vigente]].
