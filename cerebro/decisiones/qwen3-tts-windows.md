---
estado: verificado
verificado_commit: e10b522
verificado_fecha: 2026-10-12
fuentes: [comparacion_modelos/resumen_qwen3_tts_windows.json]
---
# Qwen3-TTS 0.6B en Windows nativo (qwen3-tts.cpp, 2026-10-12)

**Resultado: no es prometedor tal como está.** Compila y suena (calidad pendiente de que el usuario escuche), pero el
mejor RTF es **0,74** (criterio ≤ 0,5). Por eso **la fase B (convivencia) no se corrió**. Solo banco: nada toca a
Cacao, Piper sigue en producción ([[qwen3-tts-vllm-omni]], [[voz-candidatas]]).

## Montaje

- Motor: `predict-woo/qwen3-tts.cpp` (MIT), commit `b3ba140`, ggml `3af5f57`.
- Compilación:
  - VS 2022 (vcvars64) con Ninja, CUDA 13.4, `sm_120` y `GGML_CUDA=ON`. Compila sin cambios.
  - La DLL no exporta símbolos en Windows: se reconfiguró con `CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON`.
- Pesos: `Qwen/Qwen3-TTS-12Hz-0.6B-Base` oficial, revisión `5d83992` (la copia local que ya existía), convertidos con
  los scripts del repo en un venv propio (torch CPU).
- **Q4_K no existe en la práctica:** gguf-py no la cuantiza y el conversor cae a F16 en los 271 tensores. Se midieron
  Q8_0 y F16.
- Voz: clonación por x-vector de `A1_equilibrada.wav` (voz sintética; sin texto de referencia). El embedding se
  calcula una vez y se reutiliza.
- Todo vive en `.comparacion-runtime/qwen3-tts-cpp/` (ignorado por Git), con estas subcarpetas:
  - `fuente/`: lo descargado;
  - `scripts/`: `compilar.bat` y `tts_banco.py`, que usa ctypes y se corre con `-I`;
  - `modelos/`;
  - `salida/`: los WAV para escuchar.

## Fase A: el TTS solo

Cacao estaba cerrado y no había juegos. Son 12 frases típicas e inventadas, sintetizadas oración a oración: la
librería no hace streaming, así que el «primer audio» es lo que tarda la primera oración entera. Muestreo por defecto
(temperatura 0,9), sin semilla.

| | Q8_0 | F16 |
|---|---:|---:|
| RTF total (máx.) | 5,09 (5,42) | **0,74 (0,85)** |
| Primer audio en caliente, mediana (máx.) | 16,6 s (35,6) | 2,37 s (4,88) |
| Frase más corta («Hecho.», 0,7 s de audio) | 3,78 s | 0,59 s |
| Carga de modelos | 2,1 s | 1,3 s |
| Embedding de la voz | 25,6 s | 25,4 s |
| Primer audio en frío, desde el arranque del proceso | 47,0 s | 29,0 s |
| Pico de VRAM sobre la base | 2 406 MiB | 2 883 MiB |
| Pico de RAM (working set) | 972 MB | 972 MB |

Lectura:
- Corre en CUDA0 en las tres partes. En F16, la generación de códigos se lleva ≈ 75 % del tiempo. Es secuencial:
  un paso del talker y 15 del predictor por cada trama de 80 ms. El vocoder pesa poco.
- Q8_0 es ≈ 7 veces más lenta que F16 en esta GPU (no se investigó la causa).
- El embedding (25 s) se paga una vez por voz. Se puede guardar en un archivo (`--save-speaker`); el frío sin él no
  se midió.
- Criterio: RTF ≤ 0,5 ✗; primer audio en caliente ≤ 1 s ✗ (solo en frases de una palabra). La VRAM sí cabría
  (≈ 2,9 GB frente a los ≈ 5,9 GB libres con visión, [[memoria-liberable]]), pero no se midió junto a Cacao.

## Qué queda

- Escuchar los WAV (`salida/faseA_f16/` y `salida/faseA_q8_0/`).
- Alternativa de la orden sin probar: el backend llama.cpp de `KreutzM/qwen-3-tts` (PR #11). Publica RTF ≈ 0,38 en
  una RTX 3060, sin verificar aquí. Requiere una decisión del coordinador.
