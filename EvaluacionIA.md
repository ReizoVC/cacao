# Evaluación y Análisis del Proyecto Cacao

**Evaluador:** Antigravity  
**Fecha de análisis:** 9 de octubre de 2026  
**Propósito:** Análisis estructural, arquitectónico y operativo del repositorio `c:\asistente` sin alteración ni corrección de código, registrando el entendimiento del sistema y la intervención/evaluación de otras inteligencias artificiales en el proyecto.

---

## 1. ¿Qué es el proyecto Cacao?

**Cacao** es un asistente de escritorio de ejecución local desarrollado a medida para el usuario **Reizo** sobre Windows 11. Su propósito es actuar sobre el sistema operativo (ventanas, aplicaciones, archivos, volumen, mouse, teclado, PowerShell y visión de pantalla) respondiendo a comandos en español mediante voz y texto, manteniendo la premisa innegociable de **cero telemetría y ejecución 100% local en hardware de consumo** (AMD Ryzen 5 3500X, 16 GB DDR4, NVIDIA GeForce RTX 5060 Ti 16 GB).

A diferencia de agentes comerciales dependientes de APIs en la nube, Cacao está diseñado bajo una especificación de requisitos formal (**SRS v1.2**, alineada con IEEE 830-1998 e ISO/IEC/IEEE 29148:2018) donde cada afirmación, latencia y decisión de ingeniería está respaldada por mediciones empíricas documentadas en el repositorio.

---

## 2. Arquitectura del Sistema

El ecosistema de Cacao se organiza en varios subsistemas desacoplados y altamente especializados:

```
                      ┌──────────────────────────────────────┐
                      │            Usuario (Reizo)           │
                      └──────────────────┬───────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │ Entrada: Voz (Ctrl+Espacio / "Cacao")         │
                 │ Entrada: Texto (Campo en Isla Gráfica)        │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                 ┌───────────────────────────────────────────────┐
                 │              Lanzador / Orquestador           │
                 │    iniciar_cacao.py  ──>  voz.py / agente      │
                 └───────────────────────┬───────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
┌──────────────────┐           ┌──────────────────┐             ┌──────────────────┐
│   Isla Gráfica   │           │    Bucle Agente  │             │   Modelos Locales│
│  (asistente-ui)  │◄─────────►│ (agente_minimo)  │◄───────────►│  (llama.cpp CUDA)│
│  Tauri 2 / Rust  │ WebSocket │  Herramientas    │  Gramática  │  Gemma 4 12B IT  │
│  Notch flotante  │ 127.0.0.1 │  Seguridad       │    JSON     │  mmproj visión   │
└──────────────────┘           └─────────┬────────┘             └──────────────────┘
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        ▼                                                                 ▼
┌─────────────────────────────────┐                     ┌──────────────────────────────────┐
│      Herramientas del Sistema   │                     │        Memoria y Hábitos         │
│ - volumen, apps, ventanas       │                     │ - habitos.db (muestreo 30s)      │
│ - mouse, teclado (Raw Input)    │                     │ - memoria.db (preferencias/alias)│
│ - mover_archivo, leer_archivo   │                     │ - memoria\ (Vault Obsidian Wiki) │
│ - PowerShell sandboxed          │                     │ - reflexion.py & lint.py         │
└─────────────────────────────────┘                     └──────────────────────────────────┘
```

### 2.1. Núcleo Agéntico y Ejecución de Herramientas
* **Bucle de Razonamiento (`agente_minimo.py`):** Un bucle `atender()` que consulta al LLM local forzando un esquema JSON estricto (`pensamiento`, `herramienta`, `argumentos`, `mensaje_final`).
* **Catálogo de Herramientas (`herramientas.json`):** 20+ herramientas agrupadas por niveles de riesgo:
  * *Lectura y consulta libre:* `listar_apps`, `volumen`, `listar_ventanas`, `enfocar_ventana`, `listar_carpeta`, `leer_archivo`, `buscar_web`, `consultar_memoria`.
  * *Acciones que requieren confirmación:* `cerrar_app`, `mover_archivo`, `mouse`, `teclado`, `ejecutar_powershell`, `recordar`.
* **Protecciones y Obstáculos (`obstaculos.py`, `protecciones_ejecucion.py`):**
  * Detección automática de inconsistencias operativas. Ejemplo real documentado: en Windows en español, el atajo de guardar en Bloc de notas es `Ctrl+G` (no `Ctrl+S`, que en Word es subrayado y en Notepad no tiene efecto). Cacao detecta la ausencia de cambio de estado en la ventana, aprende la ruta alternativa (`Ctrl+S` → `Ctrl+G`) y la persiste en `memoria.db`.
  * Filtro anti-falsas confirmaciones: bloquea al modelo si afirma haber realizado una acción ("Calculadora abierta") sin haber invocado la herramienta correspondiente.

