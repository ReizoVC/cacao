# Comparación de modelos de Cacao

Fecha: 2026-10-07 (America/Lima). **Mediciones locales nuevas**, herramientas simuladas.

## Resultados

| Candidato | 1.ª literal | 1.ª histórica | Tareas comprobadas | JSON/esquema | 1.ª acción mediana / p95 | Generación tok/s | VRAM pico texto | Libre al pico texto | Visión píxeles / normalizada |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma 4 12B Q5_K_M (referencia) | 193/195 | 195/195 | 190/195 (97.4%) | 195/195 | 3.77 / 4.92 s | 30.2 | 13.41 GiB | 2.26 GiB | 0/5 / 0/5 |
| Gemma 4 12B UD-Q4_K_XL | 193/195 | 195/195 | 186/195 (95.4%) | 195/195 | 3.96 / 5.13 s | 30.2 | 12.86 GiB | 2.82 GiB | 0/5 / 1/5 |
| Qwen 3.5 9B UD-Q4_K_XL | 189/195 | 189/195 | 156/195 (80.0%) | 195/195 | 2.59 / 3.28 s | 48.0 | 8.31 GiB | 7.37 GiB | 1/5 / 4/5 |
| Qwen 3.5 9B UD-Q5_K_XL | 187/195 | 187/195 | 165/195 (84.6%) | 195/195 | 2.49 / 2.93 s | 48.3 | 8.55 GiB | 7.12 GiB | 1/5 / 4/5 |

## VRAM y margen para voz

VRAM de **toda la GPU**, incluidas las aplicaciones de fondo; no equivale a memoria exclusiva del modelo. Muestreo aproximadamente cada 250 ms más el tiempo de nvidia-smi. El pico observado puede omitir transitorios muy cortos. No se cargó un motor de voz en estas tandas. La última columna es una **estimación**, restando una reserva de 1,34 GiB (inspirada en los 1,34 GB publicados para Whisper turbo int8_float16 en `resultados_voz.md`; la unidad histórica no permite más precisión), no una prueba nueva de coexistencia.

| Candidato | Base sin modelo | Cargado texto | Pico con visión | Libre con visión | Libre estimado tras voz |
|---|---:|---:|---:|---:|---:|
| Gemma 4 12B Q5_K_M (referencia) | 1.24 GiB | 12.47 GiB | 13.63 GiB | 2.04 GiB | 0.70 GiB |
| Gemma 4 12B UD-Q4_K_XL | 2.13 GiB | 12.38 GiB | 13.38 GiB | 2.29 GiB | 0.95 GiB |
| Qwen 3.5 9B UD-Q4_K_XL | 2.22 GiB | 8.15 GiB | 9.18 GiB | 6.50 GiB | 5.16 GiB |
| Qwen 3.5 9B UD-Q5_K_XL | 1.12 GiB | 7.66 GiB | 9.99 GiB | 5.68 GiB | 4.34 GiB |

El consumo de fondo varió entre tandas: la diferencia cargado menos base fue Gemma 4 12B Q5_K_M (referencia): 11.23 GiB, Gemma 4 12B UD-Q4_K_XL: 10.25 GiB, Qwen 3.5 9B UD-Q4_K_XL: 5.94 GiB, Qwen 3.5 9B UD-Q5_K_XL: 6.54 GiB. Es una aproximación al incremento, no una medición exclusiva del proceso. Para voz se conserva el menor margen observado en las dos tandas de visión.

## Detalle de errores y estabilidad

Las tres semillas repiten las mismas 65 frases: las 195 observaciones no son tareas independientes. Las diferencias pequeñas, como cuatro tareas entre los Gemma, no prueban superioridad general. No se calcularon intervalos de confianza ni se optimizaron prompts por candidato.

| Candidato | Conversaciones con respuesta final no vacía | Evaluación humana |
|---|---:|---|
| Gemma 4 12B Q5_K_M (referencia) | 10/10 | Pendiente |
| Gemma 4 12B UD-Q4_K_XL | 7/10 | Pendiente |
| Qwen 3.5 9B UD-Q4_K_XL | 2/10 | Pendiente |
| Qwen 3.5 9B UD-Q5_K_XL | 3/10 | Pendiente |

