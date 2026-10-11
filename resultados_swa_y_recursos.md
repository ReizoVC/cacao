# Gemma Q5/Q4 con swa_full=False y recursos del conjunto completo en WSL

Informe redactado el 2026-10-10 solo a partir de datos ya guardados. Para escribirlo no se cargó ni se ejecutó ningún modelo, no se usó la GPU y no se repitió ninguna prueba. Tampoco se modificaron config.json, .venv ni producción.

Fuentes (locales, excluidas de Git):

- `comparacion_modelos/datos/ronda3/gemma_q5_swa_false.json`, `gemma_q5_swa_false_nuevas30.json`, `gemma_q4_swa_false.json` y `gemma_q4_swa_false_nuevas30.json`, generados el 10-oct entre las 20:00 y las 21:02.
- Referencia con swa_full por defecto: `datos/ronda3/gemma_q5.json` y `gemma_q4.json`, generados el 8 y 9 de octubre.
- WSL: `.comparacion-runtime/full-wsl/benchmark.json`, `windows_ram_samples.json` y los registros de servidor `gemma-q4-vision-wsl/server.stderr.log` y `vllm-omni-full-wsl/server.std{out,err}.log`.

Datos que faltan:

- Ninguna de las cuatro rondas swa_full=False tiene registro `.log` de consola. Todo lo que hay por caso está en los JSON.
- La salida de consola de la prueba WSL tampoco se guardó: falta lo que imprimían `GEMMA_VISION_READY`, `TTS_READY` y nvidia-smi entre servicios.

## 1. Gemma Q5 y Q4 con swa_full=False

Condiciones comunes a las seis rondas:

- llama-cpp-python 0.3.36, n_ctx 16384, flash-attn y K/V q8_0, sin mmap.
- El mismo prompt (`0cd889b4581f…`) y el mismo esquema (`c2ea19a80dd5…`).
- Herramientas simuladas.

Todas las rondas tienen `complete: true` y el conjunto de casos (id, semilla) está completo.

### 65 frases × 3 semillas (195 casos)

| | Q5 defecto | **Q5 swa=False** | Q4 defecto | **Q4 swa=False** |
|---|---:|---:|---:|---:|
| Completas (criterio oficial ronda 3, `complete_round2`) | 195/195 | **195/195** | 195/195 | **195/195** |
| Completas (comprobación estricta del ejecutor, `task_checked`) | 194 | **194** | 187 | **191** |
| Primera acción literal | 192 | 192 | 193 | 194 |
| JSON válido | 195 | 195 | 195 | 195 |
| Respuestas vacías (tareas / conversación) | 0 / 0 | **0 / 0** | 0 / 0 | **0 / 0** |
| Confirmaciones falsas finales | 0 | 0 | 0 | 0 |
| Acciones distintas a lo pedido | 2 | 2 | 3 | 5 |
| Correcciones internas de la protección | 1 | 0 | 1 | 2 |
| Primera acción mediana / p95 | 3,50 / 4,23 s | **3,32 / 4,07 s** | 3,42 / 4,29 s | **3,19 / 3,66 s** |
| Media por tarea (máx.) | 6,12 s (20,1) | 5,76 s (15,2) | 5,87 s (27,5) | 5,40 s (18,6) |
| tok/s | 35,0 | **37,5** | 38,0 | **42,1** |
| Pico de VRAM total (nvidia-smi) | 12 756 MiB | **10 052 MiB** | 12 065 MiB | **9 553 MiB** |
| Pico menos la base de la GPU antes de cargar | 11 710 MiB | **9 249 MiB** | 10 626 MiB | **8 387 MiB** |
| VRAM libre mínima | 3 295 MiB | 5 999 MiB | 3 986 MiB | 6 498 MiB |
| Carga del modelo | 11,3 s | 11,8 s | 11,4 s | 74,6 s |

### 30 frases nuevas × 3 semillas (90 casos)

