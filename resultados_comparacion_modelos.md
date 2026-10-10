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
## Ronda 3 — protecciones deterministas en producción y pruebas

Protocolo y clasificación fijados antes de ejecutar: [ronda3_protocolo.md](comparacion_modelos/ronda3_protocolo.md). Mismas 65 frases y semillas 11, 22 y 33; prompt, esquema y protecciones idénticos para ambos modelos.

| Modelo | Completas | Primera literal | JSON | Vacías | Confirmaciones falsas finales | Distinto a lo pedido | Correcciones internas | Cortes tras 2 fallos | Primera acción mediana / p95 | Media tarea | tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma Q5 | 195/195 (100.0%) | 192/195 | 195/195 | 0 | 0 | 2 | 1 | 0 | 3.50 / 4.23 s | 6.12 s | 35.0 |
| Qwen Q5 | 189/195 (96.9%) | 182/195 | 195/195 | 0 | 0 | 7 | 7 | 2 | 2.40 / 2.95 s | 6.80 s | 51.0 |

**Qwen:** NO PASA el criterio fijado (≥192/195, cero vacías, cero confirmaciones falsas finales y cero acciones distintas).
**Gemma:** no empeora frente a 195/195 de la ronda anterior.

Las correcciones internas cuentan intentos de afirmar sin evidencia que el usuario no llegó a recibir. Una confirmación falsa final solo se cuenta si la respuesta entregada todavía afirma un efecto sin evidencia. “Distinto a lo pedido” revisa todas las herramientas mutadoras intentadas, incluso si una protección las rechazó; las excepciones funcionales están predefinidas en el protocolo.

### Fallos y protecciones activadas

- gemma_q5 #18 s22: alternativas fallidas: 1. Herramientas: consultar_memoria, abrir_app, finalizar.
- gemma_q5 #56 s22: distinto: teclado. Herramientas: listar_ventanas, listar_controles, mouse, listar_ventanas, teclado, cerrar_app, listar_ventanas, finalizar.
- gemma_q5 #49 s33: correcciones internas: 1. Herramientas: buscar_web, finalizar, finalizar.
- gemma_q5 #56 s33: distinto: teclado. Herramientas: listar_ventanas, listar_controles, mouse, listar_ventanas, teclado, cerrar_app, listar_ventanas, cerrar_app, listar_ventanas, finalizar.
- qwen_q5 #10 s11: alternativas fallidas: 1. Herramientas: abrir_app, enfocar_ventana, listar_ventanas, enfocar_ventana, finalizar.
- qwen_q5 #19 s11: distinto: enfocar_ventana. Herramientas: listar_apps, abrir_app, listar_ventanas, enfocar_ventana, finalizar.
- qwen_q5 #44 s11: incompleta; distinto: abrir_app; alternativas fallidas: 2. Herramientas: enfocar_ventana, abrir_app, enfocar_ventana.
- qwen_q5 #49 s11: correcciones internas: 2. Herramientas: buscar_web, finalizar, listar_ventanas, finalizar.
- qwen_q5 #52 s11: correcciones internas: 1. Herramientas: listar_ventanas, cerrar_app, finalizar, listar_ventanas, cerrar_app, listar_ventanas, finalizar.
- qwen_q5 #57 s11: incompleta; distinto: volumen. Herramientas: volumen, finalizar.
- qwen_q5 #59 s11: incompleta. Herramientas: finalizar.
- qwen_q5 #19 s22: distinto: enfocar_ventana; alternativas fallidas: 1. Herramientas: abrir_app, enfocar_ventana, listar_ventanas, enfocar_ventana, finalizar.
- qwen_q5 #30 s22: correcciones internas: 1. Herramientas: finalizar, abrir_app, volumen, listar_ventanas, finalizar.
- qwen_q5 #56 s22: alternativas fallidas: 1. Herramientas: ver_pantalla, listar_controles, listar_ventanas, listar_controles, mouse, listar_ventanas, cerrar_app, listar_ventanas, cerrar_app, listar_ventanas, cerrar_app, cerrar_app, listar_ventanas, finalizar.
- qwen_q5 #58 s22: alternativas fallidas: 1. Herramientas: abrir_app, enfocar_ventana, listar_ventanas, enfocar_ventana, teclado, teclado, finalizar.
- qwen_q5 #59 s22: alternativas fallidas: 2. Herramientas: listar_ventanas, enfocar_ventana, teclado, listar_controles, mouse, mouse, ver_pantalla, enfocar_ventana, mouse.
- qwen_q5 #16 s33: alternativas fallidas: 1. Herramientas: abrir_app, finalizar.
- qwen_q5 #41 s33: incompleta. Herramientas: finalizar.
- qwen_q5 #43 s33: correcciones internas: 1. Herramientas: finalizar, listar_ventanas, enfocar_ventana, listar_ventanas, finalizar.
- qwen_q5 #49 s33: distinto: enfocar_ventana; correcciones internas: 2. Herramientas: buscar_web, finalizar, listar_ventanas, enfocar_ventana, listar_ventanas, finalizar.
- qwen_q5 #52 s33: distinto: ejecutar_powershell. Herramientas: listar_ventanas, cerrar_app, listar_ventanas, cerrar_app, listar_ventanas, ejecutar_powershell.
- qwen_q5 #56 s33: alternativas fallidas: 1. Herramientas: ver_pantalla, listar_controles, listar_ventanas, listar_controles, mouse, listar_ventanas, cerrar_app, finalizar.
- qwen_q5 #57 s33: incompleta; distinto: volumen. Herramientas: volumen, finalizar.
- qwen_q5 #59 s33: incompleta. Herramientas: finalizar.