Este recuento solo detecta salidas vacías; no puntúa calidad lingüística. En la pregunta de estudio, los dos Qwen también invocaron `registro_habitos` para pausar sin que se solicitara. La acción fue simulada.

### Gemma 4 12B Q5_K_M (referencia)

Tareas no acreditadas (id: semillas): 16: [11, 22, 33]; 24: [33]; 64: [33].

| Semilla | Primera literal | Tarea comprobada | JSON | Media tarea |
|---|---:|---:|---:|---:|
| 11 | 64/65 | 64/65 | 65/65 | 6.16 s |
| 22 | 65/65 | 64/65 | 65/65 | 5.80 s |
| 33 | 64/65 | 62/65 | 65/65 | 7.11 s |

Visión (coordenadas predichas frente al rectángulo fijado):

- Tarea 1, el botón del número 7: {"x": 315, "y": 786}; fallo; 1.99 s.
- Tarea 2, el botón más (+), para sumar: {"x": 896, "y": 973}; fallo; 1.29 s.
- Tarea 3, el botón igual (=): {"x": 871, "y": 895}; fallo; 1.30 s.
- Tarea 4, el menú Archivo: {"x": 38, "y": 185}; fallo; 1.36 s.
- Tarea 5, el botón + para crear una pestaña nueva: {"x": 312, "y": 89}; fallo; 1.33 s.

Seguimiento con contrato explícito de coordenadas 0–1000 (misma prueba para los cuatro candidatos):

- Tarea 1: {"x": 312, "y": 784}; punto en píxeles {'x': 100.464, 'y': 418.656}; fallo; 1.93 s.
- Tarea 2: {"x": 893, "y": 971}; punto en píxeles {'x': 287.546, 'y': 518.514}; fallo; 1.31 s.
- Tarea 3: {"x": 875, "y": 906}; punto en píxeles {'x': 281.75, 'y': 483.804}; fallo; 1.30 s.
- Tarea 4: {"x": 39, "y": 184}; punto en píxeles {'x': 38.454, 'y': 137.632}; fallo; 1.35 s.
- Tarea 5: {"x": 312, "y": 89}; punto en píxeles {'x': 307.632, 'y': 66.572}; fallo; 1.33 s.

### Gemma 4 12B UD-Q4_K_XL

Tareas no acreditadas (id: semillas): 16: [11, 22, 33]; 24: [11, 33]; 60: [11]; 46: [22]; 59: [22]; 18: [33].

| Semilla | Primera literal | Tarea comprobada | JSON | Media tarea |
|---|---:|---:|---:|---:|
| 11 | 64/65 | 62/65 | 65/65 | 6.58 s |
| 22 | 64/65 | 62/65 | 65/65 | 6.72 s |
| 33 | 65/65 | 62/65 | 65/65 | 6.94 s |

Visión (coordenadas predichas frente al rectángulo fijado):

- Tarea 1, el botón del número 7: {"x": 314, "y": 795}; fallo; 1.89 s.
- Tarea 2, el botón más (+), para sumar: {"x": 849, "y": 961}; fallo; 1.23 s.
- Tarea 3, el botón igual (=): {"x": 875, "y": 946}; fallo; 1.26 s.
- Tarea 4, el menú Archivo: {"x": 38, "y": 185}; fallo; 1.28 s.
- Tarea 5, el botón + para crear una pestaña nueva: {"x": 312, "y": 94}; fallo; 1.24 s.

Seguimiento con contrato explícito de coordenadas 0–1000 (misma prueba para los cuatro candidatos):

- Tarea 1: {"x": 314, "y": 795}; punto en píxeles {'x': 101.108, 'y': 424.53}; fallo; 1.90 s.
- Tarea 2: {"x": 897, "y": 963}; punto en píxeles {'x': 288.834, 'y': 514.242}; fallo; 1.25 s.
- Tarea 3: {"x": 876, "y": 941}; punto en píxeles {'x': 282.072, 'y': 502.494}; acierto; 1.24 s.
- Tarea 4: {"x": 38, "y": 184}; punto en píxeles {'x': 37.468, 'y': 137.632}; fallo; 1.31 s.
- Tarea 5: {"x": 312, "y": 94}; punto en píxeles {'x': 307.632, 'y': 70.312}; fallo; 1.27 s.

