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
## Ronda 2 — integración común y formatos de visión

Protocolo fijado antes de las tandas completas: [ronda2_protocolo.md](comparacion_modelos/ronda2_protocolo.md). Producción sigue con Gemma Q5; no se cambió config.json ni .venv. No se descargaron modelos nuevos.

**Aceptación fijada:** Qwen necesita ≥186/195 tareas completas, cero respuestas finales vacías en las 195 tareas y las diez preguntas, y no empeorar el español según tu evaluación a ciegas.

### Comparación automática

| Modelo / ronda | Tareas completas | Primera literal | JSON/esquema | Vacías tareas / conversación | Primera acción mediana / p95 | Media tarea | tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gemma Q5 / anterior recalculada | 190/195 (97.4%) | 193/195 | 195/195 | 5 / 0 | 3.77 / 4.92 s | 6.36 s | 30.2 |
| Gemma Q5 / integración común | 195/195 (100.0%) | 192/195 | 195/195 | 0 / 0 | 3.49 / 4.21 s | 6.63 s | 32.7 |
| Qwen Q5 / anterior recalculada | 167/195 (85.6%) | 187/195 | 195/195 | 12 / 7 | 2.49 / 2.93 s | 4.93 s | 48.3 |
| Qwen Q5 / integración común | 188/195 (96.4%) | 182/195 | 195/195 | 0 / 0 | 2.41 / 3.02 s | 6.90 s | 47.6 |

**Resultado automático de Qwen:** cumple ambos requisitos automáticos; el español sigue pendiente.

La condición de español aún no tiene puntuación humana. No se declara aprobado el criterio completo. Las 195 observaciones son tres repeticiones de las mismas 65 frases, sin prueba adicional de generalización.

Se conserva el evaluador anterior salvo #44: la terminal PowerShell ya enfocada acredita el pedido. La referencia Qwen se recalculó con la misma corrección; las cifras originales permanecen arriba. Los otros requisitos de argumentos y efectos no se relajaron.

Gemma cambió de 190 a 195 tareas completas. No perdió tareas en el total. Las diferencias de latencia se muestran en la tabla; no se presupone que el ajuste sea gratuito.

### Qué se corrigió y qué se verificó

- **Plantilla y pensamiento:** se mantiene la plantilla nativa del GGUF de Qwen con enable_thinking=false. El sufijo renderizado incluye un bloque think ya cerrado antes de generar. La primera ronda ya lo hacía; no se detectó pensamiento activo ni una plantilla equivocada que explique estos fallos. El historial se serializa mediante esa plantilla; no se cambió al protocolo XML de herramientas nativas.
- **Prompt/descripciones comunes:** formato explícito finalizar → argumentos.mensaje, acciones pendientes antes de finalizar, advertencia de que mensaje_final corta TODA la tarea y consejos sin cambios de ajustes. El mismo texto y descripción de finalizar se aplican a ambos modelos.
- **Gramática:** el sobre anterior permitía argumentos vacíos y mensaje_final en finalizar. Ahora oneOf separa finalizar, exige mensaje no vacío y exito, y excluye mensaje_final allí. Las otras acciones también excluyen mensaje_final; siempre se requiere finalizar. Esto añade una llamada en pedidos que antes tenían cierre rápido. No se suministra al modelo la herramienta esperada ni se fuerza una secuencia basada en las respuestas del set.
- **Convertidor JSON:** el piloto V3 encontró JSONDecodeError en Qwen #14 s22: un salto de línea literal en pensamiento. La regla char de llama-cpp-python 0.3.36 excluía comillas y barra, pero permitía controles U+0000–U+001F. Se corrigió esa regla en memoria del proceso para ambos modelos, antes de compilar la gramática. Se mantienen json.loads y validación estrictos; no se arregla ni reemplaza la salida generada para acreditarla. Esta corrección no modifica .venv ni archivos de .venv-pruebas.
- **Entorno:** stdout/stderr UTF-8. Dos fallos anteriores fueron UnicodeEncodeError al imprimir caracteres del pensamiento, no errores de JSON ni ausencia de capacidad. El diagnóstico base con UTF-8 permite comprobar esa recuperación sin cambiar prompt/esquema.
- **Capacidad real:** no se puede demostrar una limitación intrínseca a partir de estas tareas. Los errores que persistan se registran como residuales bajo esta integración; no se atribuyen automáticamente a tamaño del modelo. Todas las herramientas siguen siendo simuladas.

### Diagnóstico factorial exploratorio de Qwen