Las frases están en `pruebas_nuevas_30.json` y usan las semillas 44, 55 y 66.

| | **Q5 swa=False** | **Q4 swa=False** |
|---|---:|---:|
| Completas (`task_checked` del ejecutor) | 90/90 | 90/90 |
| Primera acción literal | 87 | 87 |
| JSON válido / vacías (tareas / conversación) | 90 / 0 / 0 | 90 / 0 / 0 |
| Confirmaciones falsas finales (detector) | 0 | 2 (ver abajo) |
| Acciones distintas a lo pedido | 2 | 2 |
| Correcciones internas de la protección | 5 | 9 |
| Primera acción mediana / p95 | 3,38 / 4,33 s | 3,23 / 3,96 s |
| Media por tarea (máx.) | 6,33 s (19,5) | 5,91 s (15,0) |
| tok/s | 36,2 | 40,5 |
| Pico de VRAM total / menos la base | 10 893 / 9 976 MiB | 9 389 / 8 154 MiB |

Límites de estos datos:

- `criterios.py` solo define comprobaciones de argumentos y efectos para los id 1–65. Las 30 nuevas (id 101–130) se puntúan únicamente con el `task_checked` del ejecutor, que exige:
  - primer paso válido;
  - herramientas requeridas presentes;
  - JSON válido;
  - respuesta no vacía;
  - ningún efecto fallido.

  No comprueba valores, por ejemplo que el volumen quede en 45 %.
- No existe una ronda de las 30 nuevas con swa_full por defecto, así que en este conjunto no hay comparación con la configuración anterior.

### Comparación con swa_full por defecto

