# Informe de trabajo y traspaso técnico de Cacao

**Fecha de corte:** 10 de octubre de 2026  
**Repositorio principal:** `C:\asistente`  
**Interfaz de escritorio:** `C:\asistente-ui`  
**Objetivo del documento:** permitir que otro chat o desarrollador continúe el trabajo sin reconstruir decisiones, pruebas y rutas.

## 1. Estado ejecutivo

Cacao continúa en producción con **Gemma 4 12B Q5_K_M** y `llama-cpp-python 0.3.36`. No se cambió `config.json`, no se reemplazó el modelo de producción y no se modificó el entorno `.venv` durante las comparaciones.

Las pruebas determinaron lo siguiente:

- **Gemma Q5** sigue siendo la referencia más conservadora: 195/195 tareas completas.
- **Gemma UD-Q4_K_XL** también consiguió 195/195 y es el candidato preferido para una integración experimental con voz, porque reduce el uso de disco y VRAM.
- **Qwen 3.5 9B Q5** es más rápido, pero obtuvo 189/195 y mantuvo siete acciones distintas de lo pedido. No superó el criterio de seguridad fijado.
- Los ajustes especializados **Wrench 9B** y **UI-Mate 9B** tampoco superaron a Gemma como cerebro general de Cacao.
- El ejecutable moderno de **llama.cpp b11429** redujo mucho la VRAM de Gemma sin perder tareas completas.
- **Qwen3-TTS 0.6B** funciona con baja latencia mediante vLLM-Omni si Gemma, TTS y Whisper comparten WSL.
- La combinación completa probada —Gemma Q4 con visión, Qwen3-TTS y Whisper— llegó a un pico de **14.760 MiB**, dejando **1.551 MiB libres** antes del último ajuste de TTS.
- El perfil TTS ajustado elevó el margen estimado a **1.880 MiB libres**, sin tocar Whisper.

La recomendación vigente es mantener producción intacta mientras se crea un lanzador experimental supervisado en WSL. Ese lanzador debe usar Gemma Q4, el perfil TTS ajustado y el Whisper actual, hacer calentamiento y comprobar la salud de los tres servicios antes de conectar la isla.

## 2. Reglas y alcance respetados

Durante el trabajo se conservaron estas restricciones:

- `C:\asistente\config.json` siguió apuntando al modelo de producción.
- `C:\asistente\.venv` no se usó para instalar motores experimentales.
- Los modelos y entornos de prueba se mantuvieron fuera de Git.
- Las herramientas se simularon durante las evaluaciones de 65 frases; no se ejecutaron acciones peligrosas.
- Las pruebas visuales usaron Calculadora y Bloc de notas de prueba, nunca capturas con contenido personal.
- La decisión de cambiar el modelo de producción quedó siempre en manos del usuario.
- El reconocimiento de voz no se degradó para ahorrar VRAM; la optimización final afectó solamente a Qwen3-TTS.

## 3. Estado de producción

### 3.1 Modelo y motor

| Elemento | Estado actual |
|---|---|
| Modelo | Gemma 4 12B Q5_K_M |
| Archivo | `C:\asistente\modelos\gemma-4-12b-it-Q5_K_M.gguf` |
| Proyector visual | `C:\asistente\modelos\mmproj\mmproj-F16.gguf` |
| Motor | `llama-cpp-python 0.3.36` |
| Contexto | 16.384 tokens |
| Capas en GPU | Todas (`n_gpu_layers: -1`) |
| Flash Attention | Activado |
| Caché K/V | `q8_0` / `q8_0` |
| Temperatura de las comparaciones | 0,3 |
| Mapeo de archivo | `use_mmap: false` |

`use_mmap: false` se conserva porque, una vez transferido el modelo a la GPU, reduce la presión sobre los 16 GB de RAM física. Con el archivo mapeado, el sistema había llegado a mantener alrededor de 8,6 GB en el conjunto de trabajo.

### 3.2 Voz y escucha actuales

