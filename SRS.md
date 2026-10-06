# Especificación de requisitos del software (SRS): asistente de escritorio con IA local

Estructura según IEEE 830-1998 e ISO/IEC/IEEE 29148:2018. Versión 1.0, 2026-10-05.

**Regla de este documento:** toda cifra viene de una medición registrada en el repositorio y lleva su fuente. Si algo
no se midió, se dice "no medido". Un requisito está **Verificado (real)** si se probó contigo frente al PC,
**Verificado (simulación)** si se probó con herramientas o datos simulados, y **Pendiente** si aún no se probó.

---

## 1. Introducción

### 1.1 Propósito

Especifica los requisitos del asistente de escritorio de Reizo: un agente que entiende pedidos en español (texto o voz)
y actúa sobre Windows con herramientas locales, con un modelo de lenguaje que corre en su PC. Sirve para:
- decidir si una versión es aceptable;
- comparar cambios (prompt, modelo, muestreo) con criterios medibles.

### 1.2 Alcance

**Lo que hace:**
- controla el volumen;
- abre, enfoca y cierra apps;
- lista ventanas, carpetas y controles, y lee archivos de texto;
- busca en la web (abre el navegador), mira la pantalla, usa mouse y teclado, y ejecuta PowerShell con límites;
- recuerda preferencias y alias;
- registra hábitos, mantiene una wiki de memoria (Obsidian) y sugiere rutinas;
- funciona por voz (pulsar para hablar) y libera la GPU cuando hay un juego abierto.

Todo el razonamiento es local: Gemma 4 12B en la GPU. La única salida a internet es `buscar_web`, que abre el
navegador predeterminado.

**Fuera de alcance:**
- la interfaz gráfica (isla), que está en diseño (`diseno_fase7.md`);
- la palabra de activación;
- el uso por más de un usuario.

### 1.3 Definiciones