### Qwen 3.5 9B UD-Q4_K_XL

Tareas no acreditadas (id: semillas): 29: [11, 22, 33]; 30: [11, 22, 33]; 31: [11, 22, 33]; 34: [11, 22, 33]; 35: [11, 22, 33]; 38: [11, 22, 33]; 39: [11, 22]; 40: [11, 22, 33]; 47: [11, 33]; 50: [11, 22]; 59: [11, 22]; 36: [22, 33]; 37: [22]; 44: [22]; 55: [22]; 58: [22, 33]; 43: [33]; 45: [33]; 56: [33].

| Semilla | Primera literal | Tarea comprobada | JSON | Media tarea |
|---|---:|---:|---:|---:|
| 11 | 63/65 | 54/65 | 65/65 | 5.33 s |
| 22 | 63/65 | 50/65 | 65/65 | 5.74 s |
| 33 | 63/65 | 52/65 | 65/65 | 5.67 s |

Visión (coordenadas predichas frente al rectángulo fijado):

- Tarea 1, el botón del número 7: {"x": 297, "y": 740}; fallo; 5.06 s.
- Tarea 2, el botón más (+), para sumar: {"x": 892, "y": 874}; fallo; 1.35 s.
- Tarea 3, el botón igual (=): {"x": 891, "y": 947}; fallo; 1.34 s.
- Tarea 4, el menú Archivo: {"x": 38, "y": 79}; fallo; 1.38 s.
- Tarea 5, el botón + para crear una pestaña nueva: {"x": 316, "y": 40}; acierto; 1.42 s.

Seguimiento con contrato explícito de coordenadas 0–1000 (misma prueba para los cuatro candidatos):

- Tarea 1: {"x": 314, "y": 752}; punto en píxeles {'x': 101.108, 'y': 401.568}; fallo; 4.57 s.
- Tarea 2: {"x": 893, "y": 874}; punto en píxeles {'x': 287.546, 'y': 466.716}; acierto; 1.38 s.
- Tarea 3: {"x": 891, "y": 947}; punto en píxeles {'x': 286.902, 'y': 505.698}; acierto; 1.37 s.
- Tarea 4: {"x": 36, "y": 81}; punto en píxeles {'x': 35.496, 'y': 60.588}; acierto; 1.41 s.
- Tarea 5: {"x": 314, "y": 40}; punto en píxeles {'x': 309.604, 'y': 29.92}; acierto; 1.42 s.

### Qwen 3.5 9B UD-Q5_K_XL

Tareas no acreditadas (id: semillas): 29: [11, 22, 33]; 30: [11, 22, 33]; 31: [11, 22, 33]; 34: [11, 22, 33]; 38: [11, 22]; 40: [11, 33]; 44: [11, 22]; 58: [11, 22]; 14: [22]; 21: [22]; 27: [22]; 35: [22]; 39: [22]; 50: [22, 33]; 56: [22]; 57: [22]; 59: [33].

| Semilla | Primera literal | Tarea comprobada | JSON | Media tarea |
|---|---:|---:|---:|---:|
| 11 | 61/65 | 57/65 | 65/65 | 4.93 s |
| 22 | 62/65 | 50/65 | 65/65 | 4.67 s |
| 33 | 64/65 | 58/65 | 65/65 | 5.18 s |

Visión (coordenadas predichas frente al rectángulo fijado):

- Tarea 1, el botón del número 7: {"x": 298, "y": 740}; fallo; 5.46 s.
- Tarea 2, el botón más (+), para sumar: {"x": 893, "y": 875}; fallo; 1.46 s.
- Tarea 3, el botón igual (=): {"x": 889, "y": 947}; fallo; 1.40 s.
- Tarea 4, el menú Archivo: {"x": 42, "y": 81}; fallo; 1.42 s.
- Tarea 5, el botón + para crear una pestaña nueva: {"x": 314, "y": 40}; acierto; 1.44 s.

Seguimiento con contrato explícito de coordenadas 0–1000 (misma prueba para los cuatro candidatos):