| Elemento | Estado actual |
|---|---|
| Reconocimiento | faster-whisper `large-v3-turbo` |
| Tipo de cálculo | `int8_float16` |
| Voz de producción | Piper |
| Archivo Piper | `C:\asistente\modelos\piper\es_MX-claude-high.onnx` |
| Atajo para hablar | `Ctrl+Espacio` |
| Palabra de activación | Activada |
| Seguimiento tras respuesta | Activado, 8 segundos |

Qwen3-TTS sigue siendo experimental. No reemplazó Piper en producción.

### 3.3 Comportamientos relacionados

- La isla usa `C:\asistente-ui\windows\target\release\asistente-ui.exe`.
- El servidor local de la isla escucha en `127.0.0.1:8765` con token de sesión.
- El modo juego descarga Gemma, visión y Whisper cuando detecta un juego activo y los recarga al terminar.
- El modo sin confirmación empieza apagado y solo se activa mediante una acción física en la isla o bandeja.
- El autocompletado de acceso continúa desactivado.

## 4. Mapa de rutas

### 4.1 Repositorio y resultados versionados

| Ruta | Contenido |
|---|---|
| `C:\asistente` | Código principal de Cacao |
| `C:\asistente-ui` | Isla/interfaz de escritorio |
| `C:\asistente\resultados_comparacion_modelos.md` | Informe acumulado de comparación |
| `C:\asistente\resultados_ciegas.md` | Respuestas conversacionales mezcladas para evaluación ciega |
| `C:\asistente\clave_comparacion_modelos.md` | Clave separada de la evaluación ciega |
| `C:\asistente\clasificacion_fallos_qwen.md` | Análisis de los siete fallos residuales de Qwen |
| `C:\asistente\comparacion_modelos` | Scripts, métricas y resúmenes reproducibles |
| `C:\asistente\pruebas.json` | 65 frases reales de evaluación |

### 4.2 Modelos

| Ruta | Uso |
|---|---|
| `C:\asistente\modelos\gemma-4-12b-it-Q5_K_M.gguf` | Modelo actual de producción |
| `C:\asistente\modelos\mmproj\mmproj-F16.gguf` | Visión de producción |
| `D:\Cacao\ModelosComparacion\gemma-4-12b-it-UD-Q4_K_XL.gguf` | Gemma Q4 experimental, 7.366.423.360 bytes |
| `D:\Cacao\ModelosComparacion\Qwen3.5-9B-UD-Q5_K_XL.gguf` | Qwen Q5 experimental, 6.743.680.224 bytes |
| `D:\Cacao\ModelosComparacion\Wrench-9B-Q4_K_M.gguf` | Ajuste Wrench, 5.629.108.640 bytes |
| `D:\Cacao\ModelosComparacion\UI-Mate-9B.Q5_K_M.gguf` | Ajuste UI-Mate, 6.467.970.336 bytes |
| `D:\Cacao\ModelosComparacion\mmproj-F16.gguf` | Proyector Gemma archivado, 918.166.080 bytes |
| `D:\Cacao\ModelosComparacion\UI-Mate-9B.mmproj-f16.gguf` | Proyector UI-Mate, 918.166.016 bytes |

Qwen Q4 fue eliminado por petición del usuario y liberó aproximadamente 5,56 GiB. Los candidatos que no se usan permanecen en D para no presionar el disco del sistema.

### 4.3 Motores y entornos experimentales

| Ruta | Función |
|---|---|
| `C:\asistente\.comparacion-runtime\llama.cpp-b11429` | llama.cpp moderno para Windows; ignorado por Git |
| `D:\cacao-pruebas\llama.cpp-b11429-linux` | llama.cpp b11429 Linux/CUDA |
| `D:\WSL\Ubuntu-24.04` | Distribución WSL movida oficialmente a D |
| `/opt/vllm-omni-test` | vLLM 0.30.0 y vLLM-Omni 0.30.0 para Qwen3-TTS |
| `/opt/whisper-test` | faster-whisper 1.2.1 y bibliotecas CUDA 12 aisladas |
| `D:\cacao voz\qwen-diseno` | Proyecto y recursos de voz |
| `D:\cacao voz\qwen-diseno\models\Qwen3-TTS-12Hz-0.6B-Base` | Modelo TTS usado en pruebas |
| `D:\cacao voz\qwen-diseno\audios\A1_equilibrada.wav` | Referencia de voz A1 |

