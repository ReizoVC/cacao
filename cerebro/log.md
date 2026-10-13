# Registro del cerebro

Una entrada por tarea, la más reciente al final: fecha, qué cambió y commit.

Entradas anteriores: [[log-2026-10-10]], [[log-2026-10-11-isla]], [[log-2026-10-11-b]], [[log-2026-10-11-c]], [[log-2026-10-11-d]] y [[log-2026-10-11-e]].

## 2026-10-12: Qwen3-TTS 0.6B en Windows nativo (qwen3-tts.cpp)

- Compila con VS 2022 + CUDA 13.4 (exportando símbolos). Fase A con A1_equilibrada: F16 RTF 0,74, primer audio en
  caliente 2,4 s (mediana); Q8_0 RTF 5,09; Q4_K no existe. No pasa: fase B sin correr. Página `qwen3-tts-windows`;
  resumen en `comparacion_modelos/resumen_qwen3_tts_windows.json` (e10b522).

## 2026-10-12: Qwen3-TTS con llama.cpp (KreutzM PR #11), voz por frases y convivencia

- `llama-tts` (llama.cpp 81bc6b8) compila en Windows; 0.6B convertido a Q8_0. RTF 0,31, primer audio en caliente
  0,88 s (mediana). Voz por frases: un hueco de 0,22 s en 16 respuestas. Fase B con `qwen9b` + caché + Whisper +
  visión: pico 13 264 MiB, 3 047 libres; TTS con Qwen cargado RTF 0,33. Q8_0 lento en qwen3-tts.cpp: causa no obvia.
  Página `qwen3-tts-windows` reescrita; resumen en `comparacion_modelos/resumen_qwen3_tts_llama_cpp.json` (e9084f7).

## 2026-10-12: voz Qwen3-TTS integrada con Piper de respaldo (apagada por defecto)

- c0945a6 y 0b9eeed:
  - `tts_qwen.py` y `tts_qwen_motor/` (un servidor por tubería, sin red, con hashes);
  - `voz.tts_motor`, con `piper` por defecto;
  - `probar_tts_qwen.py` 92/92.
- 7b4d784: `probar_palabra_activacion.py` vuelve a 41/41; se había roto en fdf84d1.
- Prueba prolongada (9230d4d): con el binario corregido, 1 051 respuestas en 30 min, sin fallos graves y con la
  memoria estable.
- Página nueva: `voz-qwen3`. Actualizadas `voz`, `qwen3-tts-windows`, `vision-general`, los dos mapas, `suites` e
  `index`.
- a04c212: `config.json` con `voz.tts_motor: qwen3`, con permiso del usuario. Se nota al reiniciar Cacao.