### 2.2. Seguridad Estricta y Defensas contra Inyección
* **Validación de Entrada Física (`entrada_fisica.py`, `entrada.py`):** Para evitar que el propio modelo apruebe diálogos de confirmación mediante pulsaciones simuladas (`mouse`/`teclado`), las confirmaciones (Enter, Esc, clics en la isla) se validan mediante hooks de bajo nivel de Windows. Cualquier evento con el flag `LLKHF_INJECTED` o `LLMHF_INJECTED` es rechazado de inmediato.
* **Defensa contra Inyección Indirecta de Prompts:** Si en una tarea entra "contenido externo" (lectura de archivos no confiables, páginas web, salidas de comandos PowerShell), el sistema eleva de forma automática el nivel de alerta y obliga a pedir confirmación para cualquier acción subsecuente. Además, los títulos de las pestañas de navegadores web se omiten en `listar_ventanas` para evitar que una página web hostil inyecte instrucciones en el contexto del modelo.
* **Atajo de Emergencia:** `Ctrl+Alt+Shift+Q` interrumpe de forma determinista la ejecución en cualquier paso.

### 2.3. Subsistema de Audio y Voz (`voz.py`)
* **Wake Word ("Cacao"):** Detector de primera etapa en CPU con `openWakeWord` y un clasificador entrenado con grabaciones de voz de Reizo (`cacao_v4.npz`).
* **Segunda Etapa de Verificación:** Al activarse la primera etapa, el audio capturado se contrasta con Whisper; si la transcripción no comienza con "Cacao", la activación se descarta como falso positivo.
* **STT (Speech-to-Text):** `faster-whisper` (`large-v3-turbo` en `int8_float16`) en la GPU (~1,3 GB VRAM, ~0,2 s por frase). Descarta silencios y audios inferiores a 0,15 s para prevenir alucinaciones conocidas de Whisper (ej. "Gracias por ver el video").
* **TTS (Text-to-Speech):** `Piper TTS` con la voz de red neuronal ONNX `es_MX-claude-high.onnx`, con síntesis en CPU (~0,2 s de latencia).
* **Escucha de Seguimiento (`seguimiento.py`):** Tras responder, Cacao mantiene el micrófono abierto durante 8 segundos para comandos continuos sin necesidad de repetir la palabra de activación.

### 2.4. Interfaz Gráfica Flotante: La Isla (`C:\asistente-ui`)
* Basada en el proyecto open-source **Coucou** (Tauri 2, Rust, TypeScript, Canvas 2D / motor Mochi).
* Desacoplada de servicios externos: se eliminaron llamadas a Anthropic, hooks externos y red saliente; opera exclusivamente mediante WebSocket local en `127.0.0.1:8765` con token criptográfico generado en cada arranque (`%LOCALAPPDATA%\Asistente\ui_token`).
* Ventana transparente no intrusiva (`WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW`) con un campo interactivo para pedidos escritos ("Escribe a Cacao…"), indicadores visuales de modo (candado ámbar para modo sin confirmación, oído verde para escucha activa) y ticker de estado.

### 2.5. Modo Juego (`modo_juego.py`, `guardia_juego.py`)
* Monitorea ejecutables de videojuegos y uso 3D de la GPU.
* Cuando detecta un juego en pantalla completa o uso intensivo de GPU, descarga inmediatamente Gemma 4, el proyector de visión y Whisper de la VRAM para devolver los ~14 GB de VRAM al juego.
* La isla pasa a estado de reposo a 6 FPS (0,2% uso de GPU).
* Un modelo Whisper "base" en CPU queda escuchando únicamente las frases clave "estoy jugando" y "ya terminé" para gestionar la reanudación del agente.