- **Completitud:** sin cambios con el criterio oficial (195/195 en las cuatro rondas). Con la comprobación estricta, Q5 se queda en 194 y Q4 pasa de 187 a 191.
- **VRAM:** el pico baja 2 704 MiB en Q5 y 2 512 MiB en Q4. Restando la base de la GPU, que varió entre rondas, baja 2 461 MiB en Q5 y 2 239 MiB en Q4.
- **Latencia y rendimiento:** la primera acción baja en mediana y en p95, y los tok/s suben (+2,5 en Q5 y +4,1 en Q4). Las rondas no se ejecutaron simultáneamente ni con la misma VRAM de base, así que estas diferencias pequeñas no se atribuyen solo a swa_full.
- **Carga de Q4 (74,6 s frente a 11,4 s):** en esta ronda `ejecutar.py` leyó el GGUF desde `D:\Cacao\ModelosComparacion\`; antes se leía desde `C:\asistente\modelos\comparacion\`. Ambos archivos miden 7 366 423 360 bytes, pero no se compararon sus hashes. La diferencia corresponde a otra ruta de lectura; no se mide aquí el efecto de swa_full sobre la carga.
- **Conversación:** con swa_full=False, 19 de las 20 respuestas cambiaron de texto respecto a la ronda por defecto (Q4 #10 quedó igual). Las respuestas de las rondas `_swa_false` y `_swa_false_nuevas30` son idénticas entre sí.

### Q4 swa_full=False: cada tarea con fallo o marca, y su causa

**65 frases.** Con el criterio oficial no falla ninguna. El `task_checked` estricto marca 4 casos y la auditoría marca 7 en total:

| Caso | Marca | Causa |
|---|---|---|
| #16 s11, s22, s33 «abre el navegador» | `task_checked` = falso | Llamó `abrir_app("navegador")`. El ejecutor lo rechazó por genérico y el modelo preguntó cuál abrir. El criterio oficial lo acepta porque es un caso ambiguo, pero el efecto fallido cuenta en la comprobación estricta. Q4 por defecto hizo lo mismo en las tres semillas. |
| #56 s22 «haz clic en la X…» | `task_checked` = falso; distinta: teclado | `listar_controles(id_ventana=0)` falló porque esa ventana no existe. El modelo se recuperó, usó Alt+F4 (teclado) y cerrar_app, y la ventana quedó cerrada. |
| #56 s11, s33 | distinta: teclado | Después del clic añadió Alt+F4 y cerrar_app, que no se pidieron. |
| #49 s11, s22 «busca en internet el clima…» | distinta: enfocar_ventana | Tras buscar_web, enfocó el navegador para «ver» el resultado. En s22 terminó diciendo que no pudo verlo. |
| #56 s11, #49 s33 | 1 corrección interna cada uno | La protección rechazó una afirmación sin evidencia. El usuario no la recibió. |

**30 frases nuevas.** No falla ninguna en `task_checked`. Marcas de auditoría:

| Caso | Marca | Causa |
|---|---|---|
| #124 s44 «pulsa el botón de cerrar…» | confirmación falsa (detector: «cerrar») | El texto dice «No he podido verificar que se haya cerrado». La negación «no he podido» no está en `_NEGATED_CLAIM`, así que es un falso positivo del detector. |
| #123 s66 «desplaza hacia abajo…» | confirmación falsa (detector: mover_archivo) | El texto dice «no puedo verificar … se haya movido». Es el mismo falso positivo: «movido» coincide con `movid[oa]`. |
| #124 s55 | distinta: cerrar_app y teclado | Se pidió pulsar el botón; además usó Alt+F4 y cerrar_app. Para el #56 equivalente, la lista de excepciones del protocolo permite cerrar_app, pero no la extiende al id 124. |
| #124 s66 | distinta: teclado | Usó Alt+F4 y terminó diciendo que no pudo cerrar la ventana. |
| #108 s44, s55, s66 «comprueba si está instalada la grabadora de sonido» | 3 correcciones internas | La respuesta correcta («la Grabadora de sonido está instalada») coincide con el patrón de volumen `sonido … está`. La protección la rechazó y la respuesta final resultó confusa («no he realizado ningún cambio en el volumen»). Es un falso positivo de la protección. |
| #123 y #124, las tres semillas | 6 correcciones internas | El primer `finalizar` afirmaba «He desplazado el contenido…» o «He cerrado la ventana…» antes de que el efecto estuviera verificado. La protección lo rechazó, y en estos casos acertó. |

Q5 muestra el mismo patrón en #123 y #124: 5 correcciones y 2 acciones distintas. Además, en la pregunta de conversación 6 la protección rechazó su primera respuesta porque contenía la palabra «escrita», que coincide con el patrón de teclado. Ese detalle está en la clave del archivo a ciegas para no revelar las letras.

## 2. Conversación a ciegas

- [resultados_ciegas_q4.md](resultados_ciegas_q4.md): 10 preguntas con 2 respuestas cada una (Q5 y Q4, swa_full=False, semilla 2026), sin editar. A y B se sortearon de nuevo en cada pregunta.
- Clave en un archivo aparte: `clave_resultados_ciegas_q4.md`. Ábrela solo después de evaluar.

Ninguno de los dos archivos está incluido en el commit. La puntuación humana sigue pendiente.

## 3. Recursos del conjunto completo en WSL

Configuración de la prueba (`run_full_wsl.sh` + `benchmark_full_wsl.py`, 10-oct, de 21:03 a 21:11):

- **Gemma Q4 con visión:** llama-server b11429 de Linux, ctx 16384, K/V q8_0. No se pasa `--swa-full`.
- **Qwen3-TTS 0.6B:** vLLM-Omni con el perfil `qwen3_tts_lean.yaml`.
- **Whisper large-v3-turbo:** int8_float16.
- **Ciclos:** tres, con visión, TTS, transcripción y texto. Las cuatro comprobaciones salieron correctas en los tres.

### Memoria

| Medida | Valor | Fuente |
|---|---:|---|
| RAM de Windows en uso antes de que subiera WSL (primera muestra, 21:03:42) | 11,08 GiB de 15,93 | windows_ram_samples.json |
| **Pico de RAM de Windows en uso, incluida WSL** | **15,92 GiB de 15,93 (0,007 GiB disponibles)**, a las 21:10:02 | windows_ram_samples.json (1 821 muestras cada ~0,25 s) |
| RAM de WSL al quedar listos los tres servicios | 6,17 GiB usados de 7,72; 1,55 GiB disponibles | benchmark.json |
| **Swap de WSL en uso** en ese momento | **1,15 GiB** | benchmark.json |
| RAM disponible que informa vLLM al cargar las etapas del TTS | 4,13 GiB en la etapa 0 y 1,65 GiB en la etapa 1 | registro de vLLM |
| VRAM antes de Whisper → después de Whisper → pico conjunto | 13 010 → 14 118 → 14 740 MiB (1 571 MiB libres en el pico) | benchmark.json |

El swap de WSL solo se midió una vez, al quedar listos los servicios. No hay serie temporal ni pico de swap, y tampoco se registró el tamaño total del swap. El pico de RAM de Windows coincide con la carga de Whisper.

### Los 374 s de carga, desglosados por servicio

`three_services_ready_seconds = 374,345` se mide desde `RELOAD_START_EPOCH`, al inicio del script dentro de WSL, hasta que Whisper termina de cargar.

Las horas absolutas se deducen de los registros y de las fechas de los archivos, con una precisión de unos ±1 s:

- El script arrancó hacia las 21:04:00,5, cuando se creó `server.stdout.log` de Gemma.
- Esa hora concuerda con el registro de Gemma, que termina en 420,1 s, y con la fecha de modificación de ese registro (21:11:01,5).

| Tramo | Duración | Fuente |
|---|---:|---|
| Gemma Q4: GGUF desde /mnt/d (registro de 5,6 a 84,1 s) | ≈78,5 s | registro de llama-server |
| Gemma: mmproj e inicialización hasta empezar a escuchar | hasta 86,4 s | registro de llama-server |
| TTS: arranque del proceso hasta su primera línea de registro (21:05:27 → 21:06:36), sin detalle en el registro | ≈69 s | horas de los registros |
| TTS etapa 0: carga del modelo (de ella, 38,66 s de pesos desde 9P) | 47,0 s | registro de vLLM |
| TTS etapa 0: init del motor (perfilado, KV y calentamiento) | 24,5 s | registro de vLLM |
| TTS: entre la etapa 0 activa (21:08:16) y el inicio de la etapa 1 (21:08:41) | ≈25 s | horas de los registros |
| TTS etapa 1: carga del modelo (de ella, 40,57 s de pesos desde 9P) | 44,8 s | registro de vLLM |
| TTS etapa 1: init del motor | 5,9 s | registro de vLLM |
| TTS: orquestador listo a las 21:09:42 y API a las 21:09:46 | — | registro de vLLM |
| **TTS en total**, del lanzamiento (≈86 s) a la API lista (≈345,5 s) | **≈259 s** | deducido |
| Whisper: arranque de Python e imports, entre ≈345,5 y ≈358,7 s | ≈13 s | deducido (374,3 − 15,7) |
| Whisper: `WhisperModel(...)` | 15,7 s | benchmark.json |

Fuera de los 374 s quedan otros tiempos medidos:

- Antes de `RELOAD_START_EPOCH` pasaron unos 19 s desde la primera muestra de PowerShell (21:03:41,5) hasta el arranque del script (≈21:04:00,5). Corresponden al inicio de `wsl.exe` y de la máquina virtual.
- La primera síntesis de TTS tardó 20,97 s hasta el primer audio. Las siguientes tardaron de 0,54 a 0,71 s.

### ¿Se leyeron los modelos desde /mnt/d?

**Sí.** Ningún modelo se leyó desde el sistema de archivos nativo de WSL:

| Archivo | Ruta | Sistema de archivos |
|---|---|---|
| GGUF de Gemma Q4 | `/mnt/d/Cacao/ModelosComparacion/gemma-4-12b-it-UD-Q4_K_XL.gguf` | D: |
| Binario de llama-server | `/mnt/d/cacao-pruebas/llama.cpp-b11429-linux/` | D: |
| TTS: pesos, audio de referencia y configuración | `/mnt/d/cacao voz/qwen-diseno/…` | D:; vLLM informa «Filesystem type for checkpoints: 9P» y desactiva la precarga |
| mmproj | `/mnt/c/asistente/modelos/mmproj/mmproj-F16.gguf` | C: (/mnt/c, también 9P) |
| Whisper | `/mnt/c/Users/reizo/.cache/huggingface/…` | C: (/mnt/c, también 9P) |

Solo los entornos de Python (`/opt/vllm-omni-test` y `/opt/whisper-test`) están dentro de WSL.

Este informe no estima cuánto bajaría la carga si los modelos estuvieran en otro disco.

Otra observación del registro de Gemma: la visión limitó `image_max_tokens` de 1120 a 512, porque `n_ubatch` es 512.

## 4. ¿Ya están estas correcciones en producción?

| Corrección | En producción | Evidencia |
|---|---|---|
| JSON sin caracteres de control (U+0000–U+001F) en la gramática | **No** | La regla `char` de `.venv/…/llama_cpp/llama_grammar.py` (0.3.36) sigue siendo `[^"\\] \| …`, que permite caracteres de control. Ningún módulo de producción modifica `PRIMITIVE_RULES`; solo lo hace `comparacion_modelos/integracion.py`, en memoria y dentro del banco de pruebas. |
| Salida UTF-8 | **Sí, al arrancar desde el acceso directo** | `Cacao.lnk` ejecuta `pythonw iniciar_cacao.py`, y `iniciar_cacao.py:70` lanza `voz.py` con `PYTHONIOENCODING=utf-8` (commit 99fd1bc, 2026-10-07). Si se ejecuta `voz.py` o `agente_minimo.py` directamente desde una consola, no hay reconfiguración de stdout/stderr. |
| Cierre rápido con `mensaje_final` | **Sigue activo, sin el cambio que se probó** | `ESQUEMA_ACCION` acepta `mensaje_final` en cualquier acción (`agente_minimo.py:433`). El bucle termina la tarea con él si la acción quedó verificada y no hay imagen (`agente_minimo.py:817-827`). Las rondas 2 y 3 lo desactivaron: excluyeron `mensaje_final` y exigieron siempre `finalizar` mediante `oneOf`. Ese contrato no está en producción. |

En consecuencia, los resultados de este informe valen para la integración de prueba, no para el agente de producción tal como está hoy.

## Recomendación

1. **Adoptar swa_full=False para Gemma.** Libera unos 2,2–2,7 GiB de VRAM, sin perder tareas con el criterio oficial ni respuestas vacías, y con una latencia igual o algo mejor. Requiere cambiar config.json y modelo.py; no se hizo aquí.
2. **No cambiar todavía de Q5 a Q4.** Q4 es más rápido (42 frente a 37,5 tok/s; p95 de 3,66 frente a 4,07 s) y usa unos 500 MiB menos de VRAM. A cambio, acumula más marcas de auditoría: 5 acciones distintas frente a 2 en las 65 frases, y 9 correcciones frente a 5 en las 30 nuevas. Falta la evaluación a ciegas de la conversación.
3. **Antes de pasar a producción:**
   - portar la regla JSON sin caracteres de control;
   - decidir si se adopta el contrato sin cierre rápido;
   - corregir los falsos positivos de la protección: «escrita», «sonido … está» y las negaciones con «no he podido» o «no puedo».
4. **El conjunto completo en WSL funciona, pero sin margen de RAM.** Windows llegó al 99,96 % de uso, WSL usó 1,15 GiB de swap y la carga de 374 s la domina el TTS (≈259 s), que lee desde /mnt/d por 9P.
