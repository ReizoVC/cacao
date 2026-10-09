# Comparación aislada de Cacao

Resultados: `../resultados_comparacion_modelos.md`. Respuestas humanas en
`../respuestas_comparacion_ciegas.md`; clave en `../clave_comparacion_modelos.md`.
La puntuación humana queda pendiente. No abrir la clave antes de puntuar.

## Motor llama.cpp independiente

El motor moderno de pruebas está fijado en llama.cpp `b11429` (`0.6.0-dev`,
CUDA 13.4) y vive en `.comparacion-runtime/llama.cpp-b11429`. No reemplaza
`llama-cpp-python 0.3.36` en `.venv` ni en `.venv-pruebas`.

```powershell
.\comparacion_modelos\actualizar_motor_llama_cpp.ps1
.\comparacion_modelos\iniciar_motor_llama_cpp.ps1 -Modelo gemma_q4 -Vision
.\.venv-pruebas\Scripts\python.exe -B .\comparacion_modelos\probar_motor_llama_cpp.py --vision
.\comparacion_modelos\detener_motor_llama_cpp.ps1
```

El inicio comprueba que Cacao esté cerrado, espera si la guardia detecta un
juego y exige al menos 12 GiB libres de VRAM. El servidor solo escucha en
`127.0.0.1`, sin interfaz ni herramientas propias. El cliente fuerza
`reasoning_format=deepseek` y `reasoning_budget=0`: con Gemma 4, dejar el
formato en `none` conserva marcadores de canal antes del JSON.

Huellas y resultados de humo: `motor_llama_cpp_b11429.json`. Son pruebas de
compatibilidad; la comparación de 65 frases por tres semillas sigue siendo una
ronda separada.

## Preparación utilizada

Windows, RTX 5060 Ti 16 GB, 16 GB de RAM. Código de Cacao: commit `3e9a735`.
Leer primero la guía, SRS, configuración, herramientas, pruebas y resultados
históricos. Medir el disco antes de descargar; `descargar.ps1` comprueba tamaños,
SHA256 y margen de 4 GiB por archivo. Los cuatro archivos nuevos ocupan 19,55 GiB.
La memoria virtual puede reducir el espacio disponible durante una carga.

Se creó `.venv-pruebas` con el Python de producción usando `-B -m venv`.
Se copiaron **solo** `llama_cpp` y su carpeta de metadatos dist-info desde
`.venv/Lib/site-packages` al nuevo entorno para conservar exactamente el binario
CUDA 0.3.36. No instalar llama-cpp-python desde PyPI encima de esa copia:
podría reemplazar el binario CUDA. Las restantes dependencias se instalaron
en el entorno de pruebas con `pip install --no-cache-dir -r comparacion_modelos/requirements.txt`.
Ver `integridad.json` para las huellas de configuración y archivos del motor.

No modificar `.venv` ni `config.json`. Las configuraciones y copias de código
de cada candidato quedan en `.comparacion-runtime`. Los modelos, entorno,
copias, datos crudos y logs están excluidos de Git.

## Repetir

Cerrar Cacao con permiso del usuario y esperar si hay un juego. Ejecutar un
solo proceso de inferencia a la vez, desde `C:\asistente`:

```powershell
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\continuar.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\vision_normalizada.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\probar_criterios.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\resumir.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\verificar.py
```

`continuar.py` omite tandas marcadas completas; para medir desde cero, conservar
los resultados anteriores en otro directorio antes de ejecutar. No lanzar el
resumen mientras haya tandas activas. La clave existente mantiene las mismas
etiquetas al regenerar los documentos. Para cancelar, crear
`comparacion_modelos/DETENER`; retirarlo antes de reanudar.

El ejecutor verifica la guardia de juegos y se detiene si detecta uno durante
la inferencia. Las herramientas usan fixtures, no controlan Windows ni leen
archivos personales. El catálogo instalado sí se copia de solo lectura: sus
nombres pueden aparecer en los registros crudos locales, por eso se excluyen.

La primera tanda de visión pide píxeles; el seguimiento pide 0–1000. Las dos
capturas limpias son ventanas reales de Calculadora y Bloc de notas vacío.
Los rectángulos se fijaron antes de las inferencias. La ronda 2 documenta y corrige
una errata del rectángulo del número 7 en `ronda2_vision_errata.md`, conservando
las respuestas originales y recalculando ambas referencias.

## Evidencia y límites

`metricas.json`: 780 filas sin respuestas, argumentos ni rutas personales.
`evidencia_vision.json`: puntos, aciertos y latencias de las 40 localizaciones.
`integridad.json`: huellas del motor y la configuración protegida.
Los datos completos quedan en `datos/`, sin commit. `criterios.py` implementa
la comprobación automática y sus límites figuran en el informe; no representa
éxito comprobado sobre Windows real ni calificación humana de conversación.

La VRAM es de toda la GPU y el margen tras cargar voz es estimado. La comparación
usa el protocolo JSON y las plantillas descritas en el informe, no un servidor
independiente con prompts optimizados para cada familia.

## Ronda 2 de integración