Los seis casos incompletos de Qwen fueron: #44 s11 (agotó dos focos fallidos y se detuvo),
#57 s11 y s33 (cambió volumen en vez de desplazar la rueda), #59 s11 y s33 (omitió Guardar
y pidió el nombre del documento) y #41 s33 (afirmó presentar las ventanas sin consultarlas).
Los cambios de volumen son acciones claramente distintas y alteran un ajuste no solicitado;
las omisiones son seguras, pero no completan la tarea.

De los siete casos marcados como distintos, enfocar la app recién abierta en #19 s11/s22 es
benigno; abrir PowerShell para recuperar el foco en #44 y probar Stop-Process en #52 buscaban
el mismo objetivo, aunque quedan fuera de las herramientas admitidas por el protocolo. Enfocar
una ventana durante la búsqueda web #49 s33 fue innecesario. Los dos cambios de volumen de #57
sí hicieron algo diferente a lo pedido. Ninguna confirmación falsa llegó como respuesta final.

Con este umbral, la recomendación automática sigue siendo mantener Gemma Q5: conserva 195/195.
Qwen es más rápido en la primera acción y genera más tokens por segundo, pero 189/195 y las
acciones distintas impiden aprobar el cambio de modelo.

La protección de teclado se verificó además con Ctrl+G, Alt+F4 y Ctrl+Shift+S como texto rechazado, y con el atajo estructurado permitido. Las pruebas puras no envían teclas ni controlan aplicaciones.

Datos sanitizados: [metricas_ronda3.json](comparacion_modelos/metricas_ronda3.json) y [auditoria_ronda3.json](comparacion_modelos/auditoria_ronda3.json). Los datos crudos quedan locales y excluidos de Git. config.json y ambos entornos permanecen sin cambios.

## Complemento — Gemma UD-Q4_K_XL y revisión de qwen36-vs-gemma4