Doce observaciones originales representativas, mismas frases y semillas; registro UTF-8 en todas. Base, prompt y esquema corresponden al piloto previo a las dos aclaraciones de apertura y rueda; combined corresponde al contrato final con esas aclaraciones y la regla de controles JSON corregida. No es un factorial perfectamente aislado de esos cambios; se conserva el diagnóstico anterior en los registros. No es una segunda puntuación de aceptación. Las causas por familia son hipótesis apoyadas por salida y código; una mejora agregada no prueba la causa de cada observación individual.

| Ajuste | Tareas completas / 12 | Respuestas vacías |
|---|---:|---:|
| baseline | 3/12 | 4 |
| prompt | 8/12 | 0 |
| schema | 9/12 | 0 |
| combined | 10/12 | 0 |

El piloto inicial conservaba el cierre rápido: prompt y esquema combinados acreditaron 9/12 pero todavía omitieron acciones en #29 y #30. Se detuvo una tanda parcial de Gemma y se archivó sin puntuarla. Antes de las tandas definitivas se fijó retirar mensaje_final para ambos modelos. Los pilotos completos y la tanda parcial se conservan en datos/piloto_ronda2_v1, fuera de Git.

El siguiente contrato, sin cierre rápido, obtuvo 188/195 en Gemma frente a 190/195 de referencia. Se rechazó ese ajuste común y no se declara como resultado final. Antes de repetir ambos modelos se aclararon apertura directa y signo de la rueda usando el contrato de Windows existente. Datos conservados en datos/piloto_ronda2_v2. El set y el umbral no se modificaron; estas iteraciones usan el mismo set conocido y pueden sobreajustarlo, por lo que falta validación fuera de él.

El piloto V3 acreditó 195/195 en Gemma y fue detenido durante Qwen tras detectar el salto de línea JSON sin escapar. Se conservó íntegro en datos/piloto_ronda2_v3. No se acredita como tanda final ni se combina con observaciones de otras versiones: ambos modelos se repitieron desde cero con la corrección común del convertidor y nuevas huellas congeladas.

Límite de las simulaciones: las listas de controles y las ventanas son fixtures; no actualizan contenido escrito ni desaparición de una ventana tras cerrarla. La puntuación comprueba argumentos y resultados de herramientas, no una interfaz que evolucione con todas las acciones. Un modelo que insiste en verificar puede encontrar esa falta de cambios. No se atribuye a capacidad real del modelo sin repetir en una simulación con estado completo o en apps de prueba reales.

### Auditoría de cada fallo original de Qwen Q5

| ID | Semilla | Clasificación | Evidencia del fallo original | Ronda 2 |
|---|---:|---|---|---|
| 29 | 11 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 30 | 11 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 31 | 11 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 34 | 11 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 38 | 11 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 40 | 11 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 44 | 11 | Evaluador | PowerShell ya estaba enfocado; el criterio anterior dependía de la palabra terminal. | Completa |
| 58 | 11 | Prompt / planificación residual | Abrió otra instancia o no enfocó el Bloc existente; no completó la escritura en la ventana solicitada. | Completa |
| 14 | 22 | Entorno del ejecutor | Impresión CP1252 abortó al encontrar caracteres no representables; no es fallo de capacidad. | Completa |
| 21 | 22 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 27 | 22 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 29 | 22 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 30 | 22 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 31 | 22 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 34 | 22 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 35 | 22 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 38 | 22 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 39 | 22 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 44 | 22 | Evaluador | PowerShell ya estaba enfocado; el criterio anterior dependía de la palabra terminal. | Completa |
| 50 | 22 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 56 | 22 | Prompt / elección de herramienta residual | Cerró la app mediante cerrar_app en vez de ejecutar el clic solicitado. | Falla |
| 57 | 22 | Prompt / interpretación residual | Confundió bajar la rueda del mouse con bajar el volumen. | Completa |
| 58 | 22 | Prompt / planificación residual | Abrió otra instancia o no enfocó el Bloc existente; no completó la escritura en la ventana solicitada. | Completa |
| 29 | 33 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 30 | 33 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 31 | 33 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 34 | 33 | Prompt + cierre anticipado | mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron. | Completa |
| 40 | 33 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 50 | 33 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Completa |
| 59 | 33 | Entorno del ejecutor | Impresión CP1252 abortó al encontrar caracteres no representables; no es fallo de capacidad. | Falla |

Se añaden entorno y evaluador como categorías porque forzar esos errores a plantilla, pensamiento, gramática, prompt o capacidad atribuiría una causa incorrecta al modelo.

En las diez preguntas originales, siete respuestas finales de Qwen estaban vacías y en la pregunta de estudio se pausaron hábitos sin autorización (simulada). Las vacías se revisan con el mismo análisis de campos y se incluyen junto con su repetición en la evaluación a ciegas.

