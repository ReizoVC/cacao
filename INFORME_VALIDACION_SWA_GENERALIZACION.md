# Validación de `swa_full=False`, generalización y convivencia completa

**Fecha:** 10 de octubre de 2026  
**Repositorio:** `C:\asistente`  
**Alcance:** inferencia aislada y herramientas simuladas; sin cambios en `config.json` ni `.venv`.

## Resultado principal

`swa_full=False` recupera la mayor parte del ahorro de VRAM de llama.cpp b11429 sin cambiar el motor de producción. Gemma Q5 conserva **195/195** tareas completas y baja de **12.756 a 10.052 MiB**. Gemma Q4 también conserva **195/195** y baja de **12.065 a 9.553 MiB**.

El conjunto nuevo de 30 frases, ejecutado con tres semillas, terminó **90/90** con ambos modelos. Q4 fue ligeramente más rápido y pequeño. Q5 mantuvo una ventaja pequeña en disciplina de primera herramienta en la ronda histórica, aunque ambos empataron en el conjunto nuevo.

La combinación Gemma Q4 + visión + Qwen3-TTS + Whisper volvió a funcionar, pero la RAM es el límite más preocupante: Windows llegó a **15,918 de 15,925 GiB usados** y WSL consumió **1,153 GiB de swap**.

## 1. Verificación del informe anterior

Las cifras se contrastaron directamente con los JSON versionados.

| Afirmación | Fuente | Verificación |
|---|---|---|
| Gemma Q5: 195/195 | `comparacion_modelos/resumen_ronda3.json` | Confirmada |
| Gemma Q4: 195/195 | `comparacion_modelos/resumen_gemma_q4_ronda3.json` | Confirmada |
| llama.cpp b11429: 12.756 → 9.542 MiB | `comparacion_modelos/resumen_gemma_q5_llama_b11429.json` | Confirmada; ahorro de 3.214 MiB |
| Perfil completo original: 14.760 MiB, 1.551 libres | `comparacion_modelos/resumen_convivencia_completa_wsl.json` | Confirmada |
| Perfil TTS ajustado: 14.431 MiB, 1.880 libres | `comparacion_modelos/resumen_optimizacion_qwen3_tts.json` | Confirmada |

Hay una precisión necesaria: **14.431/1.880 MiB** corresponde a la prueba de optimización TTS con el perfil `0.145/0.07`, Whisper y comprobación posterior de Gemma. La anterior secuencia completa que incluyó visión alcanzó **14.760/1.551 MiB**. En la repetición completa de este informe, ya con el perfil ajustado y visión, el pico fue **14.740 MiB** y quedaron **1.571 MiB libres**. Por ello no debe presentarse 14.431 MiB como pico garantizado para una carga visual completa.

## 2. Estado de tres correcciones en producción

### 2.1 Gramática JSON y caracteres de control

**No está aplicada en producción.**

La corrección existe en `comparacion_modelos/integracion.py`, donde la regla `char` excluye U+0000–U+001F y U+007F sin escapar:

```text
[^"\\\x7F\x00-\x1F] | "\\" (["\\/bfnrt] | "u" HEX HEX HEX HEX)
```

`modelo.py` y `muestreo_gramatica.py` de producción no modifican `llama_cpp.llama_grammar.PRIMITIVE_RULES['char']`. Por tanto, `llama-cpp-python 0.3.36` todavía puede admitir un salto de línea literal u otro control dentro de una cadena generada y producir un JSON que `json.loads` rechace.

Esta corrección debería trasladarse a producción con una prueba unitaria, sin relajar `json.loads` ni reparar silenciosamente una salida inválida.

### 2.2 Salida UTF-8

**Sí está aplicada en el arranque normal de producción.**

`iniciar_cacao.py` abre `registro_cacao.log` con UTF-8 y lanza `voz.py` con `PYTHONIOENCODING=utf-8`. Además, las lecturas y escrituras JSON principales especifican `encoding="utf-8"` y `ensure_ascii=False`.

### 2.3 Cierre rápido con `mensaje_final`

**Sí sigue en producción.**

`agente_minimo.py` permite `mensaje_final` en tareas verificables de un paso, especialmente `volumen` y `abrir_app`. Si la herramienta devuelve éxito, se rellenan marcadores como `{volumen_actual}` y la tarea termina sin una segunda inferencia.

En producción no se añadió latencia porque la ruta no fue retirada. Como referencia experimental:

- Ruta rápida histórica para “Sube un poco el volumen”: **1,85 s** de promedio.
- Integración de comparación con `mensaje_final` desactivado y dos llamadas, Q5 con `swa_full=False`: **5,289 s**.
- Diferencia observada: aproximadamente **+3,44 s**.

No es un A/B contemporáneo perfecto porque procede de rondas distintas, pero muestra el orden de magnitud de la segunda llamada. En Q4, la ruta de dos llamadas promedió **4,821 s**.

## 3. llama-cpp-python 0.3.36 con `swa_full=False`

### Protocolo