- Tarea 1: {"x": 296, "y": 738}; punto en píxeles {'x': 95.312, 'y': 394.092}; fallo; 4.96 s.
- Tarea 2: {"x": 894, "y": 876}; punto en píxeles {'x': 287.868, 'y': 467.784}; acierto; 1.44 s.
- Tarea 3: {"x": 890, "y": 947}; punto en píxeles {'x': 286.58, 'y': 505.698}; acierto; 1.44 s.
- Tarea 4: {"x": 38, "y": 81}; punto en píxeles {'x': 37.468, 'y': 60.588}; acierto; 1.45 s.
- Tarea 5: {"x": 317, "y": 40}; punto en píxeles {'x': 312.562, 'y': 29.92}; acierto; 1.49 s.

## Método y límites

- Mismo motor CUDA **llama-cpp-python 0.3.36**, copiado a `.venv-pruebas`; arquitectura `qwen35` cargada y probada. No fue necesaria una versión nueva. DLL y código de producción no modificados.
- Contexto 16.384, todas las capas GPU, flash attention, K/V q8_0, use_mmap=false, temperatura 0,3, top_k=64, top_p=0,95, máximo 512 tokens por acción y 15 pasos por tarea. Semillas 11, 22 y 33.
- Plantilla nativa de cada GGUF. Qwen con `enable_thinking=false` para el protocolo JSON de Cacao; no es una comparación del modo de razonamiento extendido. El prompt de sistema y las herramientas son idénticos.
- Una tarea de calentamiento, fuera del cómputo. Historial y caché KV vacíos antes de cada frase; mide primera acción con prompt frío y kernels calientes. No comparar directamente estas latencias con las tandas históricas que reutilizaban el prefijo.
- Primera acción: tiempo hasta recibir el primer JSON completo (no hasta el primer token). La mediana y p95 incluyen lectura del prompt. Tokens/s: suma de tokens de salida dividida por decode + muestreo; excluye evaluación del prompt y herramientas. Los tokenizadores de las dos familias difieren.
- Primera literal exige que la primera herramienta esté en `esperado`. Primera histórica conserva `primer_paso_ok` de evaluar_pruebas.py (acepta verificaciones previas). Tareas comprobadas añade validación de argumentos/efectos mediante criterios.py; #44 acepta que la terminal ya esté enfocada. Ninguna cifra demuestra éxito en Windows real.
- JSON/esquema valida el sobre de Cacao: `argumentos` admite un objeto vacío. Un `finalizar` con `{}` puede ser JSON válido y producir una respuesta vacía; no se acredita como tarea completa. La comprobación de tareas es automática, con condiciones específicas para volumen, apps, archivos y controles; otros casos conservan evidencia de herramientas más respuesta no vacía, sin evaluar exhaustivamente la verdad del texto. Un error intermedio recuperado no invalida por sí solo el éxito final.
- Herramientas completamente simuladas; validaciones de ventanas reales sustituidas por fixtures. Ventanas restablecidas por caso, fecha fija, wiki vacía fija, sin hábitos, archivos, capturas personales ni memoria de producción. El catálogo local de apps se copia de solo lectura y se mantiene igual para todos.
- Conversación: diez preguntas idénticas, semilla 2026, mismo agente y gramática. Respuestas finales sin editar; evaluación humana pendiente. Etiquetas A–D sorteadas; clave en archivo separado.
- Visión: cinco localizaciones sobre dos capturas reales limpias (Calculadora y Bloc de notas vacío), semilla 11. Sin clics del modelo ni texto UIA suministrado. Acierto si el punto cae en el rectángulo fijado antes de medir. Presupuesto de imagen 1120; cada arquitectura puede tokenizar la imagen de forma distinta. Muestra pequeña.
- La primera tanda pidió píxeles originales. Al observar salidas compatibles con una escala 0–1000, se repitieron las cinco tareas para TODOS los candidatos con ese contrato explícito y conversión a píxeles. Es un seguimiento exploratorio, no reemplaza la tanda inicial ni aplica una corrección retrospectiva a sus respuestas.
- El sistema detiene la inferencia si detecta un juego. No cierra Cacao automáticamente; el usuario lo cerró antes de medir.
- Incidencia de preparación: una carga de Gemma falló al reservar 2720 MiB de caché CUDA; el reintento tras las descargas funcionó. No se contabilizó como tarea. No se determinó la causa exacta.