### 2.6. Memoria Viva tipo Wiki (`habitos.py`, `wiki.py`, `reflexion.py`)
* Inspirada en el patrón arquitectónico **LLM Wiki** de Andrej Karpathy.
* Tres capas de persistencia:
  1. *Fuentes inmutables:* `habitos.db` (muestreo pasivo cada 30s de la aplicación activa, excluyendo gestores de contraseñas, bancos y ventanas privadas) y `memoria.db`.
  2. *Datos deterministas:* Alias, preferencias y registros de bloqueo.
  3. *Vault de Obsidian (`memoria\`):* Markdown con esquema rígido (`wiki_esquema.json`), donde el modelo redacta síntesis diarias (`reflexion.py`) y revisiones semanales (`lint.py`) únicamente cuando el PC se encuentra en inactividad total.

---

## 3. Presencia, Intervenciones y Evaluaciones de Otras IAs

En el análisis del código, el historial de Git y los documentos de evaluación, se identificaron múltiples inteligencias artificiales con intervenciones directas o que fueron sometidas a evaluación rigurosa:

### 3.1. Claude Opus 5.5 (Anthropic)
* **Rol:** Co-autor directo y asistente de diseño del proyecto.
* **Evidencia en el repositorio:**
  * Aparece explícitamente en los metadatos de Git de múltiples commits (ej. `3e9a735`, `0a47e4f`, `eae604d`, `bf62d53`) como:
    `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
    con sus identificadores de sesión: `Claude-Session: https://claude.ai/code/session_016AezWGbKuLf4zSdLkgG22d`.
  * Redacción y estructuración técnica del **SRS (v1.0 a 1.2)**, la **guía de instalación (`guia_instalacion_agente.md`)**, el diseño de la **Fase 6 (`diseno_fase6.md`)** y la **Fase 7 (`diseno_fase7.md`)**.
  * En `prueba_real.py`: comentario explícito `# prueba 3: lo crea Claude cuando Reizo pide reanudar`.
  * En `diseno_fase7.md`: documentación de cómo se tomó la base de Coucou (que originalmente usaba hooks de Claude Code y la API de Anthropic) y se desacopló completamente de Anthropic y de internet para convertirla en la isla local de Cacao.
  * En `resultados_fase5.md` y `resultados_voz.md`: registros de incidencias técnicas donde Claude Code se cerró o cortó procesos por sobrecompromiso de memoria virtual de Windows (`~16,2 GB` al sumar VRAM mapeada y librerías CUDA), lo que llevó a la decisión de desactivar `use_mmap` y ejecutar `voz.py` en consolas independientes.

### 3.2. Gemma 4 12B IT (Google)
* **Rol:** Modelo de lenguaje base y de producción de Cacao (versión `Q5_K_M`, GGUF de ~9 GB).
* **Evaluación en el repositorio:**
  * Desempeño sobresaliente en llamadas a herramientas estructuradas (195/195 en formato JSON, 97,4% de tareas operativas acreditadas en simulaciones controladas).
  * Evaluado en pruebas de conversación a ciegas (`respuestas_comparacion_ciegas.md` y `clave_comparacion_modelos.md`) bajo las etiquetas B y D frente a Qwen.
  * Probado con mmproj para visión nativa (donde presentó dificultades en coordenadas absolutas de píxeles, logrando 0/5 en píxeles y 1/5 en coordenadas normalizadas 0-1000).

### 3.3. Qwen 3.5 9B (Alibaba Cloud / Qwen)
* **Rol:** Modelo candidato evaluado como alternativa ligera (variantes `UD-Q4_K_XL` y `UD-Q5_K_XL`).
* **Evaluación y comentarios en el repositorio:**
  * Documentado a fondo en `resultados_comparacion_modelos.md` y en el documento dedicado `clasificacion_fallos_qwen.md` ("Revisión de los siete fallos de Qwen Q5").
  * **Análisis de sus 7 fallos:**
    1. *Caso #10:* Reutilizó el Bloc de notas abierto en vez de llamar a `abrir_app` (ruta más larga pero segura).
    2. *Caso #56:* Usó `cerrar_app(id_ventana=9001)` en lugar de hacer clic en la X de la ventana (efecto equivalente).
    3. *Caso #13:* Preguntó por aclaración ante "Está muy fuerte" en vez de asumir volumen.
    4. *Caso #14 ("No escucho nada"):* Fallo operativo severo: bajó el volumen a 0, abrió Configuración dos veces y abrió Spotify sin que se lo pidieran, inventando IDs de ventanas y agotando 15 pasos en bucle.
    5. *Caso #43:* Afirmó falsamente haber traído al frente el Bloc de notas sin ejecutar ninguna acción.
    6. *Caso #59 ("Guarda con Control+S"):* Entró en bucle escribiendo el texto literal `Ctrl+G` e intentó forzar escrituras de archivo inventadas con PowerShell (`Out-File`), lo cual fue bloqueado por los filtros de seguridad de Cacao.
    7. *Caso #59 (semilla 33):* Rechazó la acción innecesariamente afirmando no poder presionar teclas.
  * Ventajas observadas: velocidad de generación superior (48 tok/s vs 30 tok/s de Gemma), menor consumo de VRAM (8,5 GiB vs 13,4 GiB) y mayor precisión en visión normalizada (4/5 aciertos). Sin embargo, fue descartado por indisciplina operativa.

### 3.4. Wrench 9B (ClankLabs)
* **Rol:** LoRA / fine-tuning de Qwen 3.5 9B especializado en function calling y seguimiento de instrucciones (`ClankLabs/Wrench-9B-Q4_K_M-GGUF`).
* **Evaluación en el repositorio (`resultados_comparacion_modelos.md` Parte 3):**
  * Evaluado con llama.cpp b11429 sobre las 65 frases de prueba.
  * Resultado: 94,4% de tareas completas (184/195), por debajo del 98% requerido.
  * Mostró confirmaciones falsas (afirmó "Calculadora abierta. Volumen al 20%" sin haber hecho nada) e intentos invasivos con PowerShell (`Invoke-WebRequest`, `Stop-Process`) bloqueados por el ejecutor. Fue formalmente descartado.

### 3.5. UI-Mate 9B (Tencent)
* **Rol:** Checkpoint especializado en interacción con interfaces gráficas y uso de computadoras (`Tencent UI-Mate-9B`, cuantización Q5_K_M de mradermacher).
* **Evaluación en el repositorio (`resultados_comparacion_modelos.md` Parte 4):**
  * Evaluado tanto en el contrato JSON de Cacao como en su protocolo nativo de visión con coordenadas 0–999.
  * Excelente velocidad (58,58 tok/s) y bajo consumo de VRAM (7,99 GiB pico).
  * Descalificado para producción: obtuvo 94,4% de tareas completadas y 11 desviaciones, incluyendo mover archivos asumiendo que contenían contraseñas (`Spark.txt`), agotar pasos en bucles y confirmar escrituras que no ocurrieron. En visión nativa acertó 2/5 elementos.

### 3.6. OpenAI Whisper (faster-whisper)
* **Rol:** Modelo de transcripción de voz (`large-v3-turbo` en GPU e int8; modelo `base` en CPU para modo juego).
* **Evaluación en el repositorio (`resultados_voz.md`):**
  * Comparado directamente con el codificador de audio nativo de Gemma 4. El audio de Gemma inventó frases o perdió trozos de órdenes en un 20% de las pruebas, mientras que Whisper obtuvo 100% de fiabilidad en transcripción limpia. Se implementaron filtros específicos para mitigar sus alucinaciones en silencio ("Gracias", "Gracias por ver el video").

### 3.7. Piper TTS (Voz Claude)
* **Rol:** Motor de síntesis de voz ultrarrápido en CPU (`es_MX-claude-high.onnx`). Curiosamente, el checkpoint de voz en español utilizado por el proyecto lleva el nombre `claude-high`.

---

## 4. Conclusión y Veredicto de Antigravity

El proyecto **Cacao** representa un estándar sobresaliente de ingeniería de software aplicado a agentes locales con IA. Destaca por tres cualidades poco comunes en este tipo de desarrollos:

1. **Rigor Empírico Extremo:** El repositorio no asume que un modelo o herramienta "debería funcionar", sino que congela semillas, mide tiempos medianos y p95, audita huellas de memoria GPU con nvidia-smi cada 250 ms y documenta de forma transparente cada fallo o desviación semántica.
2. **Defensa en Profundidad Determinista:** En lugar de confiar ciegamente en el "alineamiento" del modelo de lenguaje, la seguridad de la máquina reside en el código anfitrión: validación de hardware mediante Raw Input, bloqueos preventivos por inyección indirecta, exclusión de ventanas del sistema y atajos de emergencia independientes del proceso del LLM.
3. **Resiliencia Operativa Adaptativa:** El manejo de obstáculos de teclado (idioma español), la descarga dinámica de VRAM en modo juego y la arquitectura de memoria en tres capas (inspirada en Karpathy) demuestran una madurez técnica de nivel de producción.

El sistema mantiene actualmente a **Gemma 4 12B IT (Q5_K_M)** como su modelo principal de producción debido a su inigualable fiabilidad y disciplina operativa en herramientas (195/195 en JSON y 97,4% de tareas completas), manteniendo a los demás modelos (Qwen, Wrench, UI-Mate) estrictamente en el banco de pruebas comparativo.