| Término | Significado |
|---|---|
| Agente | Bucle `atender()` de `agente_minimo.py`: pide al modelo una acción JSON, la ejecuta y repite hasta `finalizar` |
| Herramienta | Función que el modelo puede pedir, definida en `herramientas.json` |
| Permiso "libre" / "confirmar" | Se ejecuta sin preguntar / necesita un sí explícito de Reizo |
| Bloqueo | Rechazo del ejecutor que corta la tarea sin dar más pasos al modelo; queda en la tabla `bloqueos` |
| Contenido externo | Texto que no viene de Reizo: archivos, web, pantalla, títulos, salida de PowerShell |
| Wiki | Vault de Obsidian en `memoria\` con páginas que mantiene el agente (Fase 6) |
| Reflexión / lint | Síntesis diaria del registro de hábitos en la wiki / revisión semanal de la wiki |
| Modo juego | Estado en que el agente descarga sus modelos de la GPU porque hay un juego abierto |
| Arnés simulado | `benchmark_gramatica.py` + `evaluar_pruebas.py`: el agente real con herramientas simuladas; con `SIN_REALES=1` también se simulan carpetas, archivos y pantalla |

### 1.4 Referencias (fuentes de las cifras)

`guia_instalacion_agente.md`, `herramientas.json`, `config.json`, `resultados_latencia.md`, `resultados_fase4.md`,
`resultados_fase5.md`, `resultados_voz.md`, `resultados_fase6.md`, `resultados_reflexion.json`,
`resultados_modo_juego_*.json`, `diseno_fase6.md`, `diseno_fase7.md`.

### 1.5 Visión general

- §2: el producto.
- §3: requisitos funcionales.
- §4: requisitos no funcionales con cifras.
- §5: seguridad.
- §6: interfaces.
- §7: casos de uso.
- §8: riesgos.
- §9: trazabilidad y pendientes.

---

## 2. Descripción general

### 2.1 Perspectiva del producto

Es una aplicación de escritorio para un solo PC, sin servidor ni cuenta, con este flujo:
1. un pedido entra por consola (`agente_minimo.py`) o voz (`voz.py`);
2. el modelo elige una herramienta con un JSON forzado por gramática (`pensamiento`, `herramienta`, `argumentos`,
   `mensaje_final` opcional);
3. el ejecutor aplica permisos, bloqueos y confirmaciones, ejecuta y devuelve el resultado al modelo.

Procesos y datos:
- un hilo aparte (planificador) hace la reflexión y el lint cuando no se usa el PC;
- otro proceso (`registro_habitos.py`) muestrea la app al frente;
- datos locales: `memoria.db`, `habitos.db` y la wiki `memoria\` (con su git).

### 2.2 Funciones principales

| Grupo | Herramientas |
|---|---|
| Apps y sistema | listar_apps, abrir_app, volumen, ejecutar_powershell |
| Ventanas y pantalla | listar_ventanas, enfocar_ventana, cerrar_app, ver_pantalla, listar_controles |
| Entrada | mouse, teclado |
| Archivos | listar_carpeta, leer_archivo, mover_archivo |
| Web | buscar_web |
| Memoria | recordar, consultar_memoria, sugerencias, registro_habitos |
| Control | finalizar |

Hay 20 herramientas activas (`agente_minimo.ACTIVAS`). Cinco piden confirmación: `cerrar_app`, `mouse`, `teclado`,
`mover_archivo` y `ejecutar_powershell` (`herramientas.json`).

### 2.3 Usuario

Un único usuario (Reizo), que habla español (es-PE / es-MX). No necesita conocimientos técnicos para usarlo, pero
mantiene la configuración (`config.json`, `datos_locales.json`).

### 2.4 Entorno operativo

| Elemento | Valor | Fuente |
|---|---|---|
| CPU / RAM / GPU | Ryzen 5 3500X, 16 GB DDR4, RTX 5060 Ti 16 GB | guía, Fase 0 |
| SO | Windows 11, 10.0.26300.9550 | `diseno_fase7.md` |
| Python | 3.11.9 (`.venv`) | guía, Fase 1 |
| Modelo | Gemma 4 12B Q5_K_M (GGUF) + mmproj-F16 (visión) | `config.json` |
| Inferencia | llama-cpp-python 0.3.36 con CUDA; `n_ctx` 16 384; caché KV q8_0; flash attention; `use_mmap` false | `config.json` |
| Voz | faster-whisper large-v3-turbo int8_float16 (GPU) y Piper `es_MX-claude-high` (CPU) | `config.json`, `resultados_voz.md` |

### 2.5 Restricciones

- Todo local, sin servicios en la nube.
- Nada que pida permisos de administrador para funcionar; el registrador y el arranque automático son por usuario.
- **Dependencia frágil:** `LlamaRapida` sobrescribe un método interno de llama-cpp-python 0.3.36 (`muestreo_gramatica.py`).
- Una sola GPU de 16 GB compartida con juegos y otras apps.

### 2.6 Suposiciones

- WebView2, el driver NVIDIA (CUDA ≥ 12.8) y las Build Tools siguen instalados.
- Reizo usa el atajo de emergencia `ctrl+alt+shift+q` si algo va mal.

---

## 3. Requisitos funcionales

Formato: **ID**, requisito ("debe"), **criterio verificable** y estado.

### 3.1 Núcleo del agente

| ID | Requisito | Criterio de verificación | Estado |
|---|---|---|---|
| RF-01 | El agente debe responder siempre con un JSON válido según `ESQUEMA_ACCION` | JSON válido = 100 % en el set de pruebas | Verificado (simulación): 100 % en todas las corridas (`resultados_fase4.md` a `resultados_fase6.md`) |
| RF-02 | Debe elegir la herramienta correcta en el primer paso | ≥ 95 % de "primera herramienta" en las 60 frases × 3 semillas | Verificado (simulación): 98,9 % (base `SIN_REALES`), 99,4 % con Fase 6 y **100 %** con la regla de la frase 58 (§4.4) |
| RF-03 | Debe completar tareas de varios pasos | ≥ 95 % de "tarea completa" en las 60 frases | Verificado (simulación): 98,9 % / 99,4 % / **100 %** (§4.4) |
| RF-04 | En tareas de un paso con `mensaje_final` debe responder sin una segunda llamada al modelo y rellenar `{campo}` con el resultado | "Listo, subí el volumen a {volumen_actual}%" sale con el valor real | Verificado (simulación) (`resultados_fase4.md`, punto 4) |
| RF-05 | Debe limitar cada tarea a `max_pasos_por_tarea` (15) | Al pasarse, responde "Me pasé del límite de pasos…" | Verificado en código (`agente_minimo.atender`) |
| RF-06 | Tras un clic o un atajo de teclado, debe comprobar el efecto (listar_controles / ver_pantalla / listar_ventanas) antes de darlo por hecho | Si el modelo intenta `finalizar` sin comprobar, el ejecutor se lo pide (máximo 2 veces) | Verificado (real), Fase 5, quinta tanda |
| RF-07 | Si Reizo nombra una app para hacer algo dentro de ella, debe usar una ventana ya abierta antes de abrir otra | Frase 58: `listar_ventanas` → `enfocar_ventana` → `teclado` en 3/3 semillas | Verificado (simulación), ver §4.4 |

### 3.2 Apps, ventanas y archivos

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-10 | `abrir_app` debe abrir por nombre exacto, siglas ("VS Code") o alias guardado, y preguntar si es genérico o ambiguo | "abre el editor" con el alias guardado → VS Code; sin alias, pregunta | Verificado (real), Fase 5 (`resultados_fase5.md` §1) |
| RF-11 | `listar_apps` debe filtrar por nombre o categoría (12 categorías) | "¿qué apps de música tengo?" → `listar_apps{filtro: música}` | Verificado (simulación y real) |
| RF-12 | `cerrar_app` debe cerrar normal y solo forzar si se pide o falla, sin cerrar ventanas no pedidas | Bloc de notas cerrado por `id_ventana` | Verificado (real), Fase 5, quinta tanda |
| RF-13 | `listar_carpeta`, `leer_archivo` y `mover_archivo` solo deben actuar dentro de las 6 carpetas permitidas (Escritorio, Documentos, Descargas, Imágenes, Música, Videos) | `leer_archivo C:\Windows\win.ini` → rechazado | Verificado (simulación y real) |
| RF-14 | `mover_archivo` nunca debe sobrescribir | Con destino existente, falla | Verificado (simulación), Fase 5, grupo 4 |
| RF-15 | `ver_pantalla` debe respetar el presupuesto de tokens de imagen (70–1120) | Tokens de imagen ≈ presupuesto (306 / 569 / 1212 / 108 medidos) | Verificado (real) (`resultados_fase5.md`, visión) |
| RF-16 | `mouse` debe hacer clic por nombre de control (UI Automation) y, como respaldo, por coordenadas de una captura de menos de 2 minutos | Clic en "Archivo" del Bloc de notas, abre el menú y se verifica | Verificado (real) (`resultados_real_2m.json`) |
| RF-17 | `teclado` debe escribir texto Unicode y pulsar atajos | "hola mundo" escrito correctamente (pegando por el portapapeles) | Verificado (real), quinta tanda |

### 3.3 PowerShell

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-20 | `ejecutar_powershell` debe mostrar el motivo y el comando y pedir confirmación | "Motivo:" y "Comando:" antes del s/n | Verificado (real): `Get-Date` en 5,9 s (`resultados_fase5.md` §7) |
| RF-21 | Debe bloquear los 42 patrones de `powershell_patrones_bloqueados` (borrar, registro, instalar, red, apagar, ofuscación…) sin pedir confirmación | 18/18 bloqueados; sin falsos positivos con "model" y "Delete" | Verificado (simulación) (`probar_powershell.py`) |
| RF-22 | Si el comando solo consulta, debe rechazar la escritura a archivo (Out-File, Set-Content, Add-Content, Tee-Object, Export-*, `>`, `>>`) sin cortar la tarea; `2>&1` y `> $null` se permiten | 12 consultas que escriben, rechazadas; 9 casos legítimos, permitidos; en simulación el modelo corrige el comando solo | Verificado (simulación): 59/59 (`probar_powershell.py`) |
| RF-23 | Debe cortar el comando a los 30 s o con el atajo de emergencia | Proceso falso cortado a los 0,3 s de prueba | Verificado (simulación) |

### 3.4 Voz

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-30 | Mantener Ctrl+Espacio debe grabar y soltar debe enviar | Atajo registrado con `RegisterHotKey`; la app al frente no lo recibe | Verificado (real) (`resultados_voz.md` §7) |
| RF-31 | Debe descartar pulsaciones con menos de 0,15 s de voz y transcripciones con más de 6 palabras por segundo de voz + 3 | Los 3 silencios o ruidos de la validación, frenados | Verificado (real) |
| RF-32 | Las acciones que cambian algo se confirman con Enter (sí) / Esc (no); sin respuesta en 30 s = no | `probar_voz.py` 11/11 | Verificado (simulación). **Rechazo con Esc en vivo: Pendiente** |
| RF-33 | Solo se lee en voz alta la respuesta final, en 1–2 frases | Pensamiento y confirmaciones solo en consola | Verificado (real) |

### 3.5 Memoria, hábitos y wiki (Fase 6)

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-40 | `recordar` debe guardar sin duplicar; los alias y preferencias entran en el prompt de la sesión siguiente | Sesión 2: "abre el editor" → VS Code, 3/3 | Verificado (simulación) (`resultados_fase5.md` §3) |
| RF-41 | El registrador debe guardar cada 30 s la app, la categoría y el estado, **sin títulos**; las apps privadas y el incógnito, sin fila | 7 días simulados: 0 trampas en la base, 56/56 muestras privadas sin fila | Verificado (simulación) (`resultados_fase6.md`). En real: Pendiente |
| RF-42 | Las muestras crudas deben borrarse a los 30 días; el resumen diario se conserva | Purga de 8 672 muestras con el resumen intacto | Verificado (simulación) |
| RF-43 | La reflexión diaria debe escribir perfil, hábitos, apps y rutinas con estructura y fechas puestas por el código | 4 páginas, estructura y frontmatter correctos, 3/3 semillas | Verificado (simulación con el modelo real): 24/24 (`resultados_reflexion.json`) |
| RF-44 | La reflexión no debe contradecir el texto de Reizo, revisando TODO su texto | Comprobación directa 7/7 con una nota de ~4 350 tokens en 2 trozos | Verificado (simulación con el modelo real) |
| RF-45 | La reflexión solo debe arrancar con ≥ 10 min sin teclado, mouse ni mando, sin pantalla completa, sin juego, sin audio bloqueante y con GPU < 20 %; y detenerse con actividad | 11/11 condiciones; guardia detiene en ~0,3–0,6 s | Verificado (simulación) |
| RF-46 | Las secciones editadas por Reizo no deben sobrescribirse; escribir se pospone si el archivo cambió hace < 5 min o está activo en Obsidian | Pruebas de wiki 22/22 | Verificado (simulación) |
| RF-47 | El lint semanal debe arreglar lo mecánico y anotar el resto en `revision.md` sin acusar al texto de Reizo | 11/11 | Verificado (simulación) |
| RF-48 | Las sugerencias deben ser solo texto: máximo 2 al día, apoyo ≥ 4 de 7 días en el inicio de uso, bloqueo permanente, desbloqueo por número, texto o casilla | 18/18 | Verificado (simulación) |
| RF-49 | `consultar_memoria` debe devolver también las 1–2 secciones de la wiki más relacionadas (≤ 2 400 caracteres), nunca de `fuentes/` | "¿qué suelo hacer los lunes?" → consultar_memoria, 3/3 | Verificado (simulación) |

### 3.6 Control y modo juego

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-50 | El atajo `ctrl+alt+shift+q` debe cortar la tarea en curso y dejar el agente detenido hasta "reanudar" | Corte y rechazo de tareas hasta reanudar | Verificado (real) (`resultados_fase5.md` §3) |
| RF-51 | Con un juego ACTIVO (ventana visible o GPU sostenida; termina tras 2 min sin señales; sin lanzadores, Wallpaper Engine ni Game Bar) debe descargar Gemma, la visión y Whisper, y recargarlos al terminar; "estoy jugando" / "ya terminé" lo fuerzan; un pedido en pausa recibe un aviso | Lógica 11/11; tiempos en §4.1. La detección reconoció un juego real abierto (Roblox: `RobloxPlayerBeta.exe` y `RobloxCrashHandler.exe`) | Verificado (simulación y detección real). Ciclo completo en real: Pendiente |

---

## 4. Requisitos no funcionales (con cifras medidas)

### 4.1 Rendimiento

| ID | Requisito | Medido | Fuente |
|---|---|---|---|
| RNF-01 | Generación con gramática ≥ 30 fichas/s | **38,0 fichas/s (26,3 ms/ficha)**; sin el arreglo, 8,1 | `resultados_latencia.md` |
| RNF-02 | Pedido de un paso en texto ≤ 3 s | Frases de la Fase 3: **1,85–3,33 s** | `resultados_fase4.md` §2 |
| RNF-03 | Media del set de 60 frases ≤ 5 s | **4,18 s** (base) / **4,25 s** (Fase 6) / **3,85 s** (con la regla de la frase 58), simulado | `resultados_fase6.md` |
| RNF-04 | Voz, de soltar la tecla a que empieza a hablar, ≤ 7 s en consultas | **4,0–6,2 s** (transcribir 0,4–0,6 s, agente 3,1–5,5 s, Piper 0,1–0,4 s) | `resultados_voz.md` §9 |
| RNF-05 | `ver_pantalla` (presupuesto 280) ≤ 4 s | **2,3–3,0 s**; dentro del agente, "¿qué hay en mi pantalla?" 5,0–6,1 s | `resultados_fase5.md`, visión |
| RNF-06 | Corte del atajo de emergencia ≤ 250 ms | **15–25 ms** generando; **33–206 ms** leyendo un prompt de 6 735 fichas (antes, 4,2–5,6 s) | `resultados_fase5.md` |
| RNF-07 | Reflexión diaria ≤ 3 min de GPU | **~30 s** (4 páginas + comprobación); lint ~1,2 s | `resultados_reflexion.json` |
| RNF-08 | Modo juego: liberar la VRAM en ≤ 1 s y volver en ≤ 20 s | Descarga: Gemma + visión **0,19–0,20 s** (VRAM de la GPU 12 971 → 1 227 MB); Whisper **0,01 s** (~1,0 GB). Recarga: Gemma + visión **9,63–9,64 s**, Whisper **2,91–3,00 s** (~12,6 s en total). Antes de cada cambio hay 2 comprobaciones cada 5 s (~10 s). Juego simulado, 2 ciclos, sin fuga | `resultados_modo_juego_gemma.json`, `resultados_modo_juego_whisper.json` |

### 4.2 Memoria de GPU y RAM

| ID | Requisito | Medido | Fuente |
|---|---|---|---|
| RNF-10 | Agente con visión ≤ 13 GB de VRAM | 855 MiB sin modelo → **12 367 MiB** con el modelo → **12 830–12 900 MiB** con visión | `resultados_fase5.md`, visión |
| RNF-11 | Con voz, dejar ≥ 2 GB de VRAM libre | Pico **13 730 de 16 311 MB** (2 581 MB libres), con Chrome, Claude y ChatGPT abiertos | `resultados_voz.md` §9 |
| RNF-12 | Whisper ≤ 1,5 GB de VRAM | **1,34 GB** (large-v3-turbo int8) | `resultados_voz.md` §6 |
| RNF-13 | RAM física del agente ≤ 2 GB y sin fugas | **1 175 MB** tras cargar; **1 297 → 1 302 MB** en 6 tareas (+4–5 MB); el sistema conserva 8,3–8,5 GB libres | `resultados_fase5.md` §4 |
| RNF-14 | Contexto de un pedido típico ≤ 16 384 fichas | Prompt de sistema **~3 140 → ~3 600** fichas (+índice de ~135); un pedido típico, ~6–10 k (estimado) | `resultados_fase6.md` |
| RNF-15 | Memoria comprometida | ~13,6 GB con Gemma; ~16,2 GB con transcripción y Piper. Es memoria virtual, no RAM física | `resultados_voz.md`, incidencias |

### 4.3 Precisión

| ID | Requisito | Medido | Fuente |
|---|---|---|---|
| RNF-20 | Transcripción: 0 fallos de sentido en la validación | **0/17** frases habladas con fallo; **2,7 %** de palabras erróneas; en vivo 5/5 | `resultados_voz.md` |
| RNF-21 | Primera herramienta ≥ 95 % (60 frases × 3) | 98,3 % (Fase 4, 40 frases) → 98,9 % (Fase 5, 60) → 99,4 % (Fase 6, `SIN_REALES`) → **100 %** (frase 58) | `resultados_fase4/5/6.md` |
| RNF-22 | Reflexión: detectar los patrones simulados sin trampas ni contradicciones | 24/24; comprobación 7/7 | `resultados_reflexion.json` |

### 4.4 Regresión tras la regla de la frase 58

Regla nueva en el prompt: si Reizo nombra una app para hacer algo dentro de ella, primero `listar_ventanas` y
`enfocar_ventana`; `abrir_app` solo si no hay ventana. Mismo arnés en las tres pasadas (`SIN_REALES=1`, 3 semillas):

| Pasada | 60 frases: primera herramienta | Tarea completa | Frase 58 | Tiempo medio | Fuente |
|---|---|---|---|---|---|
| Base (sin Fase 6) | 178/180 (98,9 %) | 98,9 % | 1/3 | 4,18 s | `resultados_pruebas_60_sinreales_base.json` |
| Fase 6 | 179/180 (99,4 %) | 99,4 % | 2/3 | 4,25 s | `resultados_pruebas_65_sinreales_fase6.json` |
| **Con la regla** | **180/180 (100 %)** | **100 %** | **3/3** | **3,85 s** | `resultados_pruebas_65_frase58.json` |

Con las 5 frases de la Fase 6: 195/195. Un primer texto de la regla hizo que la frase 56 ("haz clic en la X de la
ventana activa") empezara con `listar_ventanas` en 3/3. Se acotó a "cuando nombra una app" y volvió a 3/3.

### 4.5 Fiabilidad y mantenimiento

| ID | Requisito | Situación |
|---|---|---|
| RNF-30 | Los errores de llama.cpp/CUDA deben quedar registrados | `modelo.py` los muestra y los guarda en `errores_llama.log` (`resultados_voz.md`, incidencias) |
| RNF-31 | La reflexión, el lint y el modo juego nunca deben tumbar al agente | Capturan sus excepciones, las anotan y reintentan más tarde (código) |
| RNF-32 | Las pruebas no deben tocar datos reales | Bases y vault temporales (`*_prueba*`), borrados al terminar |
| RNF-33 | Cada fase tiene su script de pruebas | `evaluar_pruebas.py`, `probar_fase6.py` (142/142), `probar_powershell.py` (59/59), `probar_modo_juego.py` (11/11), `probar_voz.py` (11/11) |

---

## 5. Requisitos de seguridad y privacidad

| ID | Requisito | Mecanismo | Estado |
|---|---|---|---|
| RS-01 | Ninguna acción con efecto se ejecuta sin un sí explícito | Permiso "confirmar" en 5 herramientas; en voz, toda acción no de solo lectura | Verificado (real) |
| RS-02 | Las acciones prohibidas no deben existir como herramienta (borrar, registro, configuración del sistema, instalar, apagar) | `acciones_prohibidas` y 42 patrones de PowerShell | Verificado (simulación) |
| RS-03 | Un bloqueo debe cortar la tarea sin dar al modelo otro camino | `bloqueado: true` → `terminar()` y registro en `bloqueos` | Verificado (simulación y real): "abre regedit", 1 paso |
| RS-04 | Las apps del sistema sensibles no se abren; las consolas piden confirmación | 9 ejecutables + 5 AppID bloqueados; 5 ejecutables + 24 AppID con confirmación | Verificado (simulación) |
| RS-05 | Los archivos de contraseñas y claves no se listan, leen, mueven ni nombran en PowerShell | 27 patrones sensibles, aplicados a la ruta entera | Verificado (real): el CSV de contraseñas de Descargas no aparece ni se lee (`resultados_fase5.md`) |
| RS-06 | `ver_pantalla` no captura ventanas sensibles | Rechaza la captura si la ventana activa es sensible; tapa en negro las demás | Verificado (real) |
| RS-07 | El contenido externo no debe poder guardar memorias ni tocar sugerencias | Tarea "contaminada" → `recordar`/`sugerencias`/`registro_habitos` piden confirmación; el origen lo pone el ejecutor | Verificado (simulación) |
| RS-08 | La wiki solo se alimenta de lo que dice Reizo, `recordar` y el registro de hábitos; nunca de `fuentes/` ni de salidas de herramientas | Exclusión por ruta; filtro sensible, de secretos y de apps privadas antes de escribir | Verificado (simulación) |
| RS-09 | El registro de hábitos no guarda títulos; privados e incógnito sin fila | Sin columna de título; título del navegador leído en memoria solo para detectar el incógnito | Verificado (simulación) |
| RS-10 | Las consultas de PowerShell no escriben archivos | RF-22 | Verificado (simulación) |
| RS-11 | Los datos personales no van al repositorio | `.gitignore`: `memoria.db`, `habitos.db`, `memoria/`, `datos_locales.json`, resultados y audios. La wiki tiene un git local sin remoto | Verificado (revisión del historial en la Fase 5) |
| RS-12 | Atajo de emergencia siempre disponible | RF-50 | Verificado (real) |

**Límite reconocido:** los patrones son una red de seguridad, no un sandbox. La barrera principal es la confirmación
(`herramientas_powershell.py`).

---

## 6. Interfaces

### 6.1 Usuario

- **Consola** (`agente_minimo.py`): pedidos por texto, confirmación s/n y "reanudar".
- **Voz** (`voz.py`): Ctrl+Espacio para hablar y Enter/Esc para confirmar; respuesta con Piper.
- **Obsidian**:
  - lectura y edición de la wiki;
  - notas en "Notas de Reizo" o `mis_notas/`;
  - casillas de desbloqueo en `rutinas.md`.
- **Isla gráfica (Fase 7):** `C:\asistente-ui`. Muestra los estados del agente con Mochi y pide las confirmaciones con
  botones, que solo aceptan clics físicos. Probada en simulación y con la isla real (`probar_fase7.py`, 37/37).

### 6.2 Software

| Interfaz | Detalle |
|---|---|
| Modelo | llama-cpp-python (CUDA) con `LlamaRapida`; JSON por gramática; visión por mtmd + mmproj |
| Windows | Win32 (pywin32/ctypes), UI Automation (pywinauto), pycaw (audio), `Get-StartApps` (PowerShell), `RegisterHotKey`, XInput y Raw Input (mandos) |
| Voz | faster-whisper (CTranslate2), Piper, sounddevice |
| Datos | SQLite (`memoria.db`, `habitos.db` en WAL), Markdown en el vault, git |
| Configuración | `config.json` (modelo, voz, memoria_wiki, modo_juego), `herramientas.json` (catálogo, permisos y límites), `wiki_esquema.json`, `datos_locales.json` |

### 6.3 Hardware

GPU NVIDIA con ≥ 16 GB (RTX 5060 Ti), micrófono (auriculares Logitech G435 en las pruebas) y mandos XInput/HID,
estos últimos solo para detectar actividad.

---

## 7. Casos de uso

| ID | Actor / disparador | Flujo principal | Alternativas y errores |
|---|---|---|---|
| CU-01 Volumen | Reizo: "baja un poco el volumen" | `volumen{bajar,10}` → "Listo, bajé el volumen a N %" sin segunda llamada | Ambiguo ("está muy fuerte") → baja igual |
| CU-02 Abrir una app | "abre el editor" | Alias de `memoria.db` → `abrir_app("VS Code")` | Sin alias → pregunta cuál; bloqueada (regedit) → bloqueo |
| CU-03 Escribir en una app abierta | "escribe 'hola mundo' en el bloc de notas" | `listar_ventanas` → `enfocar_ventana` → `teclado` (confirmación) → verificación | Sin ventana → `abrir_app`; Reizo dice no → no se escribe |
| CU-04 Consulta con PowerShell | "¿cuánto tiempo lleva encendido?" | Comando de lectura → confirmación → respuesta | Si propone `Out-File`, rechazo y comando corregido; patrón bloqueado → bloqueo |
| CU-05 Archivos | "lee el HELP.md de inventarios" | `listar_carpeta` → `leer_archivo` → resumen | Fuera de las carpetas permitidas o sensible → rechazo |
| CU-06 Ver la pantalla | "¿qué hay en mi pantalla?" | `ver_pantalla` (280–560) → descripción | Ventana activa sensible → rechazo; otras sensibles tapadas |
| CU-07 Orden por voz | Ctrl+Espacio | Graba → frenos → Whisper → agente → Piper | Silencio o texto inventado → descartado; acción → Enter/Esc |
| CU-08 Emergencia | `ctrl+alt+shift+q` | Corta la tarea y queda detenido | "reanudar" lo desbloquea |
| CU-09 Recordar | "cuando digo el editor me refiero a VS Code" | `recordar{alias}` → en el prompt desde la sesión siguiente | Tras contenido externo → pide confirmación |
| CU-10 Reflexión diaria | Planificador (día cerrado, PC inactivo) | Datos del código → frases del modelo → comprobación → escritura → índice → commit | Actividad, juego, audio o pantalla completa → se detiene y sigue después |
| CU-11 Sugerencia | Reizo habla a la hora de una rutina | "A esta hora (09:00) sueles abrir Spotify. ¿Lo abro?" | "no me sugieras eso" → bloqueada; listar o desbloquear |
| CU-12 Modo juego | Se abre un juego | Descarga Gemma, la visión y Whisper → pausa | Pedido en pausa → aviso; al cerrar el juego → recarga |

---

## 8. Riesgos

| ID | Riesgo | Probabilidad / impacto | Mitigación actual | Pendiente |
|---|---|---|---|---|
| R-01 | Inyección de instrucciones desde archivos, web, pantalla o títulos | Media / alto | Confirmación de acciones, bloqueos, tarea contaminada (RS-07), la wiki excluye `fuentes/` | Revisar con contenido real |
| R-02 | El modelo elige mal o da pasos de más (p. ej. frase 58) | Baja / medio | Set de 65 frases con 3 semillas por cada cambio | Seguir midiendo tras cada cambio de prompt |
| R-03 | VRAM insuficiente con juegos u otras apps | Media / alto | Modo juego (RF-51): libera ~11,7 GB (Gemma + visión) + ~1 GB (Whisper); quedan 2,6 GB libres en el pico con voz | Probar el ciclo en real. Resuelto: un juego en la bandeja (Roblox al cerrarlo) ya no cuenta, comprobado en real (solo lectura) |
| R-04 | El sistema se queda sin memoria comprometida (~16,2 GB con voz); Claude Code cortó procesos | Media / medio | `use_mmap` false; lanzar `voz.py` desde una terminal propia | — |
| R-05 | Error de CUDA intermitente (una vez al arrancar `voz.py`) | Baja / medio | Registro en `errores_llama.log` | Reproducir si vuelve |
| R-06 | Actualizar llama-cpp-python rompe `LlamaRapida` (método interno) | Media / alto | `requirements.txt` fija 0.3.36; `modo_gramatica: null` como vuelta atrás | Volver a medir al actualizar |
| R-07 | Windows de la rama Insider (26300): cambios de API o comportamiento | Media / medio | — | Volver a probar tras cada actualización grande |
| R-08 | Los patrones de PowerShell no son un sandbox (alias raros, ofuscación) | Media / alto | La confirmación es la barrera principal; `-enc`, `iex` e `Invoke-Expression` bloqueados | — |
| R-09 | Un mouse que deriva o el uso de otra persona reinicia la inactividad y la reflexión no arranca | Media / bajo | Diagnóstico Raw Input: era entrada real de dispositivos físicos (`resultados_fase6.md`) | Revisar contigo |
| R-10 | Whisper inventa texto en silencio o ruido | Alta sin frenos / alto | Frenos de silencio, palabras/s y frases de subtítulos | — |
| R-11 | Choque entre ediciones en Obsidian y escritura del agente | Baja / medio | Hash por sección, posponer 5 min, pestaña activa, escritura atómica | Probar en real |
| R-12 | Privacidad del registro de hábitos | Media / alto | Sin títulos, privados sin fila, purga a 30 días, base fuera de git | Lista de apps de banco (pendiente de Reizo) |
| R-13 | Licencia de los assets de Coucou (Fase 7) | Baja / medio | Uso personal y local, repositorio sin remoto | Cambiar nombre, personaje y sonidos si algún día se comparte |

---

## 9. Trazabilidad y pendientes

- **Requisitos → pruebas:**
  - RF-01..07 y RNF-21 → `evaluar_pruebas.py` y `pruebas.json` (65 frases);
  - RF-20..23 → `probar_powershell.py`;
  - RF-40..49 → `probar_fase6.py`, `probar_reflexion.py`;
  - RF-51 y RNF-08 → `probar_modo_juego.py`;
  - RF-30..33 → `probar_voz.py`, `validar_transcripcion.py`;
  - RF-50 → `probar_emergencia.py`, `prueba_real.py 3`.
- **Probado en real el 2026-10-05:** rechazo con Esc en voz; Whisper de la CPU con "estoy jugando" y "ya terminé";
  isla con clic físico en Permitir/Denegar y Enter, sin quitar el foco; modo juego con Roblox; incógnito en Chrome;
  regla de audio (música, video en ventana y en pantalla completa, llamada); registro de hábitos al arrancar.
- **Pendientes en real:**
  - actividad con un mando;
  - grabar la isla con "Permitir capturas";
  - registro de hábitos durante una semana (reflexión y sugerencias con datos reales);
  - Obsidian.