## Compatibilidad de la gramática

| Candidato | Versión | Respaldos en prueba top_k=1 | Resultado |
|---|---|---:|---|
| Gemma 4 12B Q5_K_M (referencia) | 0.3.36 | 7 | Enum artificial y entero: JSON validado |
| Gemma 4 12B UD-Q4_K_XL | 0.3.36 | 7 | Enum artificial y entero: JSON validado |
| Qwen 3.5 9B UD-Q4_K_XL | 0.3.36 | 8 | Enum artificial y entero: JSON validado |
| Qwen 3.5 9B UD-Q5_K_XL | 0.3.36 | 8 | Enum artificial y entero: JSON validado |

La prueba fuerza el camino de respaldo desde top_k a vocabulario completo; las 195 tareas comprueban además el esquema JSON de Cacao. Esto valida esta instalación, no garantiza compatibilidad con futuras versiones.

## Recomendación

**Mantener Gemma 4 12B Q5_K_M por ahora**, pendiente de tu evaluación a ciegas. Es el candidato con más tareas acreditadas en esta integración. No se cambió el modelo de producción.

Gemma UD-Q4_K_XL reduce el tamaño en disco y algo el pico observado, pero no ganó velocidad de generación y acreditó menos tareas. Con la variación de VRAM de fondo, estas tandas no justifican un cambio por rendimiento.

Qwen genera alrededor de 48 frente a 30 tok/s y reduce la mediana de primera acción a unos 2,5–2,6 s. Deja mucho más margen para voz, pero ambos cuantizados omitieron acciones en pedidos compuestos: por ejemplo, #29 ajusta volumen sin abrir Spotify, y #30 abre Calculadora sin ajustar volumen. Algunas respuestas dicen haber hecho ambas cosas. También hubo respuestas finales vacías aunque el JSON era válido. Son problemas medidos con el protocolo actual de Cacao; no demuestran incapacidad general del modelo.

Si priorizas voz y quieres continuar evaluando Qwen, **UD-Q5_K_XL es el siguiente candidato**: acreditó más tareas que Q4 y conservó amplio margen de VRAM. Antes de adoptarlo habría que validar una integración que exija mensaje final y verifique todos los pasos. La visión normalizada mejoró a 4/5 para ambos Qwen; exige adaptar y verificar ese contrato en Cacao y ampliar las capturas. Ningún cambio de producción forma parte de esta comparación.

## Evaluación a ciegas y archivos

- [Respuestas a ciegas](respuestas_comparacion_ciegas.md): puntuar claridad, corrección, naturalidad y brevedad (1–5), sin abrir la clave.
- [Clave separada](clave_comparacion_modelos.md): abrir después de puntuar.
- [Mediciones por frase sin datos personales](comparacion_modelos/metricas.json). Registros completos locales en `comparacion_modelos/datos/` (excluidos de Git).
- Código reproducible, criterios y capturas: `comparacion_modelos/`. Modelos en `modelos/comparacion/`; entorno en `.venv-pruebas/`; ambos excluidos de Git.

## Procedencia e integridad

- Gemma: [unsloth/gemma-4-12b-it-GGUF](https://huggingface.co/unsloth/gemma-4-12b-it-GGUF/tree/fc034cfff751157913579611efad8462ac1be606).
- Qwen: [unsloth/Qwen3.5-9B-GGUF](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/tree/3885219b6810b007914f3a7950a8d1b469d598a5).
- Tamaños y SHA256 comprobados en descargar.ps1. Tres modelos nuevos + mmproj: 20.994.365.248 bytes (19,55 GiB).
- Espacio antes de descargar: 29.248.856.064 bytes (27,24 GiB). La memoria virtual de Windows redujo el margen durante la carga; no se cambiaron ajustes del sistema.
- SHA256 config.json de producción: `fb10d3ec38a7ae49ce3c51cfeca6740d7cefe19aa5d1ede08eee078fe74c884e`.
- SHA256 prompt común: `0855ade1123729cab1adeb33a1aa1dc90c73ff99db5228f928f68d894a8e8ef4`.
- Commit de código de Cacao evaluado: `3e9a735`.
