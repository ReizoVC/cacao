---
estado: verificado
verificado_commit: 9230d4d
verificado_fecha: 2026-10-12
fuentes: [comparacion_modelos/resumen_qwen3_tts_windows.json, comparacion_modelos/resumen_qwen3_tts_llama_cpp.json]
---
# Qwen3-TTS 0.6B en Windows nativo (2026-10-12)

**Resultado: llama.cpp cumple el criterio de «prometedor»; qwen3-tts.cpp no.** El usuario aprobó la calidad de
los dos motores (`faseA_f16` y luego la de llama.cpp). Es solo banco: nada se conecta a Cacao y
Piper sigue en producción ([[qwen3-tts-vllm-omni]], [[voz-candidatas]]).

Montaje común:
- pesos oficiales `Qwen/Qwen3-TTS-12Hz-0.6B-Base`, revisión `5d83992`;
- voz `A1_equilibrada.wav` (sintética);
- 12 frases inventadas, sintetizadas oración a oración: no hay streaming, así que el «primer audio» es la primera
  oración entera;
- Cacao cerrado y sin juegos.

Todo vive en `.comparacion-runtime/` (ignorado por Git, [[mapa-archivos]]).

## Los dos motores (fase A, el TTS solo)

| | qwen3-tts.cpp F16 | qwen3-tts.cpp Q8_0 | **llama.cpp Q8_0** |
|---|---:|---:|---:|
| RTF total (máx.) | 0,74 (0,85) | 5,09 (5,42) | **0,31 (0,46)** |
| Primer audio en caliente, mediana (máx.) | 2,37 s (4,88) | 16,6 s (35,6) | **0,88 s (2,10)** |
| Primer audio en frío, desde el arranque | 29,0 s | 47,0 s | **3,2 s** |
| Pico de VRAM sobre la base | 2 883 MiB | 2 406 MiB | 3 334 MiB |
| Pico de RAM | 972 MB | 972 MB | 2 034 MB |

**qwen3-tts.cpp** (`predict-woo`, MIT, `b3ba140`):
- Compila con VS 2022 y CUDA 13.4, pero la DLL hay que generarla con `CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON`.
- Su Q4_K cae a F16 sin avisar.
- La huella de voz (x-vector) tarda 25 s, una vez por voz.
- **Q8_0 es 7 veces más lenta**, por una causa no obvia: con `GGML_SCHED_DEBUG=2`, Q8_0 y F16 tienen las mismas
  particiones, y las 6 que van a la CPU son del vocoder (`CONV_TRANSPOSE`).

**llama.cpp** (`81bc6b8`, el que fija `KreutzM/qwen-3-tts` PR #11; MIT):
- Se usa `llama-tts` oficial, compilado en Windows sin cambios (VS 2022, Ninja, CUDA 13.4, `sm_120`).
- Para medir en caliente, un banco propio (`banco_tts.cpp`, API `mtmd gen_audio`) carga una vez y sintetiza todo.
- Los pesos 0.6B se convirtieron con su `convert_hf_to_gguf.py` (talker y mmproj Q8_0). KreutzM usaba el 1.7B.
- **La huella no se puede guardar:** `llama-tts` recibe el audio de referencia y lo procesa en cada síntesis, en
  ≈ 0,03 s.
- Muestreo: semilla 42, temperatura 0,9.

## Voz por frases (llama.cpp, simulada)

La síntesis sigue oración a oración mientras suena la anterior. Simulado con las 12 frases y 4 respuestas de 3 a 5
oraciones (`simular_por_frases.py`):
- **un solo hueco: 0,22 s**, en «Buenos días. Hoy es…». La primera oración es muy corta y la segunda tarda más de lo
  que dura la primera;
- en las respuestas largas, sin huecos y con el primer audio en 0,46–0,75 s;
- el primer audio supera 1,2 s solo cuando la primera oración es larga (#6 y #9, de una sola oración: 1,9–2,1 s).

## Fase B: convivencia (llama.cpp Q8_0, `convivencia.py`)

Con `config.json` tal cual:
- `qwen9b` con caché por estados, flash, KV q8_0 y `use_mmap=false`;
- Whisper en la GPU y Piper calentado;
- el TTS residente tras una síntesis en frío;
- pedido simulado y captura **sintética**;
- después, las 12 frases con todo cargado.

| Paso (MiB de toda la GPU, base 776) | |
|---|---:|
| Qwen + Whisper, calentado | 8 683 |
| + TTS en espera | 12 009 |
| **Pico (con visión y TTS)** | **13 264 → 3 047 libres** |

Con Qwen cargado, el TTS da RTF 0,33 (máx. 0,44) y un primer audio en caliente de 0,99 s de mediana (máx. 1,91).

**Criterio:**
- RTF ≤ 0,5 ✓;
- primer audio en caliente ≤ 1 s: ✓ en la mediana, ✗ en oraciones largas;
- ≥ 500 MiB libres con visión ✓ (3 047);
- calidad: falta escuchar llama.cpp.

## Integración (2026-10-12)

El usuario aprobó la calidad de llama.cpp. Está integrado en Cacao con Piper de respaldo, apagado por defecto
(`voz.tts_motor`). La partición por comas y la prueba prolongada están en [[voz-qwen3]].