También existe `Qwen3-TTS-12Hz-1.7B-VoiceDesign`, pero el perfil acreditado para convivencia fue el modelo Base de 0,6B.

### 4.4 Caché de Whisper

Ruta Windows:

`C:\Users\reizo\.cache\huggingface\hub\models--mobiuslabsgmbh--faster-whisper-large-v3-turbo\snapshots\0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`

Ruta equivalente en WSL:

`/mnt/c/Users/reizo/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots/0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`

## 5. Método de comparación

La prueba principal usa las 65 frases de `pruebas.json` con tres semillas: 11, 22 y 33. Esto produce 195 casos por modelo.

Se midió:

1. Acierto de la primera herramienta.
2. Finalización completa de la tarea.
3. JSON válido.
4. Tiempo hasta la primera acción.
5. Velocidad de generación.
6. Pico y margen de VRAM.
7. Respuestas vacías, confirmaciones falsas y acciones distintas de lo pedido.
8. Conversación en español mediante diez preguntas mezcladas a ciegas.
9. Visión con cinco tareas en aplicaciones de prueba cuando el modelo la soportaba.

Las frases originales no se cambiaron para favorecer un modelo. Gemma y Qwen recibieron la misma configuración operativa, con la adaptación mínima de plantilla, modo de pensamiento y formato visual que requiere cada arquitectura.

El criterio final fijado para Qwen fue: al menos 98 % de tareas completas, cero respuestas vacías, cero acciones distintas de lo pedido y cero confirmaciones falsas. Qwen no lo alcanzó.

## 6. Correcciones de integración para Qwen

Los primeros resultados de Qwen estaban contaminados por diferencias de integración. Se corrigieron:

- La plantilla de chat correspondiente a Qwen.
- La desactivación real del modo de pensamiento.
- La convivencia entre salida estructurada y gramática JSON.
- Las instrucciones comunes de planificación y herramientas.
- Las descripciones de herramientas que podían mejorarse sin perjudicar a Gemma.
- El formato de coordenadas visual propio de cada familia.

Desactivar el pensamiento nativo no vuelve al modelo menos capaz en esta tarea. Evita que emita razonamiento libre donde Cacao necesita una acción JSON estricta. El modelo todavía razona internamente mediante la secuencia de herramientas y observaciones; simplemente no expone un bloque de pensamiento incompatible con el ejecutor.

Después de estas correcciones, Qwen dejó de producir respuestas vacías, pero sus errores residuales demostraron que la diferencia no era solo de plantilla.

## 7. Protecciones universales añadidas

Las protecciones se implementaron en producción y en el banco de pruebas.

### 7.1 No afirmar un efecto sin evidencia

Cacao no puede decir que terminó una acción de interfaz si el ejecutor no verificó su efecto. Después de clics, teclas o atajos, debe comprobar mediante controles, ventanas o pantalla. Si intenta confirmar sin evidencia, el ejecutor corrige la respuesta y lo informa.

Archivos principales:

- `C:\asistente\protecciones_ejecucion.py`
- `C:\asistente\agente_minimo.py`
- `C:\asistente\comparacion_modelos\ejecutar.py`

### 7.2 Detención tras dos alternativas fallidas

Si dos caminos diferentes fallan para el mismo objetivo, Cacao se detiene y pregunta al usuario. Ya no continúa improvisando hasta consumir los 15 pasos.

### 7.3 Rechazo de atajos escritos como texto

