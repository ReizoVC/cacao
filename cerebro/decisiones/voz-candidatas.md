---
estado: sin verificar
verificado_commit: c297bcb
verificado_fecha: 2026-10-11
fuentes: [config.json]
---
# Voz personalizada: motores candidatos en Windows (investigación del 2026-10-11)

**Sin verificar:** sale de buscar en la web; nada se ha medido en este PC. El bloqueo no es la VRAM (con Qwen 9B
quedan ~5,9 GB libres, [[memoria-liberable]]), sino un motor rápido en **Windows nativo**: Qwen3-TTS solo fue rápido
con vLLM-Omni en WSL, y WSL está descartado ([[qwen3-tts-vllm-omni]]).

| Candidato | Clonar voz | Español | Windows nativo | VRAM | Velocidad publicada | Licencia |
|---|---|---|---|---|---|---|
| Qwen3-TTS 0.6B en GGML/llama.cpp (`qwen3-tts.cpp`, o el backend llama.cpp de `KreutzM/qwen-3-tts`) | sí (Base) | sí (10 idiomas) | sin probar: CMake + MSVC; el backend de KreutzM se probó en WSL2 | ¿? | RTF ≈ 0,38–0,39 en RTX 3060 (KreutzM, Q8_0); `qwen3-tts.cpp` ~3–4× más rápido que PyTorch | MIT (cpp) |
| Chatterbox Multilingual con NVIDIA NVIGI (GGML, q4_0 + decoder F16) | sí | sí (23 idiomas) | sí: plugin de NVIDIA con CUDA, Vulkan y D3D12 | ≥ 3,5 GB (presupuesto de NVIDIA) | «casi tiempo real» (sin cifra) | MIT (modelo) |
| XTTS v2 (PyTorch) | sí, con ~6 s de audio | sí, bien documentado | PyTorch en Windows | ~4 GB | ~2 s por frase en RTX 3060 | CPML (no comercial; vale para uso personal) |
| Kokoro | no (voces fijas) | sí | sí, incluso en CPU | 2–3 GB | el más rápido | Apache 2.0 |

Lo ya medido aquí: Qwen3-TTS con PyTorch en Windows, RTF 3,84 (descartado); con vLLM-Omni en WSL, RTF 0,249, primer
audio en 0,6 s y pico de 5 250 MiB.

## Siguiente paso propuesto

Pedir permiso para descargar y medir en el banco (`.comparacion-runtime/`), sin tocar Piper ni producción:
1. Qwen3-TTS 0.6B en llama.cpp/GGML nativo. Es la voz que ya se eligió; falta saber si compila en Windows.
2. Chatterbox Multilingual por NVIGI. Es el camino con soporte oficial en Windows.

Para cada uno: RTF, primer audio, VRAM junto a Qwen 9B y Whisper, y calidad en español (evaluación del usuario).
Antes, el usuario decide **qué voz**: clonar una voz de referencia (con permiso de su dueño) o usar una voz prediseñada.
