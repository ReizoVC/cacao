---
estado: verificado
verificado_commit: e3dfe04
verificado_fecha: 2026-10-11
fuentes: [voz.py, agente_minimo.py, transcripcion.py, microfono.py, confirmacion_voz.py, config.json]
---
# Voz

`voz.py` es el proceso principal en producción. El lanzador ejecuta `voz.py`, que importa `agente_minimo` (sin
cargar el modelo). Al arrancar, `a.salida_utf8()` pone la salida en UTF-8 y `preparar()` llama primero a
`a.cargar_modelo()` (Gemma y las apps del menú Inicio) y después a Whisper y Piper.

## Entrada

- Pulsar para hablar: `voz.atajo_hablar` = `ctrl+espacio` (`microfono.py`).
- Palabra «Cacao» y escucha de seguimiento: [[palabra-activacion]].
- Grabación de 30 s como máximo (`max_grabacion_s`).

## Frenos antes del agente (`voz.filtrar`)

Se descarta:
- una pulsación casi sin voz (`min_voz_s` = 0,15);
- una transcripción con más palabras de las que caben en los segundos con voz;
- las frases típicas de alucinación de Whisper («Gracias por ver el video»…).

## Transcripción

- **Motor:** `motor_transcripcion: whisper`, faster-whisper `large-v3-turbo` `int8_float16` en la GPU
  (`transcripcion.TranscriptorWhisper`). `whisper_pausa: base`: en modo juego, «estoy jugando» o «ya terminé» se
  reconocen con un Whisper base en la CPU.
- **Audio nativo de Gemma:** `transcripcion.py` incluye una alternativa con el audio nativo del mmproj (segundo
  contexto sobre los mismos pesos). Hoy no es el motor activo según `config.json`.

## Salida

- Se lee con Piper (`voz.piper_voz`, una voz ONNX en `modelos/piper/`), y solo la respuesta final. El pensamiento,
  los pasos y las confirmaciones nunca se leen.
- En modo voz, el prompt pide 1 o 2 frases (`agente_minimo.MODO_VOZ`).

## Confirmaciones en voz

`ejecutar_voz()` pide confirmación para todo lo que no está en `SOLO_LECTURA` ([[permisos-y-bloqueos]]).

Formas de confirmar:
- Enter/Esc físicos;
- los botones de la isla;
- «confirmo la instrucción» en una grabación aparte (`confirmacion_voz.py`). Un «sí» solo no vale.

## Registro

Cada comando deja un WAV y una línea en `voz_registro/registro.jsonl` con la transcripción, los frenos y las
latencias. La carpeta es personal y no va a Git: no la leas.

## Control

- Ctrl+Alt+Shift+Q detiene la tarea y lo que se está diciendo; «reanudar» sigue.
- «salir» termina.
- `voz.py --medir N` mide la latencia (carga modelos: solo con la GPU libre).

## Experimental (no está en producción)

Qwen3-TTS 0.6B con vLLM-Omni en WSL ([[qwen3-tts-vllm-omni]], [[wsl-dominio-cuda]]).
