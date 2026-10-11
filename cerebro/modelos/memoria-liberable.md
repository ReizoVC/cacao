---
estado: verificado
verificado_commit: 829fea9
verificado_fecha: 2026-10-11
fuentes: [comparacion_modelos/medir_memoria.py, comparacion_modelos/datos/memoria/2026-10-11_1135.json, config.json, voz.py, transcripcion.py, cerebro/decisiones/qwen3-tts-vllm-omni.md]
---
# Memoria liberable sin perder calidad (Qwen 9B, 2026-10-11)

Medido con `comparacion_modelos/medir_memoria.py --perfil qwen9b`; datos en
`comparacion_modelos/datos/memoria/2026-10-11_1135.json` (ignorado por Git).

**Cómo se midió.** Un arranque de voz como `voz.preparar()`, con cada variante en su propio proceso. Pasos:
1. cargar el modelo;
2. cargar Whisper large-v3-turbo int8 en la GPU;
3. calentar (prompt de voz, silencio a Whisper, Piper);
4. un pedido simulado («pon el volumen al 30»);
5. una captura **sintética** por la ruta de `ver_pantalla` (presupuesto 560).

Sin micrófono, sin isla, sin la wiki ni `memoria.db`, y con las herramientas simuladas. GPU de 16 311 MiB. Antes de
cargar ya había ≈ 1 250 MiB en uso por el escritorio y otras apps. No se midieron contexto menor, KV a 4 bits ni
Whisper más pequeño ([[no-reducir-whisper-ni-contexto]]).

## Resultados (MiB de toda la GPU, nvidia-smi)

| Variante | Modelo | + Whisper | Calentado | Pico (con visión) | Libre en el pico |
|---|---:|---:|---:|---:|---:|
| base: KV f16, sin flash, `swa_full` por defecto, mmap | 8 305 | 9 318 | 9 538 | 15 342 | 969 |
| + `swa_full=false` | 8 268 | 9 293 | 9 540 | 15 235 | 1 076 |
| + flash attention (KV f16) | 8 169 | 9 209 | 9 392 | 10 647 | 5 664 |
| + flash + KV q8_0 | 7 941 | 8 965 | 9 161 | 10 407 | 5 904 |
| + `use_mmap=false` | 8 269 | 9 304 | 9 548 | 15 254 | 1 057 |
| **todas (= perfil `qwen9b`)** | **7 948** | **9 017** | **9 202** | **10 424** | **5 887** |

Lectura:
- **Flash attention** es casi todo el ahorro: la captura sin flash sube unos 5,7 GiB. Con flash, el pico baja
  ≈ 4,6 GiB.
- **KV q8_0** ahorra ≈ 230 MiB más. Ya estaba activa en los dos perfiles (`type_k`/`type_v` = q8_0).
- **`swa_full=false` no cambia nada en Qwen** (dentro del ruido, < 110 MiB): su arquitectura no usa la ventana
  deslizante de Gemma.
- **`use_mmap=false`** no cambia la VRAM. Baja la RAM del proceso (working set 2,1–2,3 GB frente a 4–7 GB con mmap;
  cifra ruidosa). Ver [[use-mmap-false]].
- **Whisper** ocupa ≈ 1 030 MiB y se carga al arrancar (`voz.preparar` → `TranscriptorWhisper`). No existe la opción
  de cargarlo al primer uso: solo se descarga y se vuelve a cargar en el modo juego.

## ¿Cabe Qwen3-TTS?

El perfil lean de Qwen3-TTS tuvo un pico de 5 250 MiB, medido en WSL con vLLM-Omni ([[qwen3-tts-vllm-omni]]).
- Con Qwen + Whisper en el pico con visión quedan 5 887 MiB libres: **cabría con ≈ 640 MiB de margen**, justo.
- Sin usar la visión quedan ≈ 7 100 MiB (16 311 − 9 202).

El TTS no se ha medido en Windows, ni junto con Cacao.