La herramienta `teclado` rechaza cadenas como `Ctrl+G`, `Alt+F4` o `Ctrl+Shift+S` cuando llegan como texto. Los atajos solo se aceptan mediante la acción estructurada `atajo` y el arreglo de teclas.

Archivo principal:

- `C:\asistente\herramientas_grupo4.py`

Las pruebas puras de estas protecciones finalizaron 25/25. No envían teclas reales ni controlan aplicaciones.

## 8. Resultados de modelos

### 8.1 Ronda comparable con protecciones

| Modelo | Tareas completas | Primera herramienta | JSON válido | Vacías | Confirmación falsa final | Acciones distintas | Mediana primera acción | Tokens/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma 4 12B Q5_K_M | 195/195 | 192/195 | 195/195 | 0 | 0 | 2 | 3,50 s | 35,03 |
| Gemma 4 12B UD-Q4_K_XL | 195/195 | 193/195 | 195/195 | 0 | 0 | 3 | 3,42 s | 38,01 |
| Qwen 3.5 9B UD-Q5_K_XL | 189/195 | 182/195 | 195/195 | 0 | 0 | 7 | 2,40 s | 51,00 |

Gemma Q4 ahorró aproximadamente **0,98 GiB de disco** y **691 MiB de VRAM** frente a Q5 en la ronda equivalente, conservando las 195 tareas completas. Gemma Q5 siguió siendo algo más disciplinado en navegación.

### 8.2 Clasificación de los siete casos residuales de Qwen

- Dos fueron caminos más largos pero funcionales: casos 10/semilla 22 y 56/semilla 22.
- Uno fue una aclaración segura pendiente: caso 13/semilla 11.
- Cuatro fueron fallos operativos: casos 14/semilla 11, 43/semilla 22, 59/semilla 22 y 59/semilla 33.
- El caso 14 añadió acciones no pedidas.
- El caso 59/semilla 22 intentó escribir un atajo como texto y propuso una ruta de PowerShell inventada.
- Todas las herramientas estaban simuladas, por lo que esos intentos no causaron daño real.

El detalle está en `C:\asistente\clasificacion_fallos_qwen.md`.

### 8.3 Ajustes especializados probados

| Modelo | Completas | Primera herramienta | JSON | Confirmación falsa | Acciones distintas | Tokens/s | Pico VRAM | Decisión |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Wrench 9B Q4 | 184/195 | 179/195 | 195/195 | 1 | 9 | 66,90 | 6.177 MiB | Descartado como principal |
| UI-Mate 9B Q5 | 184/195 | 188/195 | 195/195 | 1 | 11 | 58,58 | 7.990 MiB | Solo posible especialista supervisado |

UI-Mate está basado en Qwen3.5-9B y fue afinado para interacción gráfica. En las pruebas nativas de visión obtuvo 2/5 y en conversación llegó a iniciar acciones no solicitadas. Puede investigarse como agente visual separado, nunca como ejecutor general sin supervisión.

### 8.4 Conversación a ciegas

Se regeneraron diez respuestas de conversación para Gemma Q5 y Qwen Q5 con la integración corregida:

- Respuestas mezcladas: `C:\asistente\resultados_ciegas.md`
- Clave: `C:\asistente\clave_comparacion_modelos.md`

Este informe no contiene una evaluación humana final registrada. Otro chat no debe asumir que Qwen igualó a Gemma en español hasta revisar el resultado del usuario.

## 9. llama.cpp moderno

Se creó un motor aislado con **llama.cpp b11429**, commit interno `d81235049...`, CUDA 13.4.

Ruta Windows:

`C:\asistente\.comparacion-runtime\llama.cpp-b11429`

Resultado con Gemma Q5:

| Métrica | llama-cpp-python 0.3.36 | llama.cpp b11429 | Cambio |
|---|---:|---:|---:|
| Tareas completas | 195/195 | 195/195 | Sin pérdida |
| Primera herramienta | 192/195 | 192/195 | Igual |
| Tokens/s | 35,03 | 41,13 | +6,10 |
| Mediana primera acción | 3,50 s | 3,91 s | +0,41 s |
| Pico VRAM | 12.756 MiB | 9.542 MiB | -3.214 MiB |
| VRAM libre mínima | — | 6.509 MiB | Margen útil |