| Pregunta de conversación | Clasificación | Evidencia original | Ronda 2 |
|---|---|---|---|
| 2 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Con respuesta |
| 3 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Con respuesta |
| 4 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Con respuesta |
| 5 | Prompt / acción no solicitada | Pausó el registro de hábitos al recibir un pedido de consejo para estudiar. | Con respuesta |
| 6 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Con respuesta |
| 7 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Con respuesta |
| 8 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Con respuesta |
| 10 | Prompt + gramática permisiva | El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado. | Con respuesta |

### Fallos nuevos y regresiones por frase

- Gemma Q5: fallos ninguno; nuevas regresiones ninguna.
- Qwen Q5: fallos #13 s11, #14 s11, #10 s22, #43 s22, #56 s22, #59 s22, #59 s33; nuevas regresiones #13 s11, #14 s11, #10 s22, #43 s22, #59 s22.

| Fallo nuevo de Qwen | Herramientas ejecutadas | Clasificación residual |
|---|---|---|
| #13 s11 | finalizar | Interpretación: pidió aclarar una frase ambigua; el criterio congelado exige bajar volumen. No prueba incapacidad. |
| #14 s11 | volumen, volumen, consultar_memoria, listar_ventanas, abrir_app, listar_controles, listar_ventanas, listar_apps, abrir_app, listar_controles, listar_ventanas, ejecutar_powershell, abrir_app, consultar_memoria, abrir_app | Planificación/diagnóstico excesivo: no finalizó satisfactoriamente; las ventanas estáticas pueden alimentar el bucle. |
| #10 s22 | listar_ventanas, enfocar_ventana, finalizar | Contrato del benchmark: enfocó una ventana existente en vez de abrir_app. No acredita la apertura requerida, aunque reutilizar una ventana puede ser útil en uso real. |
| #43 s22 | finalizar | Omisión operativa residual: afirmó traer Bloc de notas al frente sin ejecutar ninguna acción. No hay fallo de plantilla, pensamiento o JSON en esta observación. |
| #56 s22 | ver_pantalla, listar_ventanas, cerrar_app, finalizar | Elección de herramienta: cerró la app, pero omitió el clic solicitado en X; no acredita el método pedido. |
| #59 s22 | listar_ventanas, enfocar_ventana, teclado, listar_controles, teclado, listar_controles, mouse, listar_controles, teclado, listar_controles, teclado, ejecutar_powershell, teclado, mouse, teclado | Planificación/verificación: escritura o cierre de tarea no acreditados; los controles estáticos no reflejan el texto escrito. |
| #59 s33 | finalizar | Rechazo operativo residual: dijo que no podía guardar archivos y omitió Ctrl+S pese a disponer de teclado. No ejecutó una verificación. |

### Visión con el formato de cada familia