- Motor: `llama-cpp-python 0.3.36` en `.venv-pruebas`.
- Contexto: 16.384.
- Flash Attention: activado.
- Caché K/V: `q8_0`.
- Temperatura: 0,3.
- Tres semillas: 11, 22 y 33.
- Herramientas: exclusivamente simuladas.
- Integración y criterio funcional: los mismos de la ronda protegida.
- `swa_full=False` se inyectó solo en la copia aislada de `modelo.py` dentro de `.comparacion-runtime`.

### Resultados de las 65 frases

| Modelo | Completas | Primera herramienta | JSON válido | Vacías | Primera acción mediana | Tiempo medio de tarea | Tokens/s | Pico VRAM | Libre mínimo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemma Q5 | **195/195** | 192/195 | 195/195 | 0 | 3,316 s | 5,764 s | 40,45 | **10.052 MiB** | 5.999 MiB |
| Gemma Q4 | **195/195** | 194/195 | 195/195 | 0 | 3,194 s | 5,400 s | 45,50 | **9.553 MiB** | 6.498 MiB |

La columna “completas” usa `comparacion_modelos/criterios.py`, que reconoce como correctas las aclaraciones seguras de solicitudes ambiguas. El marcador genérico interno del ejecutor dio 194/195 para Q5 y 191/195 para Q4 porque contabiliza como fallo cualquier consulta fallida recuperada; no es el criterio funcional congelado usado para los 195/195 anteriores.

### Ahorro frente a la configuración anterior

| Modelo | Pico anterior | `swa_full=False` | Ahorro |
|---|---:|---:|---:|
| Gemma Q5 | 12.756 MiB | 10.052 MiB | **2.704 MiB** |
| Gemma Q4 | 12.065 MiB | 9.553 MiB | **2.512 MiB** |

Para Q5, llama.cpp b11429 había ahorrado 3.214 MiB. `swa_full=False` logra **84,1 %** de ese ahorro y queda a **510 MiB** del pico de b11429, sin cambiar el motor.

Para Q4, el chequeo breve de b11429 en texto registró 8.482 MiB. Frente al pico anterior de 12.065 MiB, `swa_full=False` consigue **70,1 %** del ahorro observado y queda a unos **1.071 MiB** de b11429. La comparación Q4 es menos fuerte porque la cifra de b11429 procede de una compatibilidad breve, no de otra ronda completa de 195 casos.

## 4. Conjunto nuevo de 30 frases

El conjunto se guardó antes de cargar los modelos en:

`C:\asistente\comparacion_modelos\pruebas_nuevas_30.json`

SHA-256 congelado:

`f040cd643b24250358e693efd43a870660814f238f8bee1093ba1afdc358982a`

No tiene frases exactamente iguales a `pruebas.json`. Incluye variaciones nuevas de volumen, apertura y catálogo de apps, ventanas, archivos, web, mouse, teclado, hábitos y conversación. Se ejecutó con semillas 44, 55 y 66: 90 casos por modelo.

| Modelo | Completas | Primera herramienta | JSON válido | Vacías | Primera acción mediana | Tiempo medio | Tokens/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gemma Q5 | **90/90** | 87/90 | 90/90 | 0 | 3,380 s | 6,331 s | 39,45 |
| Gemma Q4 | **90/90** | 87/90 | 90/90 | 0 | 3,230 s | 5,906 s | 44,02 |

Ambos generalizaron bien en este conjunto. Q4 fue 0,15 s más rápido hasta la primera acción y cerca de 12 % más rápido al generar tokens. Esto reduce la preocupación de que su 195/195 anterior dependiera solo de las frases conocidas.

Los picos de esta ronda fueron 10.893 MiB para Q5 y 9.389 MiB para Q4. Para comparar ahorro de motor se usan los picos de la ronda principal de 195, porque el nivel base de GPU no fue idéntico entre lanzamientos.

## 5. Evaluación ciega Q4 frente a Q5

Las diez respuestas de cada modelo se copiaron sin editar desde las rondas `swa_full=False`, semilla 2026, y se mezclaron de forma independiente en cada pregunta.

- Evaluación: `C:\asistente\resultados_ciegas_q4.md`
- Clave separada: `C:\asistente\clave_resultados_ciegas_q4.md`

No se incluye la clave aquí para preservar la evaluación.

Existe una incidencia registrada en la clave: en la pregunta 6, una protección interpretó la palabra “escrita” como posible afirmación de una acción de teclado y desvió la primera respuesta de Q5. Es un falso positivo del detector de confirmaciones, no un fallo inicial de conocimiento. Debe considerarse al puntuar y corregirse después sin alterar las respuestas ya congeladas.

## 6. RAM total y recarga después del modo juego

### Método

Se partió sin los tres servicios cargados. Un monitor de Windows midió la memoria física global, que ya incluye el proceso de WSL; dentro de WSL se registraron `/proc/meminfo`, swap y el tiempo desde el arranque hasta que Gemma Q4 con visión, Qwen3-TTS y Whisper quedaron cargados.