El motor moderno aumenta el rendimiento de generación y reduce notablemente VRAM, aunque en esta medición añadió algo de latencia antes de la primera acción. Producción aún no fue migrada.

El archivo `C:\asistente\comparacion_modelos\motor_llama_cpp_b11429.json` confirma que el ejecutable reconoce las opciones MTP, pero **MTP no fue probado**. No debe afirmarse que funciona en Cacao hasta probar el modelo borrador correcto, compatibilidad y consumo conjunto.

## 10. Gemma Q4, MTP y el modelo 26B

Gemma Q4 es viable como alternativa para liberar margen. Con el motor moderno se observaron aproximadamente:

- 8.482 MiB en texto.
- 8.956 MiB con visión.

MTP puede acelerar la generación especulativa, pero añade otro modelo y consume VRAM. No reduce el tamaño base del modelo y todavía no fue validado en Cacao. Debe probarse después de estabilizar el conjunto Gemma Q4 + visión + TTS + Whisper.

Gemma 4 26B A4B, por ser MoE, podría ejecutarse mediante descarga parcial de expertos a CPU y RAM. No se probó. Con 16 GB de RAM del sistema y la voz simultánea, su margen operativo sería peor y su complejidad no está justificada para las tareas sencillas de Cacao.

## 11. Integración de Qwen3-TTS

### 11.1 Primer intento con PyTorch

Gemma Q4 y Qwen3-TTS pudieron convivir en memoria, con un pico de 11.668 MiB y unos 4.643 MiB libres, pero la voz fue demasiado lenta:

- 23,677 s para generar 6,16 s de audio.
- RTF 3,844.
- La fragmentación manual adelantó el primer audio a 16,687 s, pero aumentó el total a 29,666 s y creó una pausa de unos 9,299 s.

Este camino quedó descartado.

### 11.2 vLLM-Omni con streaming

La solución funcional usa:

- vLLM `0.30.0`
- vLLM-Omni `0.30.0`
- PyTorch `2.13.0+cu132`
- FlashAttention 2
- Muestreador PyTorch mediante `VLLM_USE_FLASHINFER_SAMPLER=0`

Se desactivó el muestreador FlashInfer porque su compilación JIT no encontraba `curand.h`.

Perfil reducido inicial de Cacao, `0.16/0.08`:

- Reposo TTS: 4.956 MiB.
- Pico TTS: 5.250 MiB.
- Primer audio caliente: 0,604 s.
- Tiempo total: 1,433 s para 5,76 s de audio.
- RTF: 0,249.

La primera petición en frío puede tardar entre 9 y 16 segundos por carga y compilación. El supervisor futuro debe hacer calentamiento antes de anunciar que la voz está lista.

### 11.3 Un solo dominio CUDA

Ejecutar Gemma en Windows y TTS en WSL cabía físicamente, pero el endpoint Windows de Gemma dejó de aceptar conexiones después de iniciar CUDA en WSL. Esa combinación no quedó acreditada.

Al mover ambos motores al mismo WSL, el resultado fue estable:

- Gemma: 12/12 respuestas.
- TTS: 6/6 audios.
- Gemma después de usar voz: 5/5.
- Gemma caliente: primer token promedio 0,123 s; total 0,798 s.
- TTS caliente: primer audio 0,553 s; total 1,002 s; RTF 0,238.
- Reposo conjunto: 12.735 MiB.
- Pico conjunto: 13.162 MiB.
- Libre en el pico: 3.149 MiB.

La decisión técnica es conservar un único dominio CUDA en WSL para la integración experimental.

## 12. Prueba completa: modelo, visión, voz y reconocimiento

Se probaron tres ciclos con Gemma Q4, mmproj F16, Qwen3-TTS y faster-whisper:

| Componente | Resultado |
|---|---:|
| Visión en Calculadora de prueba | 3/3 |
| Generación de voz | 3/3 |
| Transcripción | 3/3 |
| Gemma después del ciclo | 3/3 |

Rendimiento:

- Carga de Whisper: 13,987 s.
- Primera transcripción: 5,181 s.
- Transcripción caliente promedio: 0,323 s.
- TTS frío: primer audio 15,715 s; total 16,363 s.
- TTS caliente: primer audio 0,574 s; total 1,103 s.
- Visión: primera respuesta 7,7 s; promedio 3,368 s.
- VRAM antes de Whisper: 13.027 MiB.
- VRAM después de Whisper: 14.152 MiB.
- Pico: 14.760 MiB.
- Libre en el pico: 1.551 MiB.
- VRAM después de descargar: 848 MiB.

La combinación funciona, pero el margen original de 1,5 GiB exige conservar el modo juego, hacer comprobaciones de salud y probar recuperación ante fallos antes de llevarla a producción.

## 13. Optimización de VRAM

### 13.1 Contexto de Gemma

Se midió el consumo normalizado de Gemma Q4 con visión, Flash Attention y KV `q8_0`:

| Contexto | Base | Total | Incremento |
|---|---:|---:|---:|
| 16.384 | 870 MiB | 8.910 MiB | 8.040 MiB |
| 8.192 | 875 MiB | 8.834 MiB | 7.959 MiB |

Reducir el contexto a la mitad ahorró solamente **81 MiB**. La decisión fue mantener 16.384 tokens porque el ahorro no compensa perder la mitad del historial útil.

### 13.2 Qwen3-TTS sin modificar Whisper

Se conservaron `large-v3-turbo` e `int8_float16`. Solo se redujeron las reservas de vLLM-Omni.

| Perfil | Talker | Code2wav | Voz | Transcripción | Primer audio | Total | Pico conjunto | Libre |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Original | 0,16 | 0,08 | Acreditada | Acreditada | 0,574 s | 1,103 s | 14.760 MiB | 1.551 MiB |
| Intermedio | 0,15 | 0,075 | 5/5 | 5/5 | 0,606 s | 0,891 s | 14.511 MiB | 1.800 MiB |
| Ajustado | 0,145 | 0,07 | 5/5 | 5/5 | 0,556 s | 0,842 s | 14.431 MiB | 1.880 MiB |

El perfil ajustado consiguió:

- 214 MiB menos en reposo.
- 329 MiB menos en el pico.
- Similitud mínima de transcripción de 0,97.
- Gemma operativa después de la prueba.
- RTF promedio de 0,244.

El talker dispuso de 2.416 tokens KV para un máximo configurado de 2.048 y concurrencia calculada de 1,18. No se recomienda reducir más antes de una prueba prolongada.

Archivos experimentales ignorados por Git:

- `C:\asistente\.comparacion-runtime\qwen3_tts_cacao.yaml`
- `C:\asistente\.comparacion-runtime\qwen3_tts_balanced.yaml`
- `C:\asistente\.comparacion-runtime\qwen3_tts_lean.yaml`
- `C:\asistente\.comparacion-runtime\start_vllm_omni.sh`
- `C:\asistente\.comparacion-runtime\run_joint_wsl.sh`
- `C:\asistente\.comparacion-runtime\benchmark_conjunto_wsl.py`
- `C:\asistente\.comparacion-runtime\run_full_wsl.sh`
- `C:\asistente\.comparacion-runtime\benchmark_full_wsl.py`
- `C:\asistente\.comparacion-runtime\run_tts_tuning_wsl.sh`
- `C:\asistente\.comparacion-runtime\benchmark_tts_tuning.py`

Muestras de audio del perfil ajustado:

- `C:\asistente\.comparacion-runtime\tts-tuning\lean\voz_1.wav`
- `C:\asistente\.comparacion-runtime\tts-tuning\lean\voz_2.wav`
- `C:\asistente\.comparacion-runtime\tts-tuning\lean\voz_3.wav`
- `C:\asistente\.comparacion-runtime\tts-tuning\lean\voz_4.wav`
- `C:\asistente\.comparacion-runtime\tts-tuning\lean\voz_5.wav`