Gemma: box_2d [y_min,x_min,y_max,x_max], 0–1000, según [Google](https://ai.google.dev/gemma/docs/capabilities/vision/image). Qwen: point_2d [x,y], 0–1000, según el [cookbook Qwen3-VL](https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/spatial_understanding.ipynb). Este último es una referencia de su antecesor: no se encontró recomendación específica para Qwen3.5. El centro se convierte a píxeles ANTES de evaluar con los rectángulos verificados (errata del 7 descrita abajo). Mismas cinco tareas, capturas, presupuesto 1120 y semilla 11. No se hicieron clics.

| Modelo | Formato | Aciertos | Pico VRAM texto / visión | Libre al pico texto / visión |
|---|---|---:|---:|---:|
| Gemma Q5 | box_2d Y/X | 0/5 | 12.45 / 12.93 GiB | 3.23 / 2.74 GiB |
| Qwen Q5 | point_2d X/Y | 5/5 | 7.84 / 9.08 GiB | 7.83 / 6.59 GiB |

- Gemma Q5, tarea 1: `{"box_2d": [719, 208, 836, 405]}` → {'x': 98.693, 'y': 415.185}; fallo (2.21 s).
- Gemma Q5, tarea 2: `{"box_2d": [879, 786, 1000, 975]}` → {'x': 283.521, 'y': 501.693}; fallo (1.60 s).
- Gemma Q5, tarea 3: `{"box_2d": [813, 790, 965, 984]}` → {'x': 285.614, 'y': 474.726}; fallo (1.58 s).
- Gemma Q5, tarea 4: `{"box_2d": [156, 14, 217, 68]}` → {'x': 40.426, 'y': 139.502}; fallo (1.59 s).
- Gemma Q5, tarea 5: `{"box_2d": [56, 301, 124, 328]}` → {'x': 310.097, 'y': 67.32}; fallo (1.57 s).
- Qwen Q5, tarea 1: `{"point_2d": [305, 741]}` → {'x': 98.21, 'y': 395.694}; acierto (4.69 s).
- Qwen Q5, tarea 2: `{"point_2d": [891, 875]}` → {'x': 286.902, 'y': 467.25}; acierto (1.44 s).
- Qwen Q5, tarea 3: `{"point_2d": [890, 947]}` → {'x': 286.58, 'y': 505.698}; acierto (1.43 s).
- Qwen Q5, tarea 4: `{"point_2d": [39, 81]}` → {'x': 38.454, 'y': 60.588}; acierto (1.44 s).
- Qwen Q5, tarea 5: `{"point_2d": [315, 40]}` → {'x': 310.59, 'y': 29.92}; acierto (1.46 s).

**Errata de la primera ronda:** el rectángulo del número 7 señalaba la tecla vecina xʸ. Se revisó directamente la captura y se corrigió antes de esta nueva tanda. Los objetivos y las respuestas no cambian. Se conserva arriba la puntuación publicada; este recálculo reemplaza su interpretación para visión. Detalle en [ronda2_vision_errata.md](comparacion_modelos/ronda2_vision_errata.md).

| Referencia anterior | Píxeles recalculada | Normalizada recalculada |
|---|---:|---:|
| gemma_q5 | 0/5 | 0/5 |
| gemma_q4 | 0/5 | 1/5 |
| qwen_q4 | 1/5 | 5/5 |
| qwen_q5 | 1/5 | 5/5 |

La VRAM incluye otras aplicaciones; no mide memoria exclusiva ni coexistencia con Qwen3-TTS. No se cambió el contexto para ganar espacio. En Gemma, el centro del número 7 quedó solo 0,185 píxeles fuera del rectángulo verificado: cuenta como fallo bajo el criterio congelado. Cinco capturas no bastan para inferir capacidad visual general.

### Evaluación humana pendiente y decisión

[Respuestas nuevas y anteriores mezcladas a ciegas](respuestas_integracion_ciegas.md), [clave separada](clave_integracion_modelos.md). Hay cuatro etiquetas constantes por pregunta (Gemma y Qwen, antes y después), sorteadas sin revelar la correspondencia. Puntuar claridad, corrección, naturalidad y brevedad de 1 a 5. Las respuestas se guardan sin editar.

Qwen cumple la parte automática; **queda pendiente tu español a ciegas antes de recomendar un cambio**.

Esta ronda actualiza la recomendación histórica de arriba. Gemma conserva mayor fiabilidad de tareas en este set. Qwen ofrece menor espera inicial, más tokens por segundo, mejor localización medida y mucho más margen para voz. Su media de tiempo por tarea fue ligeramente mayor por los pasos y bucles, así que más tok/s no significa que termine todos los pedidos antes. No se valida aquí Qwen3-TTS simultáneo ni se migra la producción.

### Integridad y reproducción

- Prompt común SHA256: `adb0e35e13d3348e2c164cc0d83f1032b19574febe51effbc84fa2d47eb2f56e`.
- Esquema común SHA256: `c2ea19a80dd5a4960922f21b72ed5936dbd6aa22b98f2147b672b37b0e05f425`.
- Motor CUDA llama-cpp-python 0.3.36 en .venv-pruebas. Se vuelve a probar el respaldo después de top_k=1 en cada tanda; no se instaló otra versión.
- Pruebas originales y criterios congelados: comparacion_modelos/ronda2_congelado.json. No se modificaron las frases ni herramientas.json de producción.
- Secuencia: ejecutar ronda2.py tras los diagnósticos y luego resumir_ronda2.py. Datos crudos locales excluidos; evidencia sanitizada en comparacion_modelos/metricas_ronda2.json y auditoria_qwen_ronda2.json. Configuración y motor verificados con verificar.py.
## Complemento — conversación nueva y revisión semántica

Se ejecutó nuevamente la inferencia de las diez preguntas con cada Q5, usando la misma integración corregida, semilla 2026 y parámetros. Veinte respuestas no vacías, con JSON validado. No se copiaron respuestas anteriores; con la misma semilla pueden coincidir. La puntuación humana sigue pendiente.

[Nueva evaluación a ciegas](resultados_ciegas.md), [clave separada: abrir después](clave_resultados_ciegas.md). A/B se sortean por pregunta; no identifican siempre al mismo modelo.

[Clasificación semántica de los siete fallos de Qwen](clasificacion_fallos_qwen.md): dos alternativas funcionales (#10 s22 y #56 s22), una aclaración segura pendiente (#13 s11) y cuatro fallos operativos (#14 s11, #43 s22, #59 s22 y #59 s33). #14 añadió acciones no pedidas. #59 s22 escribió texto literal e intentó guardar por PowerShell en una ruta inventada: la escritura fue bloqueada. No se ejecutó ninguna acción real. La puntuación congelada permanece 188/195.

Huellas y fechas de estas inferencias: comparacion_modelos/conversacion_nueva_integridad.json. Producción intacta.