Protocolo y umbral predefinidos en `ronda2_protocolo.md`, huellas en
`ronda2_congelado.json`. Ajustes en `integracion.py` aplicados solo por el ejecutor
con `--round2`; no son cambios del agente de producción. La referencia original
se conserva. No ejecutar `resumir.py` después de anexar la ronda 2 sin volver a
ejecutar también `resumir_ronda2.py`, pues el primer resumen solo conoce la ronda 1.

Secuencia (sin otro proceso de inferencia activo):

```powershell
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\diagnosticar.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\ronda2.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\probar_integracion.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\resumir_ronda2.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\verificar.py
```

Datos crudos en `datos/ronda2` (excluidos de Git). El diagnóstico omite tandas
ya completas y la secuencia permite conservar las tandas terminadas al reanudar. Las
respuestas a ciegas de esta ronda mezclan las versiones anteriores y ajustadas;
su clave es independiente de la primera. La aprobación humana sigue pendiente.

## Conversación regenerada antes de la evaluación humana

`conversacion_nueva.py` reutiliza en memoria el ejecutor congelado de la ronda 2:
solo omite el bucle de 195 tareas y ajusta el marcador de finalización a diez
conversaciones y cero tareas. No altera el archivo congelado, la integración,
las preguntas, el contexto, la temperatura ni la semilla 2026. La inferencia se
ejecuta otra vez; no copia respuestas anteriores. Con los mismos parámetros,
algunas respuestas pueden coincidir con las anteriores.

```powershell
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\conversacion_nueva.py gemma_q5 --round2
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\conversacion_nueva.py qwen_q5 --round2
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\resumir_conversacion_nueva.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\verificar.py
```

Ejecutar secuencialmente, sin otro modelo en GPU. Salidas crudas nuevas en
`datos/conversacion_nueva/ronda2`, excluidas de Git; nunca sobrescriben la ronda 2.
`resultados_ciegas.md` mezcla A/B de nuevo en cada pregunta, con clave independiente
en `clave_resultados_ciegas.md`. Una regeneración del documento conserva esa clave.
Para repetir la inferencia después de evaluar, archivar primero esta tanda y su
clave, pues el ejecutor sustituye la salida de su modelo. Los veinte textos se
guardan sin editar; `conversacion_nueva_integridad.json` conserva huellas y fechas
de generación. La revisión semántica de los siete fallos se entrega por separado
en `clasificacion_fallos_qwen.md`, sin cambiar el marcador 188/195.

## Gemma UD-Q4_K_XL con las protecciones de la ronda 3

La comparación directa con Gemma Q5 reutiliza sin cambios el prompt, las 65 frases,
las semillas 11/22/33, el esquema y las protecciones de la ronda 3:

```powershell
.\.venv-pruebas\Scripts\python.exe -B -u comparacion_modelos\ejecutar.py gemma_q4 --round3
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\resumir_gemma_q4_ronda3.py
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\verificar.py
```

La salida cruda queda en `datos/ronda3/gemma_q4.json` y se excluye de Git. Las
métricas sanitizadas y el resumen sí se conservan para auditar el informe.

## Ronda completa con llama-server b11429

Con el servidor aislado ya iniciado para `gemma_q5`, el mismo ejecutor de la
ronda 3 puede usar su API local sin tocar los entornos Python:

```powershell
.\comparacion_modelos\iniciar_motor_llama_cpp.ps1 -Modelo gemma_q5
.\.venv-pruebas\Scripts\python.exe -B -u comparacion_modelos\ejecutar.py gemma_q5 --round3 --server-url http://127.0.0.1:18081
.\comparacion_modelos\detener_motor_llama_cpp.ps1
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\resumir_gemma_q5_llama_b11429.py
```

El adaptador reutiliza la caché del prompt durante los pasos de una misma tarea
y borra el slot antes de la siguiente. Por eso el servidor debe iniciarse con
`--slot-save-path`, como hace el script. La salida cruda queda en
`datos/llama_cpp_b11429/ronda3`; las métricas sanitizadas se guardan en
`metricas_gemma_q5_llama_b11429.json` y
`resumen_gemma_q5_llama_b11429.json`. El resumen también comprueba que las
huellas del prompt y del esquema coincidan con la referencia de
llama-cpp-python 0.3.36.

## Fine-tuning Wrench 9B

Wrench es un LoRA de Qwen 3.5 9B orientado a herramientas. Su GGUF Q4_K_M
queda aislado en `modelos/comparacion` y se obtiene desde una revisión fija:

```powershell
.\comparacion_modelos\descargar_wrench.ps1
.\comparacion_modelos\probar_wrench.ps1
.\.venv-pruebas\Scripts\python.exe -B comparacion_modelos\resumir_wrench_b11429.py
```

`probar_wrench.ps1` conserva el servidor dentro de una sola operación: ejecuta
una prueba corta, continúa con las 195 tareas solo si pasa y siempre detiene el
motor al terminar. Los datos crudos quedan en
`datos/wrench_b11429/ronda3`; las salidas sanitizadas son
`metricas_wrench_b11429.json` y `resumen_wrench_b11429.json`.
