---
estado: verificado
verificado_commit: 9230d4d
verificado_fecha: 2026-10-12
fuentes: [comparacion_modelos/resumen_tts_qwen_prolongada.json, tts_qwen.py, tts_qwen_motor/servidor.cpp, tts_qwen_motor/compilar.bat, tts_qwen_motor/hashes.json, voz.py, probar_tts_qwen.py, comparacion_modelos/probar_tts_qwen_prolongada.py]
---
# Voz Qwen3-TTS en producción (con Piper de respaldo)

**Interruptor:** `config.json` → `voz.tts_motor`.
- `"piper"`: el valor por defecto en el código.
- `"qwen3"`: activa `tts_qwen.LocutorQwen`. **Activo desde a04c212** (2026-10-12, permiso del usuario). El motor medido y su elección están en [[qwen3-tts-windows]].

## Piezas

- **Motor** en `modelos/qwen3-tts/`, fuera de Git ([[mapa-datos]]):
  - `bin/tts_qwen_servidor.exe`: se compila desde `tts_qwen_motor/servidor.cpp` con `compilar.bat`, contra
    llama.cpp `81bc6b8`;
  - las DLL de llama/ggml y cuBLAS 13.4;
  - el modelo y el mmproj Q8_0 del 0.6B;
  - `voz/A1_equilibrada.wav`.
- **Hashes:** `tts_qwen_motor/hashes.json` guarda el SHA-256 de los 13 archivos. Se comprueban en cada arranque
  (≈ 1,4 s); si alguno falta o no coincide, habla Piper.
- **Sin red:**
  - el servidor es un proceso hijo por tubería: texto por stdin; por stdout, `A <id> <muestras> <tasa>` y PCM int16;
  - llama.cpp se compila sin curl ni OpenSSL y se lanza con `--offline`;
  - no abre puertos.
  - Su stderr va a `registro_tts_qwen.log`, un bloque por arranque, ignorado por Git.
- **Misma interfaz que `voz.Locutor`** (`hablar`, `callar`, `hablando`, `salida`, `voz`, `tasa`). El audio suena
  en el proceso de Cacao, así que no cambian:
  - `fin_habla` y la isla;
  - la escucha de seguimiento (ignora los primeros 0,4 s);
  - `confirmacion_voz.otro_audio_sonando`, que excluye este proceso.
- `voz_registro` anota qué motor habló en cada respuesta: `voz` = `qwen3`, `piper` o `qwen3+piper`.

## Cuándo carga y cuándo habla Piper

`voz.preparar()` lo inicia en un hilo después del LLM, de Whisper y del calentamiento; mientras carga habla Piper.
Antes de arrancar comprueba, en este orden:
1. los hashes;
2. `guardia_juego.juego_abierto()` (no se relaja: con un juego abierto, Piper);
3. que el perfil esté medido (solo `qwen9b`; **Gemma no cabe**: Piper, sin error);
4. que haya VRAM libre ≥ **5 085 MiB**.

El umbral sale de la fase B ([[qwen3-tts-windows]]): 3 330 de TTS residente, más 1 255 del pico de la visión de
qwen9b, más 500 de margen.

**Supervisión:**
- **Cae, se cuelga, da error o va lento:** pasa una de estas cosas:
  - el servidor termina o devuelve un error;
  - un trozo tarda más de `3 + 0,08 × caracteres` s, más despacio que el propio habla.

  Entonces el resto de esa respuesta lo dice Piper, se anota (`[voz qwen3] fallo`) y el proceso se mata y se
  rearranca en segundo plano, pasando otra vez por la guardia y la VRAM. Máximo **3 rearranques**; después, Piper
  hasta reiniciar Cacao.
- **Generación desbocada:** el servidor corta en `25 + 2` tramas por carácter (`limite_de_tramas`). Esa respuesta
  la dice Piper y el proceso sigue sin rearrancar.
- **Modo juego:** `descargar()`/`cargar()` van en `EXTRAS_MODO_JUEGO`, después de Whisper. La pausa habla con
  Piper en la CPU; al volver, se repiten todas las comprobaciones.

**Texto:**
- Trozos por oraciones. La primera, si pasa de 60 caracteres, también se parte por comas, en trozos de 20 o más.
- Cada trozo se sintetiza mientras suena el anterior.
- `normalizar_texto` pasa números (enteros, miles, decimales, horas) y símbolos (%, °, $, €, &, +) a palabras;
  Piper lo hace con espeak. `limpiar_para_voz` se aplica antes, como con Piper.

## Pruebas

- `probar_tts_qwen.py`: sin GPU, con un servidor falso con el mismo protocolo; cada respaldo de arriba, el modo
  juego, el orden en `voz.py` y 8 mutaciones.
- `comparacion_modelos/probar_tts_qwen_prolongada.py`: el motor real durante 30 min, sin LLM ni altavoz
  (`resumen_tts_qwen_prolongada.json`).

| 30 min, motor real | Corrida 1 (c0945a6) | **Corrida 2 (0b9eeed)** |
|---|---:|---:|
| Respuestas | 942 | **1 051** |
| Fallos graves / rearranques | 11 / 11 | **0 / 0** |
| Desbocadas reintentadas / a Piper | — | 13 / 1 |
| Respuestas con hueco (máx.) | 51 (0,87 s) | 1 (0,17 s) |
| Primer audio: mediana / p95 | 0,84 / 1,42 s | 0,94 / 1,39 s |
| RAM del servidor / VRAM | 2 025 → 2 026 MB; 4 312–4 605 MiB | 2 024 → 2 026 MB; 4 325–4 577 MiB |

En la corrida 1, los tiempos máximos eran generaciones desbocadas y los huecos venían de «Buenos días. Son las…».

**#6 y #9 partidas por comas:** el primer audio baja de 1,9–2,1 s a 0,86–1,61 s. No siempre queda por debajo de
1,2 s: en la corrida 2, lo superan 3 de 10 medidas. Unir la primera oración corta cambia huecos por espera: la plantilla «Buenos
días…» pasa de 1,2 s en 83 de sus 85 respuestas.

Falta la prueba con altavoz real, con el usuario delante.