## 14. Almacenamiento y WSL

Ubuntu 24.04 se trasladó oficialmente de C a:

`D:\WSL\Ubuntu-24.04`

En el momento de la migración, el espacio libre de C subió aproximadamente de 10,28 a 33,27 GiB. Al redactar este informe se observaron:

- C: **31,79 GiB libres**.
- D: **311,77 GiB libres**.

Estos valores cambian con cachés, registros y modelos. La distribución WSL observó aproximadamente 7,7 GiB de RAM y 2 GiB de intercambio; por ello las cargas iniciales pueden ser lentas aunque la inferencia caliente sea rápida.

Mover modelos inactivos a D es correcto porque D es SSD. No se deben mover los archivos que producción espera en C sin cambiar y validar expresamente la configuración.

## 15. Decisiones vigentes

### Mantener

- Gemma Q5 como modelo actual de producción.
- Contexto de 16.384 tokens.
- Caché KV `q8_0` y Flash Attention.
- Whisper `large-v3-turbo int8_float16` sin recortes.
- Modo juego para liberar la GPU.
- Las tres protecciones universales del ejecutor.

### Candidato de integración experimental

- Gemma 4 12B UD-Q4_K_XL.
- llama.cpp b11429 en WSL.
- mmproj F16.
- Qwen3-TTS 0.6B Base con perfil `0.145/0.07`.
- faster-whisper actual en el entorno aislado.

### Descartado como modelo principal

- Qwen 3.5 9B Q5: rápido, pero 189/195 y siete acciones distintas.
- Wrench 9B: mejor velocidad y VRAM, menor fiabilidad.
- UI-Mate 9B: posible especialista visual futuro, insuficiente como agente general.
- Qwen Q4: eliminado para recuperar espacio.

### Pendiente, sin resultado acreditado

- MTP para Gemma Q4.
- Gemma 26B A4B con expertos parcialmente en CPU.
- Migración del motor de producción desde `llama-cpp-python` a `llama.cpp` servidor.
- Sustitución de Piper por Qwen3-TTS.
- Evaluación humana final de las respuestas a ciegas.

## 16. Próximo paso recomendado

Crear un **lanzador de pruebas fuera de producción** que haga esta secuencia:

1. Iniciar WSL y comprobar acceso a la RTX 5060 Ti.
2. Levantar llama.cpp b11429 con Gemma Q4 y mmproj.
3. Levantar vLLM-Omni con Qwen3-TTS 0.6B y perfil `0.145/0.07`.
4. Preparar faster-whisper en `/opt/whisper-test`.
5. Hacer una petición de calentamiento a Gemma, TTS y Whisper.
6. Verificar salud, latencia y VRAM de los tres.
7. Conectar una instancia de prueba de Cacao y la isla, sin tocar `config.json`.
8. Detener todo de forma ordenada y comprobar que la VRAM vuelve cerca de su base.

Después se debe ejecutar una prueba prolongada con conversación real, frases largas, visión, reinicios individuales, suspensión del equipo, pérdida de un endpoint y entrada/salida de modo juego. Solo si se recupera de esas situaciones conviene preparar una migración reversible de producción.

MTP debe evaluarse después. Su prueba debe comparar primer token, tokens/s, pico VRAM, estabilidad y aceptación especulativa con el mismo texto, primero sin voz y después con el conjunto completo.

## 17. Evidencia principal