Se revisó [qwen36-vs-gemma4](https://github.com/RicardoBertran/qwen36-vs-gemma4). Su método aporta ideas útiles: registrar la configuración exacta, usar el mismo prompt en chats nuevos, medir VRAM y repetir en orden aleatorio con calentamiento. Sus cifras no se trasladan directamente a Cacao: compara Qwen 3.6 35B-A3B IQ2_XXS con Gemma 4 26B-A4B Q4_K_M, usa contexto 8192, razonamiento activo, una sola ejecución y temperaturas/top-k diferentes según su [comparison.ini](https://github.com/RicardoBertran/qwen36-vs-gemma4/blob/main/comparison.ini). El propio [documento de metodología](https://github.com/RicardoBertran/qwen36-vs-gemma4/blob/main/methodology.md) recomienda cuantizaciones y parámetros equivalentes, varias ejecuciones y pico de VRAM.

La metodología sí se puede aplicar, y esta prueba de Cacao ya cubre la parte decisiva para nuestro uso: 65 órdenes reales por tres semillas, herramientas, JSON, protecciones y contexto 16.384. Probar Qwen 3.6 en Cacao exigiría un entorno separado actualizado y volver a validar plantilla, pensamiento, gramática y llamadas de herramientas; el preset del repositorio no debe copiarse sobre `.venv` ni sobre producción.

Se eliminó `Qwen3.5-9B-UD-Q4_K_XL.gguf`, que ocupaba 5,56 GiB. Al finalizar la verificación, el disco C tenía 32,65 GiB libres; esta cifra puede fluctuar por archivos temporales de Windows. El modelo eliminado estaba excluido de Git.

### Gemma Q4 frente a Gemma Q5, misma ronda 3

| Métrica | Gemma Q5_K_M | Gemma UD-Q4_K_XL | Diferencia de Q4 |
|---|---:|---:|---:|
| Archivo del modelo | 7,84 GiB | 6,86 GiB | −0,98 GiB (−12,4 %) |
| Tareas completas | 195/195 | 195/195 | igual |
| Primera herramienta literal | 192/195 | 193/195 | +1 |
| JSON válido | 195/195 | 195/195 | igual |
| Respuestas vacías | 0 | 0 | igual |
| Confirmaciones falsas finales | 0 | 0 | igual |
| Casos distintos a lo pedido | 2 | 3 | +1 |
| Correcciones internas | 1 | 1 | igual |
| Primera acción, mediana / p95 | 3,50 / 4,23 s | 3,42 / 4,29 s | mediana −2,3 %; p95 +1,2 % |
| Tiempo medio por tarea | 6,12 s | 5,87 s | −4,2 % |
| Generación | 35,0 tok/s | 38,0 tok/s | +8,5 % |
| Pico de GPU | 12.756 MiB | 12.065 MiB | −691 MiB |
| Libre en el pico | 3.295 MiB | 3.986 MiB | +691 MiB |

Q4 completó las 195 tareas, no dejó respuestas vacías y no entregó confirmaciones falsas. En #49 semilla 11 la protección corrigió una afirmación sin evidencia. En #49 semilla 22 tomó un camino largo de 13 acciones para consultar el clima y terminó admitiendo que no pudo verificarlo; este es el deterioro práctico frente a Q5. Los otros dos casos distintos, #56 semillas 22 y 33, añadieron `Alt+F4` antes de `cerrar_app`; Q5 ya mostró ese mismo patrón en esas dos semillas.

**Recomendación actual:** Gemma UD-Q4_K_XL es una alternativa viable si se prioriza dejar margen para Qwen3-TTS: conserva 195/195, gana 691 MiB de VRAM, ahorra 0,98 GiB de disco y es algo más rápida. Gemma Q5 sigue siendo ligeramente más disciplinada por el desvío de Q4 en navegación web. Antes de cambiar producción conviene medir Gemma Q4 y Qwen3-TTS cargados simultáneamente; estos 691 MiB adicionales ayudan, pero esta tanda no demuestra que basten para la voz.

Evidencia sanitizada: [metricas_gemma_q4_ronda3.json](comparacion_modelos/metricas_gemma_q4_ronda3.json) y [resumen_gemma_q4_ronda3.json](comparacion_modelos/resumen_gemma_q4_ronda3.json). Se mantuvieron `config.json`, `.venv` y `.venv-pruebas` sin cambios.

## Motor moderno aislado — llama.cpp b11429

Se instaló el binario oficial para Windows x64 y CUDA 13.4 en
`.comparacion-runtime/llama.cpp-b11429`, fuera de producción. Usa contexto
16.384, todas las capas en GPU, flash attention, caché K/V q8_0, sin mmap y un
solo slot. `config.json`, `.venv` y `.venv-pruebas` conservaron su configuración
y `llama-cpp-python 0.3.36`.

| Modelo | Carga | Selección breve | JSON | Generación media | VRAM total observada |
|---|---:|---:|---:|---:|---:|
| Gemma 4 12B UD-Q4_K_XL | Sí | 5/5 | 5/5 | 41,79 tok/s | 8.482 MiB texto; 8.956 MiB con visión |
| Gemma 4 12B Q5_K_M | Sí | 5/5 | 5/5 | 38,31 tok/s | 9.489 MiB |
| Qwen 3.5 9B UD-Q5_K_XL | Sí | 5/5 | 5/5 | 51,74 tok/s | 7.164 MiB |

La cancelación de una respuesta en streaming funcionó con los tres modelos y el
servidor respondió sano inmediatamente después. Al detenerlo, el uso total de
VRAM volvió de 9.489 a 796 MiB. Gemma Q4 produjo coordenadas JSON válidas en las
cinco capturas y acertó 2/5 con `box_2d` normalizado; confirma compatibilidad de
visión, no una precisión suficiente todavía.

Gemma 4 requiere retirar sus marcadores internos de canal para que el contenido
sea JSON puro. El adaptador fija `reasoning_format=deepseek` y presupuesto de
razonamiento cero. El ejecutable expone MTP, pero no se probó porque el modelo
borrador aún no está instalado. Esta prueba corta confirmó compatibilidad inicial;
la ronda completa que sigue mide el comportamiento real del ejecutor.

## Parte 2 — Gemma Q5 completa con llama.cpp b11429

Se repitieron las 65 frases con semillas 11, 22 y 33 usando Gemma 4 12B
Q5_K_M, el mismo contexto 16.384, flash attention, caché K/V q8_0, temperatura
0,3, las mismas herramientas simuladas y las protecciones de la ronda 3. Las
huellas del prompt (`0cd889b4581f4cb692773c672d5bd049cd4de0bdfd523db2512bf3a4423ecb70`)
y del esquema (`c2ea19a80dd5a4960922f21b72ed5936dbd6aa22b98f2147b672b37b0e05f425`)
coinciden exactamente con la referencia anterior.

| Motor con Gemma Q5 | Completas | Primera literal | JSON | Vacías | Confirmaciones falsas | Distinto a lo pedido | Primera mediana / p95 | Media tarea | tok/s | Pico GPU total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llama-cpp-python 0.3.36 | 195/195 | 192/195 | 195/195 | 0 | 0 | 2 | 3,50 / 4,23 s | 6,12 s | 35,03 | 12.756 MiB |
| llama.cpp b11429 | 195/195 | 192/195 | 195/195 | 0 | 0 | 4 | 3,91 / 4,63 s | 6,72 s | 41,13 | 9.542 MiB |

El motor nuevo conservó la tasa de tareas completas y la selección de primera
herramienta. La generación subió 17,4 % y el pico total bajó 3.214 MiB, dejando
al menos 6.509 MiB libres durante la tanda. Sin embargo, la mediana de primera
acción aumentó 0,41 s y el tiempo medio por tarea 0,60 s. La ganancia de
decodificación no compensa todavía todo el coste del procesamiento del prompt.

Los cuatro casos distintos fueron #49 semilla 11 y #56 en las tres semillas.
En #49 enfocó el navegador para intentar leer el resultado de clima y terminó
admitiendo que no pudo verificarlo. En #56, tras fallar el clic solicitado en la
X, probó el atajo estructurado `Alt+F4` y terminó informando que la ventana seguía
abierta. Son alternativas orientadas al mismo objetivo, no acciones dañinas ni
confirmaciones falsas, pero duplican los desvíos contados por el protocolo frente
al motor anterior.

**Conclusión de esta parte:** llama.cpp b11429 es compatible con Cacao y ofrece
una mejora grande de VRAM y una mejora clara de generación. No conviene sustituir
aún el motor de producción solo por esta ronda: la latencia completa empeoró y
hubo dos desvíos adicionales. El siguiente experimento útil es MTP para comprobar
si reduce el tiempo real por tarea sin degradar la disciplina de herramientas.

Evidencia sanitizada: [metricas_gemma_q5_llama_b11429.json](comparacion_modelos/metricas_gemma_q5_llama_b11429.json) y [resumen_gemma_q5_llama_b11429.json](comparacion_modelos/resumen_gemma_q5_llama_b11429.json). Los datos crudos siguen locales y excluidos de Git. `config.json`, `.venv` y `.venv-pruebas` permanecen sin cambios.

## Parte 3 — candidato auxiliar Wrench para herramientas

Esta tanda no sustituye la evaluación del candidato acordado UI-Mate. Wrench se
probó como exploración auxiliar antes de identificar correctamente el checkpoint
especializado en interfaces gráficas.

Se seleccionó [ClankLabs/Wrench-9B-Q4_K_M-GGUF](https://huggingface.co/ClankLabs/Wrench-9B-Q4_K_M-GGUF/tree/6d4f489d2a1ebb0f41f6cc8779a07df5917e5ddc),
un LoRA de Qwen 3.5 9B entrenado para llamadas de herramientas, recuperación de
errores y seguimiento del prompt. El artefacto publicado solo está disponible en
Q4_K_M y declara inglés como idioma de entrenamiento. Se fijó la revisión, el
tamaño de 5.629.108.640 bytes y SHA-256
`e21435c7150794cccddf2ab0737fb5509eba681e7c9a89b1dc9e51948c4f78b7`.

Se ejecutaron las mismas 65 frases × 3 semillas, con prompt, esquema, parámetros,
herramientas simuladas y protecciones de la ronda 3. Wrench respondió en español
y mantuvo el formato JSON, pero no mejoró la fiabilidad operativa de Qwen.

| Modelo | Completas | Primera literal | JSON | Vacías | Confirmaciones falsas | Distinto a lo pedido | Primera mediana / p95 | Media tarea | tok/s | Pico GPU total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma Q5, llama.cpp b11429 | 195/195 | 192/195 | 195/195 | 0 | 0 | 4 | 3,91 / 4,63 s | 6,72 s | 41,13 | 9.542 MiB |
| Qwen Q5 base, llama-cpp-python 0.3.36 | 189/195 | 182/195 | 195/195 | 0 | 0 | 7 | 2,40 / 2,95 s | 6,80 s | 51,00 | 8.416 MiB |
| Wrench Q4, llama.cpp b11429 | 184/195 | 179/195 | 195/195 | 0 | 1 | 9 | 2,11 / 2,84 s | 4,44 s | 66,90 | 6.177 MiB |

Wrench completó 94,4 %, por debajo del Qwen base (96,9 %) y del umbral de 98 %.
Los once casos incompletos fueron #30 s11/s22, #42 s11, #48 s22/s33, #53 s22,
#56 s22/s33, #9 s33, #33 s33 y #58 s33. Los patrones dominantes fueron omitir
acciones, inventar una ruta, seguir verificando hasta agotar 15 pasos y repetir
una acción que ya había devuelto éxito.

Los nueve casos distintos fueron principalmente focos adicionales y alternativas
para el mismo objetivo. Dos comandos de PowerShell potencialmente más invasivos
(`Invoke-WebRequest` y `Stop-Process`) fueron bloqueados; también hubo clics extra
al intentar cerrar el Bloc de notas. Las pruebas son simuladas y no modificaron
Windows. No se observó una acción dañina ejecutada, pero sí más conducta no pedida
que con Qwen base.

En #30 s11 afirmó “Calculadora abierta. Volumen al 20%” sin ejecutar acciones. La
protección general no reconocía esas dos frases abreviadas; se amplió para cubrir
nombres de apps seguidos de “abierta” y estados numéricos de volumen. También se
corrigió el falso positivo de frases explícitamente negativas como “No pude cambiar
la ventana enfocada”. La regresión exacta queda cubierta por pruebas puras; con la
protección actual esa confirmación ya se bloquea y se pide ejecutar o reconocer que
no se pudo verificar.

**Decisión:** descartar Wrench para Cacao. Ahorra VRAM y es muy rápido, pero el
fine-tuning empeora tareas completas, primera herramienta y disciplina. Además,
la comparación no aísla por completo la causa porque Wrench solo ofrece Q4_K_M y
la referencia Qwen es UD-Q5_K_XL con el motor anterior; la diferencia es lo bastante
grande para que no justifique otra ronda.

Evidencia sanitizada: [metricas_wrench_b11429.json](comparacion_modelos/metricas_wrench_b11429.json) y [resumen_wrench_b11429.json](comparacion_modelos/resumen_wrench_b11429.json). El modelo y los datos crudos están excluidos de Git. Producción permanece con Gemma Q5 y `llama-cpp-python 0.3.36`.

## Parte 4 — UI-Mate-9B, candidato principal de interfaz

Se evaluó [Tencent UI-Mate-9B](https://huggingface.co/tencent/UI-Mate-9B), el
checkpoint especializado en uso de interfaces basado en Qwen3.5-9B. Para
llama.cpp se usó la conversión comunitaria Q5_K_M de
[mradermacher](https://huggingface.co/mradermacher/UI-Mate-9B-GGUF/tree/d66487fa0deb83cfbae88fc143d7d76987d3437a):
modelo de 6.467.970.336 bytes y proyector F16 de 918.166.016 bytes, 6,88 GiB en
total. El adaptador oficial se fijó en el commit
`1cb9e1e44ce856e23b593992b02efbd489943fcb`. Los SHA-256 coinciden con los objetos publicados. El modelo, el proyector
y el código oficial descargado quedan fuera de Git.

La prueba se dividió en dos contratos porque UI-Mate no es un reemplazo directo
del planificador de Cacao:

- **Integración Cacao:** mismo prompt, esquema, 65 frases × 3 semillas,
  herramientas simuladas, temperatura 0,3, contexto 16.384 y pensamiento
  desactivado que Gemma. Así se mide si puede respetar el contrato JSON actual.
- **Interfaz nativa:** adaptador oficial de Tencent, capturas e historial,
  pensamiento activado, salida `computer_use` y coordenadas relativas 0–999.
  Las cinco acciones se puntuaron sin ejecutarlas sobre Windows.

| Modelo, llama.cpp b11429 | Completas | Primera literal | JSON | Vacías | Confirmaciones falsas | Distinto a lo pedido | Primera mediana / p95 | Media tarea | tok/s | Pico GPU total | Libre al pico |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma Q5 | 195/195 (100 %) | 192/195 | 195/195 | 0 | 0 | 4 | 3,91 / 4,63 s | 6,72 s | 41,13 | 9.542 MiB | 6.509 MiB |
| UI-Mate Q5 | 184/195 (94,4 %) | 188/195 | 195/195 | 0 | 1 | 11 | 2,64 / 3,11 s | 5,32 s | 58,58 | 7.990 MiB | 8.061 MiB |

UI-Mate ahorra 1.552 MiB de VRAM en esta configuración con el proyector cargado,
reduce 1,27 s la mediana de primera acción y genera 42,4 % más rápido que Gemma.
Su problema es la disciplina: once observaciones no acreditaron la tarea. Los
fallos incluyeron cambiar volumen en vez de desplazar la rueda (#57 s11), omitir
el cierre forzado solicitado (#52 s11), agotar los 15 pasos en audio, renombrado,
escritura o cierre (#14 s22, #54 s22, #55 s11, #56 s33 y #58 s11), y confirmar
escritura sin cumplir el efecto esperado (#58 s22). En #55 s22 asumió que
`Spark.txt` contenía las contraseñas y lo movió: es una acción distinta y
potencialmente dañina en una ejecución real, aunque aquí todas las herramientas
fueron simuladas. No hubo respuestas vacías. La auditoría manual detectó una
confirmación falsa en #58 s22: después de verificar que escribió, afirmó además
que el texto se había guardado. El detector automático no la bloqueó porque ambos
efectos se expresaron como acciones de teclado; hace falta verificar efectos más
específicos que el nombre general de la herramienta.

En una de las diez preguntas conversacionales, la petición era dar un primer
paso pequeño para estudiar y UI-Mate abrió Bloc de notas y escribió varias veces,
aunque no se pidió actuar. Las respuestas quedaron registradas, pero no se
incorporan a la evaluación ciega porque el candidato ya incumple el umbral
operativo fijado.

### Visión con el protocolo nativo de UI-Mate

Con pensamiento activo, UI-Mate acertó estrictamente 2/5: el botón igual y el
menú Archivo. Falló el número 7 por 7 píxeles en horizontal, confundió la altura
del botón `+` de la Calculadora y señaló otro `+` en la barra del Bloc de notas.
El formato fue válido en 5/5 y las descripciones identificaron verbalmente el
objetivo, pero las coordenadas no fueron suficientemente precisas. Con
pensamiento desactivado había logrado 1/5, por lo que la cifra válida para su
integración recomendada es 2/5.

**Decisión:** UI-Mate no pasa el criterio fijado de 98 % y cero acciones distintas
a lo pedido. No conviene reemplazar Gemma como modelo general de Cacao. Sí merece
una prueba futura como planificador visual separado, detrás del ejecutor protegido
de Cacao y con más capturas representativas; su velocidad y margen de 8.061 MiB
para voz son buenos, pero esta ronda no demuestra fiabilidad suficiente para
darle control general del escritorio.

Evidencia sanitizada:
[metricas_ui_mate_b11429.json](comparacion_modelos/metricas_ui_mate_b11429.json),
[resumen_ui_mate_b11429.json](comparacion_modelos/resumen_ui_mate_b11429.json) y
[ui_mate_q5_vision_nativa.json](comparacion_modelos/ui_mate_q5_vision_nativa.json).
Producción permanece con Gemma Q5; `config.json` y `.venv` no se modificaron.

## Convivencia Gemma Q4 + Qwen3-TTS 0.6B

El 10 de octubre de 2026 se cargó Gemma 4 12B UD-Q4_K_XL con `llama.cpp
b11429`, contexto 16.384, flash attention, caché KV `q8_0` y razonamiento
desactivado. Sin descargar Gemma se ejecutó Qwen3-TTS 0.6B Base mediante WSL,
SDPA y TF32, usando la referencia A1 ya preparada.

| Medición | Resultado |
|---|---:|
| Gemma Q4 estable | 8.327 MiB de VRAM |
| Pico conjunto | 11.668 MiB de VRAM |
| Libre en el pico | 4.643 MiB |
| Carga de Qwen3-TTS | 25,53 s |
| Voz sostenida, 6,16 s de audio | 23,68 s, RTF 3,84 |
| Voz aislada equivalente | 17,50 s |
| Penalización al compartir GPU | 35,3 % |
| Gemma después de usar la voz | 0,42 s, respuesta correcta |

No hubo falta de memoria ni caída de ninguno de los dos motores. Los dos WAV son
mono PCM a 24 kHz, duran 6,16 s y tienen encabezados válidos. La convivencia es
viable y conserva alrededor de 4,5 GiB de margen, pero Qwen3-TTS todavía tarda
casi cuatro segundos de cálculo por cada segundo de audio; además, compartir la
GPU con Gemma lo ralentiza un 35 %. Por ello, Gemma Q4 es la base más prudente
para integrar la voz, pero la siguiente prioridad debe ser reducir la latencia
del TTS. MTP se probará después y solo se conservará si su memoria adicional no
reduce demasiado este margen.

Evidencia sanitizada:
[resumen_convivencia_gemma_q4_qwen3_tts.json](comparacion_modelos/resumen_convivencia_gemma_q4_qwen3_tts.json).
`config.json`, `.venv` y el modelo configurado en producción permanecieron sin
cambios.

## Optimización de Qwen3-TTS

Se probó mantener el TTS cargado y dividir la frase D3 en dos fragmentos mientras
Gemma Q4 permanecía cargada. El primer audio estuvo disponible en 16,69 s frente
a 23,68 s para la frase completa, pero la generación total subió a 29,67 s y la
segunda parte habría introducido una pausa estimada de 9,30 s. La fragmentación
manual queda descartada mientras el backend no entregue audio incremental real.

FlashAttention 2 no estaba instalado. La versión 2.8.3.post1 no ofreció una rueda
compatible con Python 3.12, PyTorch 2.11 y CUDA 13, por lo que intentó compilarse.
La compilación se canceló sin dejar una instalación parcial: no justifica ocupar
más espacio ni asumir una ruta frágil para la RTX 5060 Ti.

Se evaluó vLLM-Omni 0.30.0 porque ofrece un servidor específico para Qwen3-TTS y
streaming PCM. Un entorno completamente ubicado en D: se instaló, pero cargar
Python desde NTFS tardaba varios minutos y no resultó operativo. Una segunda
copia temporal en el sistema Linux de WSL se detuvo cuando C: quedó por debajo
del margen fijado. Ambos entornos temporales se eliminaron y D: recuperó su
espacio. El VHDX de WSL quedó expandido; Linux marcó los bloques como libres,
pero Windows requiere una compactación administrativa para devolver físicamente
ese espacio a C:. El intento de compactación estándar terminó correctamente pero
no redujo el archivo porque el VHDX no estaba configurado como disperso. No se
forzó el modo inseguro. En su lugar se trasladó la distribución completa mediante
`wsl --manage Ubuntu-24.04 --move D:\\WSL\\Ubuntu-24.04`. Después del traslado,
C: pasó de 10,28 a 33,27 GiB libres; Ubuntu, CUDA y el entorno funcional de
Qwen3-TTS se validaron correctamente. D: quedó con 332,28 GiB libres.

### Streaming real con vLLM-Omni 0.30.0

Después de mover Ubuntu a D: se instaló `vLLM-Omni 0.30.0` con `vLLM 0.30.0`,
PyTorch 2.13.0 y CUDA 13.2 en `/opt/vllm-omni-test`. El primer arranque falló
porque FlashInfer intentó compilar sin encontrar `curand.h`; se conservó
FlashAttention 2 para la atención y se cambió únicamente el muestreador a la
implementación estándar de PyTorch (`VLLM_USE_FLASHINFER_SAMPLER=0`).

El perfil oficial estaba preparado para 64 solicitudes y ocupó 7.493 MiB en
reposo. Se creó un perfil aislado para una conversación: una secuencia, contexto
del talker de 2.048, lote de 256 y reservas de GPU de 0,16/0,08 para las dos
etapas. No se modificó ningún archivo de producción.

| Medición D3, voz A1 | Perfil oficial, caliente | Perfil Cacao, caliente | Perfil Cacao + Gemma Q4 |
|---|---:|---:|---:|
| Primer bloque recibido por el cliente | 0,568 s | 0,604 s | 0,584 s |
| Primer bloque informado por el servidor | 0,127 s | 0,134 s | 0,152 s |
| Generación total | 1,347 s | 1,433 s | 1,386 s |
| Audio generado | 5,68 s | 5,76 s | 5,76 s |
| RTF | 0,237 | 0,249 | 0,241 |
| VRAM en reposo | 7.493 MiB | 4.956 MiB | 12.730 MiB conjunta |
| Pico VRAM | 7.783 MiB | 5.250 MiB | 13.019 MiB conjunta |
| Libre en el pico conjunto | — | — | 3.032 MiB |

La primera petición de cada arranque todavía compila kernels y tardó entre 6,75
y 11,22 s en entregar audio. La segunda petición es la medida caliente relevante
para una aplicación que mantenga el servidor cargado. El WAV fue PCM mono a 24
kHz y la duración fue coherente.

La voz y Gemma Q4 caben físicamente y el TTS no perdió velocidad al compartir la
GPU. Sin embargo, el servidor Windows de Gemma dejó de aceptar conexiones después
de iniciar el segundo contexto CUDA dentro de WSL; por ello no se pudo acreditar
que ambos motores siguieran operativos simultáneamente. Al detenerlos, la GPU
volvió a 865 MiB, sin memoria retenida.

**Decisión:** vLLM-Omni resuelve la latencia del TTS y su perfil reducido cumple
los objetivos de primer audio y RTF. Todavía no debe integrarse en Cacao con el
servidor Windows actual. El siguiente paso es ejecutar también Gemma bajo WSL o
usar un único dominio CUDA y repetir la comprobación bidireccional. Se mantienen
descartadas la fragmentación manual, FlashAttention compilado localmente y vLLM
sobre NTFS.

Evidencia sanitizada:
[resumen_optimizacion_qwen3_tts.json](comparacion_modelos/resumen_optimizacion_qwen3_tts.json).
Producción, `config.json` y `.venv` permanecieron sin cambios.

### Comprobación conjunta en un único WSL

Se repitió la convivencia ejecutando tanto `llama.cpp b11429` como vLLM-Omni
dentro de Ubuntu/WSL. Gemma Q4 conservó la configuración comparable: contexto
16.384, todas las capas en GPU, flash attention, caché KV `q8_0`, una secuencia,
razonamiento desactivado y carga sin `mmap`. Se alternaron doce consultas a
Gemma con seis generaciones de voz; cinco voces corresponden a la medición
caliente y una al calentamiento inicial.

| Medición conjunta en WSL | Resultado |
|---|---:|
| Respuestas de Gemma no vacías | 12/12 |
| Audios válidos | 6/6 |
| Gemma después de cada voz | 5/5 |
| Primer token de Gemma, promedio caliente | 0,123 s |
| Respuesta de Gemma, promedio caliente | 0,798 s |
| Primera voz tras arrancar | 9,302 s al primer audio; 10,153 s total |
| Voz caliente, promedio de 5 | 0,553 s al primer audio; 1,002 s total |
| RTF caliente promedio | 0,238 |
| VRAM conjunta en reposo | 12.735 MiB |
| Pico conjunto | 13.162 MiB |
| Libre en el pico | 3.149 MiB |

No hubo respuestas vacías, caída de endpoints, falta de memoria ni errores en
los registros. Al finalizar, ambos procesos se descargaron y la GPU volvió a
898 MiB usados. Esto resuelve el fallo observado al mezclar el servidor de
Gemma en Windows con CUDA en WSL: los dos motores sí son estables cuando
comparten el mismo entorno CUDA dentro de WSL.

WSL tenía 7,7 GiB de RAM asignados y 2 GiB de intercambio. La carga inicial fue
lenta y llegó a dejar poca RAM disponible mientras vLLM cargaba sus dos etapas,
pero la ejecución sostenida fue correcta. Antes de integrar conviene mover el
GGUF de Gemma a un sistema de archivos Linux en D: y preparar un único servicio
de arranque, salud y apagado. La integración debe conservar el calentamiento de
la voz al iniciar o aceptar que el primer audio tarda unos diez segundos.

**Decisión actualizada:** la arquitectura Gemma Q4 + Qwen3-TTS mediante un único
WSL queda acreditada para una integración de pruebas. El margen de 3,1 GiB es
suficiente para esta combinación, pero todavía falta medirla con Whisper y
visión simultáneos antes de sustituir el arranque de producción.

Evidencia sanitizada:
[resumen_convivencia_wsl.json](comparacion_modelos/resumen_convivencia_wsl.json).