El perfil TTS fue el ajustado `0.145/0.07`. Después se ejecutaron tres ciclos de visión, voz, transcripción y consulta posterior a Gemma.

### Memoria

| Métrica | Resultado |
|---|---:|
| RAM física disponible | 15,925 GiB |
| RAM usada antes de arrancar | 11,078 GiB |
| Pico total Windows, incluido WSL | **15,918 GiB** |
| RAM física libre mínima | **0,007 GiB** |
| Memoria asignada a WSL | 7,720 GiB |
| Memoria usada dentro de WSL con los tres servicios | 6,168 GiB |
| Disponible dentro de WSL | 1,552 GiB |
| Swap usado por WSL | **1,153 GiB** |

Windows estuvo prácticamente sin RAM física libre. Aunque el sistema terminó la prueba, este margen puede producir paginación, pausas o inestabilidad al sumar navegador, isla y aplicaciones reales.

### Tiempo de recarga

| Hito | Tiempo desde servicios descargados |
|---|---:|
| Gemma + TTS + Whisper cargados | **374,345 s** (6 min 14 s) |
| Whisper dentro de esa secuencia | 15,683 s de carga |
| Con calentamiento de Whisper y TTS | **≈402 s** (6 min 42 s) |

Este tiempo es una recarga fría equivalente a volver del modo juego con los tres servicios. Gran parte corresponde al inicio de WSL, lectura del modelo Q4 desde D y arranque/JIT de vLLM-Omni. No es aceptable como experiencia inmediata después de jugar; se necesita un supervisor que muestre estado de carga y permita que la isla siga respondiendo mientras los motores se preparan.

### Repetición funcional completa

| Componente | Resultado |
|---|---:|
| Visión | 3/3 |
| TTS | 3/3 |
| Whisper | 3/3 |
| Gemma después de cada ciclo | 3/3 |
| Primer audio TTS caliente | 0,599 s |
| TTS total caliente | 1,122 s |
| Whisper caliente | 0,308 s |
| Visión promedio | 2,616 s |
| Pico VRAM | 14.740 MiB |
| VRAM libre en el pico | 1.571 MiB |

Después de cerrar la prueba, la GPU volvió a 1.077 MiB usados, confirmando que los servicios experimentales se descargaron.

## 7. Origen de `A1_equilibrada.wav`

No es la voz identificable de una actriz, actor o persona grabada. Fue **generada sintéticamente** con:

- Modelo: `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`.
- Semilla: `4101`.
- Candidato: `A1`, dirección “Equilibrada”.
- Duración: 15,36 s.
- Descripción: voz adulta joven, suavemente andrógina, cálida, de tono medio a ligeramente alto, español latinoamericano conversacional, curiosidad sutil y expresividad contenida.

El archivo sirve luego como referencia de clonación para Qwen3-TTS 0.6B Base. Su procedencia está documentada en:

- `D:\cacao voz\qwen-diseno\config\candidates.json`
- `D:\cacao voz\qwen-diseno\logs\generation_report.json`
- `D:\cacao voz\qwen-diseno\INFORME.md`

## 8. Conclusión y recomendación

`swa_full=False` merece incorporarse a producción después de una prueba corta controlada, porque conserva 195/195 y libera alrededor de **2,7 GiB en Q5** sin migrar de `llama-cpp-python 0.3.36`. Antes deben trasladarse la corrección de caracteres de control y sus pruebas a producción.

Gemma Q4 también queda validada: 195/195 en el conjunto histórico y 90/90 en el nuevo, con mejor velocidad y unos 499 MiB menos de VRAM que Q5 bajo `swa_full=False`. La evaluación humana a ciegas debe decidir si su conversación conserva la calidad suficiente.

No recomiendo habilitar todavía el conjunto completo al iniciar Cacao. La VRAM cabe, pero la RAM llega al límite y la recarga fría tarda más de seis minutos. El siguiente trabajo debe reducir RAM y tiempo de arranque de vLLM/WSL, crear un supervisor no bloqueante y corregir el falso positivo de “escrita” antes de plantear el cambio de voz.

## 9. Archivos de evidencia

- `C:\asistente\comparacion_modelos\datos\ronda3\gemma_q5_swa_false.json`
- `C:\asistente\comparacion_modelos\datos\ronda3\gemma_q4_swa_false.json`
- `C:\asistente\comparacion_modelos\datos\ronda3\gemma_q5_swa_false_nuevas30.json`
- `C:\asistente\comparacion_modelos\datos\ronda3\gemma_q4_swa_false_nuevas30.json`
- `C:\asistente\.comparacion-runtime\full-wsl\benchmark.json`
- `C:\asistente\.comparacion-runtime\full-wsl\windows_ram_samples.json`
- `C:\asistente\resultados_ciegas_q4.md`
- `C:\asistente\clave_resultados_ciegas_q4.md`

`config.json` conservó el SHA-256 `fb10d3ec38a7ae49ce3c51cfeca6740d7cefe19aa5d1ede08eee078fe74c884e`. `.venv` no fue modificado.