| Archivo | Contenido |
|---|---|
| `C:\asistente\resultados_comparacion_modelos.md` | Informe humano acumulado |
| `C:\asistente\comparacion_modelos\resumen_ronda3.json` | Gemma Q5 frente a Qwen Q5 con protecciones |
| `C:\asistente\comparacion_modelos\resumen_gemma_q4_ronda3.json` | Ronda completa de Gemma Q4 |
| `C:\asistente\comparacion_modelos\resumen_gemma_q5_llama_b11429.json` | Gemma Q5 con motor moderno |
| `C:\asistente\comparacion_modelos\motor_llama_cpp_b11429.json` | Compatibilidad del motor |
| `C:\asistente\comparacion_modelos\resumen_wrench_b11429.json` | Evaluación de Wrench |
| `C:\asistente\comparacion_modelos\resumen_ui_mate_b11429.json` | Evaluación de UI-Mate |
| `C:\asistente\comparacion_modelos\resumen_convivencia_gemma_q4_qwen3_tts.json` | Primeras pruebas Gemma + TTS |
| `C:\asistente\comparacion_modelos\resumen_convivencia_wsl.json` | Gemma y TTS en un solo WSL |
| `C:\asistente\comparacion_modelos\resumen_convivencia_completa_wsl.json` | Visión + voz + Whisper |
| `C:\asistente\comparacion_modelos\resumen_optimizacion_qwen3_tts.json` | Ajustes de reserva TTS |

Los archivos `metricas_*.json` y registros `.log` de `C:\asistente\comparacion_modelos` contienen el detalle por caso.

## 18. Historial de commits relevantes

| Commit | Cambio |
|---|---|
| `59ba166` | Comparación inicial de modelos, conversación y visión |
| `009756d` | Integración común corregida de Qwen y Gemma |
| `e45d7d7` | Conversación ciega y clasificación de fallos de Qwen |
| `9e2c1f1` | Protecciones del ejecutor y nueva ronda |
| `9e5a4bb` | Gemma Q4 con la ronda protegida |
| `09c69d7` | Motor llama.cpp moderno para pruebas |
| `84fbe0b` | Validación de Gemma Q5 con llama.cpp moderno |
| `5889dda` | Evaluación de Wrench |
| `0c20c03` | Evaluación de UI-Mate |
| `da029a4` | Convivencia inicial Gemma Q4 + Qwen3-TTS |
| `0723ab3` | Optimización inicial de Qwen3-TTS |
| `faab666` | Migración de WSL al disco D |
| `7166ce7` | Prueba de streaming con vLLM-Omni |
| `a937a3a` | Convivencia acreditada de Gemma y TTS en WSL |
| `a3dc19e` | Validación completa de voz, visión y Whisper |
| `dc9e898` | Medición de contexto 16K frente a 8K |
| `b7270b4` | Perfil ajustado de Qwen3-TTS |

## 19. Limitaciones y advertencias para quien continúe

- No interpretar que un modelo “cabe” como prueba de estabilidad. Hay que medir picos durante visión, voz y transcripción simultáneas.
- No sumar consumos aislados como garantía de convivencia; las reservas CUDA y los procesos Windows/WSL interactúan.
- No mezclar motores CUDA entre Windows y WSL para la integración acreditada. El camino estable probado mantiene todos los servicios en WSL.
- No reducir Whisper para ganar memoria sin una solicitud expresa del usuario.
- No reducir el contexto: el ahorro medido fue solo 81 MiB.
- No activar MTP en producción basándose únicamente en que llama.cpp reconoce sus banderas.
- No presentar UI-Mate como reemplazo general; su posible uso es el de especialista visual aislado y supervisado.
- `C:\asistente\comparacion_modelos\verificar.py` tiene hashes congelados de archivos que cambiaron en trabajos posteriores. Actualmente puede fallar esa comprobación aunque las pruebas puras de protecciones sean 25/25 y los resultados JSON sean válidos. Antes de usarlo como puerta automática, hay que revisar y actualizar de forma consciente su línea base.
- Los recursos de `.comparacion-runtime` están ignorados por Git. Una clonación del repositorio no los reconstruye por sí sola.

## 20. Preferencia documental

Por indicación del usuario, cualquier documento futuro debe entregarse en **Markdown (`.md`)**, salvo que solicite explícitamente otro formato.
