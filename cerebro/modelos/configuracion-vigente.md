---
estado: verificado
verificado_commit: 829fea9
verificado_fecha: 2026-10-11
fuentes: [config.json, modelo.py, vision.py, muestreo_gramatica.py, requirements.txt, agente_minimo.py, probar_carga_modelo.py]
---
# Configuración vigente de producción

Leída de `config.json`. La fuente de verdad es ese archivo; esta página puede quedar atrasada.

## LLM: perfiles (17bb46c)

`modelo_activo` elige el perfil de `perfiles`, y `modelo.aplicar_perfil()` lo pone encima del resto de claves.
**Hoy: `gemma`.** `qwen9b` se probó en producción el 2026-10-11 y no pasó; se volvió a Gemma (829fea9,
[[qwen-como-cerebro]]).
**Volver a Gemma:** en `config.json`, `"modelo_activo": "gemma"` y reiniciar Cacao. Nada más cambia.
`probar_carga_modelo.py` comprueba los dos perfiles sin cargar el modelo.

| Perfil | `modelo` | `mmproj` | Extras |
|---|---|---|---|
| `gemma` | `modelos/gemma-4-12b-it-Q5_K_M.gguf` | `modelos/mmproj/mmproj-F16.gguf` | sin `swa_full` |
| `qwen9b` | `modelos/comparacion_local/Qwen3.5-9B-UD-Q5_K_XL.gguf` (copia en C:) | `modelos/comparacion/mmproj-F16.gguf` | `swa_full: false`, `sin_pensamiento: true` |

`sin_pensamiento`: la plantilla de chat del modelo con `enable_thinking=false`, en el texto (`modelo.py`) y en
`ver_pantalla` (`vision.py`), igual que el banco. El prompt y el esquema son los mismos con los dos perfiles.
`mmproj` vacío o `null` desactiva `ver_pantalla`.

Claves comunes:

| Clave | Valor |
|---|---|
| Motor | llama-cpp-python 0.3.36 (`requirements.txt`) |
| `n_ctx` | 16 384 |
| `n_gpu_layers` | -1 (todas en la GPU) |
| `flash_attn` | true |
| `type_k` / `type_v` | q8_0 / q8_0 |
| `modo_gramatica` | `topk` (`muestreo_gramatica.LlamaRapida`) |
| Regla `char` de la gramática JSON | estricta, sin U+0000–U+001F: la pone `modelo.py` al importarse (7d31aa7) |
| `use_mmap` | false ([[use-mmap-false]]) |
| `swa_full` | solo en el perfil `qwen9b` (false). Gemma va sin la clave desde 397d0a2 ([[swa-full-false]]) |
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
