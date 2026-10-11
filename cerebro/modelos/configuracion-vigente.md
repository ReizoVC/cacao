---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [config.json, modelo.py, muestreo_gramatica.py, requirements.txt, agente_minimo.py]
---
# Configuración vigente de producción

Leída de `config.json`. La fuente de verdad es ese archivo; esta página puede quedar atrasada.

## LLM

| Clave | Valor |
|---|---|
| `modelo` | `modelos/gemma-4-12b-it-Q5_K_M.gguf` (Gemma 4 12B Q5_K_M) |
| `mmproj` | `modelos/mmproj/mmproj-F16.gguf` (visión; vacío o `null` desactiva `ver_pantalla`) |
| Motor | llama-cpp-python 0.3.36 (`requirements.txt`) |
| `n_ctx` | 16 384 |
| `n_gpu_layers` | -1 (todas en la GPU) |
| `flash_attn` | true |
| `type_k` / `type_v` | q8_0 / q8_0 |
| `modo_gramatica` | `topk` (`muestreo_gramatica.LlamaRapida`) |
| `use_mmap` | false ([[use-mmap-false]]) |
| `swa_full` | no se pasa: el valor por defecto de llama-cpp-python ([[swa-full-false]]) |
| Muestreo en `pedir_accion` | temperatura 0,3, top_p 0,95, top_k 64, 512 tokens |

## Voz

| Clave | Valor |
|---|---|
| `voz.motor_transcripcion` | whisper |
| `voz.whisper_modelo` / `whisper_tipo` | large-v3-turbo / int8_float16 |
| `voz.whisper_pausa` | base (en la CPU, para la pausa de modo juego) |
| `voz.piper_voz` | voz ONNX de Piper en `modelos/piper/` |
| `voz.atajo_hablar` | ctrl+espacio |
| `voz.palabra_activacion.activa` | true |
| `voz.seguimiento.segundos` | 8 |

## Otros interruptores

| Clave | Valor |
|---|---|
| `modo_juego.activo` | true |
| `ui.activa` / `ui.lanzar` | true / true |
| `autocompletar_login.activa` | false |
| Modo sin confirmación | empieza apagado en cada arranque, por código; no hay clave |

## Experimental (no es producción)

Gemma UD-Q4_K_XL + llama.cpp b11429 + Qwen3-TTS + Whisper en WSL ([[wsl-dominio-cuda]]). La comparación de modelos
usa su propio `config.json` copiado en `.comparacion-runtime/<modelo>/` ([[comparacion-modelos]]).

## Cambiar algo aquí

Pide permiso, cambia `config.json`, vuelve a pasar las suites y las 65 frases, y actualiza esta página y
[[log]].
