# Especificación de requisitos del software (SRS): Cacao, asistente de escritorio con IA local

Estructura según IEEE 830-1998 e ISO/IEC/IEEE 29148:2018. Versión 1.2, 2026-10-06 (la 1.1 es del mismo día y la 1.0
del 2026-10-05).

**Regla de este documento:** toda cifra viene de una medición registrada en el repositorio y lleva su fuente. Si algo
no se midió, se dice "no medido". Un requisito está **Verificado (real)** si se probó contigo frente al PC,
**Verificado (simulación)** si se probó con herramientas o datos simulados, y **Pendiente** si aún no se probó.

**Cambios de la 1.1:** nombre del asistente (§3.9); modo juego con detección por actividad (§3.6); la isla y sus
confirmaciones con entrada física (§3.7); modo sin confirmación y atajos bloqueados (§3.8); confirmación por voz y
palabra de activación "Cacao" (§3.4); `autocompletar_login`, en simulación (§3.10); arranque automático,
preparado (§3.11); riesgos R-14 a R-21.

**Cambios de la 1.2:** en el modo sin confirmación, mouse y teclado ya no preguntan salvo un texto que puede venir de
contenido de fuera (RF-72, RF-73, RF-76); los navegadores salen sin el título de la pestaña (RF-79b); bloqueos
de escribir en ventanas sensibles (RF-79) y en el menú Inicio o la búsqueda, y de mouse y teclado en Configuración y
el Panel de control (RF-79a); isla proporcional al
monitor con tamaño en Ajustes, que se esconde sola tras responder, y ticker sin texto encimado; escucha de
seguimiento tras cada respuesta (§3.12); RS-16 y riesgos R-22 y R-23.

---

## 1. Introducción

### 1.1 Propósito

Especifica los requisitos de Cacao, el asistente de escritorio de Reizo: un agente que entiende pedidos en español
(texto o voz) y actúa sobre Windows con herramientas locales, con un modelo de lenguaje que corre en su PC. Sirve para:
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
- funciona por voz: pulsar para hablar o la palabra de activación "Cacao", y sigue oyendo unos segundos tras
  responder;
- muestra su estado y pide las confirmaciones en una isla gráfica;
- tiene un modo sin confirmación, que Reizo activa a mano, para acciones acotadas;
- libera la GPU cuando hay un juego activo;
- (en simulación, apagado) activa el autocompletado de contraseñas de Chrome sin que el modelo vea las credenciales;
- arranca al iniciar sesión (activado el 2026-10-06).

Todo el razonamiento es local: Gemma 4 12B en la GPU. La única salida a internet es `buscar_web`, que abre el
navegador predeterminado.

**Fuera de alcance:**
- el uso por más de un usuario y el reconocimiento de quién habla;
- cualquier herramienta que entregue usuarios o contraseñas al modelo.

### 1.3 Definiciones

| Término | Significado |
|---|---|
| Cacao | Nombre del asistente (y de su palabra de activación) |
| Agente | Bucle `atender()` de `agente_minimo.py`: pide al modelo una acción JSON, la ejecuta y repite hasta `finalizar` |
| Herramienta | Función que el modelo puede pedir, definida en `herramientas.json` |
| Permiso "libre" / "confirmar" | Se ejecuta sin preguntar / necesita un sí explícito de Reizo |
| Bloqueo | Rechazo del ejecutor que corta la tarea sin dar más pasos al modelo; queda en la tabla `bloqueos` |
| Contenido externo | Texto que no viene de Reizo: archivos, web, pantalla, títulos, salida de PowerShell |
| Entrada física | Tecla o clic de un dispositivo real: el hook de bajo nivel no lo marca `LLKHF_INJECTED` / `LLMHF_INJECTED` (`entrada_fisica.py`) |
| Isla | Interfaz gráfica de `C:\asistente-ui` (Tauri 2, basada en Coucou) conectada al agente por WebSocket local |
| Modo sin confirmación | Modo que Reizo enciende con un clic físico; deja pasar sin preguntar las acciones acotadas de `modo_directo.py` |
| Palabra de activación | "Cacao" dicho en voz alta: abre una grabación sin pulsar teclas (`palabra_activacion.py`) |
| Segunda etapa | Comprobación con Whisper de que la grabación empieza con "Cacao"; si no, la activación se descarta |
| Juego activo | Proceso de juego con ventana visible o con uso sostenido de la GPU (§3.6) |
| Wiki | Vault de Obsidian en `memoria\` con páginas que mantiene el agente (Fase 6) |
| Reflexión / lint | Síntesis diaria del registro de hábitos en la wiki / revisión semanal de la wiki |
| Modo juego | Estado en que el agente descarga sus modelos de la GPU porque hay un juego activo |
| Arnés simulado | `benchmark_gramatica.py` + `evaluar_pruebas.py`: el agente real con herramientas simuladas; con `SIN_REALES=1` también se simulan carpetas, archivos y pantalla |

### 1.4 Referencias (fuentes de las cifras)

- Documentos: `guia_instalacion_agente.md`, `herramientas.json`, `config.json`, `diseno_fase6.md`, `diseno_fase7.md`.
- Resultados: `resultados_latencia.md`, `resultados_fase4.md`, `resultados_fase5.md`, `resultados_voz.md`,
  `resultados_fase6.md`, `resultados_reflexion.json`, `resultados_modo_juego_*.json`, `resultados_cacao.json`,
  `resultados_cacao_instalado.json`, `resultados_oye_cacao.json`.
- Pruebas (el total sale al ejecutarlas y está en el mensaje del commit): `probar_modo_directo.py`,
  `probar_confirmacion_voz.py`, `probar_palabra_activacion.py`, `probar_fase7.py`, `probar_modo_juego.py`,
  `probar_voz.py`.

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
1. un pedido entra por consola (`agente_minimo.py`) o voz (`voz.py`: Ctrl+Espacio o la palabra "Cacao");
2. el modelo elige una herramienta con un JSON forzado por gramática (`pensamiento`, `herramienta`, `argumentos`,
   `mensaje_final` opcional);
3. el ejecutor aplica permisos, bloqueos, el modo sin confirmación y las confirmaciones (teclado físico, botones de la
   isla o la frase "confirmo la instrucción"), ejecuta y devuelve el resultado al modelo.

Procesos y datos:
- la isla (`asistente-ui.exe`), que el agente lanza y cierra, unida a su proceso por un Job de Windows;
- un hilo aparte (planificador) hace la reflexión y el lint cuando no se usa el PC; otro (modo juego) vigila los juegos;
- otro proceso (`registro_habitos.py`) muestrea la app al frente;
- datos locales: `memoria.db`, `habitos.db`, `historial_movimientos.json` y la wiki `memoria\` (con su git).

### 2.2 Funciones principales

| Grupo | Herramientas |
|---|---|
| Apps y sistema | listar_apps, abrir_app, volumen, ejecutar_powershell |
| Ventanas y pantalla | listar_ventanas, enfocar_ventana, cerrar_app, ver_pantalla, listar_controles |
| Entrada | mouse, teclado |
| Archivos | listar_carpeta, leer_archivo, mover_archivo, deshacer_movimiento |
| Web | buscar_web |
| Memoria | recordar, consultar_memoria, sugerencias, registro_habitos |
| Control | finalizar |

Hay 21 herramientas activas (`agente_minimo.ACTIVAS`). Seis piden confirmación: `cerrar_app`, `mouse`, `teclado`,
`mover_archivo`, `deshacer_movimiento` y `ejecutar_powershell` (`herramientas.json`). En voz, además, se confirma
toda herramienta que no sea de solo lectura (`voz.SOLO_LECTURA`). `autocompletar_login` (confirmar) está en el
catálogo pero fuera de `ACTIVAS` mientras `config.json` → `autocompletar_login.activa` sea false.

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
| Voz | faster-whisper large-v3-turbo int8_float16 (GPU), Whisper "base" en la CPU en modo juego y Piper `es_MX-claude-high` (CPU) | `config.json`, `resultados_voz.md` |
| Palabra de activación | Características de openWakeWord + clasificador propio (`modelos/cacao`), en la CPU | guía, Fase 7 punto 10 |
| Isla | Tauri 2 + WebView2 (runtime 154.0.4258.53); WebSocket en `127.0.0.1:8765` | `diseno_fase7.md` |

### 2.5 Restricciones

- Todo local, sin servicios en la nube.
- Nada que pida permisos de administrador para funcionar; el registrador y el arranque automático son por usuario.
- **Dependencia frágil:** `LlamaRapida` sobrescribe un método interno de llama-cpp-python 0.3.36 (`muestreo_gramatica.py`).
- Una sola GPU de 16 GB compartida con juegos y otras apps.
- La isla se compila con VS 2022 (`vcvars64.bat`); VS 18 Insiders no trae `msvcrt.lib`.

### 2.6 Suposiciones

- WebView2, el driver NVIDIA (CUDA ≥ 12.8) y las Build Tools siguen instalados.
- Reizo usa el atajo de emergencia `ctrl+alt+shift+q` si algo va mal.
- Quien está frente al teclado y el mouse es Reizo (ver R-16).

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
| RF-08 | Un "no" de Reizo (Denegar, Esc, sin respuesta) debe terminar la tarea: el modelo no prueba con otra ventana, app ni camino | Tras un rechazo, el ejecutor cierra con "No lo hice porque no lo autorizaste." sin otra llamada al modelo | Verificado (real) el 2026-10-05 (guía, Fase 7, "Corregido durante las pruebas") |

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
| RF-18 | `deshacer_movimiento` debe devolver a su ruta original todo lo que movió `mover_archivo` en la última tarea, sin sobrescribir | Movimiento y "deshaz lo último" sobre archivos reales en una carpeta temporal | Verificado (simulación) (`probar_modo_directo.py`, parte 5) |

### 3.3 PowerShell

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-20 | `ejecutar_powershell` debe mostrar el motivo y el comando y pedir confirmación | "Motivo:" y "Comando:" antes del s/n | Verificado (real): `Get-Date` en 5,9 s (`resultados_fase5.md` §7) |
| RF-21 | Debe bloquear los 42 patrones de `powershell_patrones_bloqueados` (borrar, registro, instalar, red, apagar, ofuscación…) sin pedir confirmación | 18/18 bloqueados; sin falsos positivos con "model" y "Delete" | Verificado (simulación) (`probar_powershell.py`) |
| RF-22 | Si el comando solo consulta, debe rechazar la escritura a archivo (Out-File, Set-Content, Add-Content, Tee-Object, Export-*, `>`, `>>`) sin cortar la tarea; `2>&1` y `> $null` se permiten | 12 consultas que escriben, rechazadas; 9 casos legítimos, permitidos; en simulación el modelo corrige el comando solo | Verificado (simulación): 59/59 (`probar_powershell.py`) |
| RF-23 | Debe cortar el comando a los 30 s o con el atajo de emergencia | Proceso falso cortado a los 0,3 s de prueba | Verificado (simulación) |

### 3.4 Voz, confirmación por voz y palabra de activación

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-30 | Mantener Ctrl+Espacio debe grabar y soltar debe enviar | Atajo registrado con `RegisterHotKey`; la app al frente no lo recibe | Verificado (real) (`resultados_voz.md` §7) |
| RF-31 | Debe descartar pulsaciones con menos de 0,15 s de voz y transcripciones con más de 6 palabras por segundo de voz + 3 | Los 3 silencios o ruidos de la validación, frenados | Verificado (real) |
| RF-32 | Las acciones que cambian algo se confirman con Enter (sí) / Esc (no) físicos; sin respuesta en 30 s = no | `probar_voz.py` 11/11; "abre la calculadora" → Esc físico: no se abrió | Verificado (simulación y real, 2026-10-05; guía, Fase 7, "Estado real") |
| RF-33 | Solo se lee en voz alta la respuesta final, en 1–2 frases | Pensamiento y confirmaciones solo en consola | Verificado (real) |
| RF-34 | La frase "confirmo la instrucción", en una grabación aparte tras la pregunta, debe valer como sí; no valen "sí" solo, negaciones, palabras de más, una grabación casi sin voz, otra app sonando ni un Espacio inyectado | `probar_confirmacion_voz.py` 33/33; en vivo: con Ctrl+Espacio y con "Cacao, confirmo la instrucción" vale; "sí" solo no vale | Verificado (simulación y real, 2026-10-06; guía, "Pruebas presenciales") |
| RF-35 | Decir "Cacao" debe abrir una grabación (con 1,6 s de búfer previo, para "Cacao, sube el volumen" de corrido) que termina con un silencio o a los 30 s y pasa por los frenos de RF-31 | Detector `cacao_v4` (umbral 0,9): tu voz, tomas que no vio, **15/17** (el anterior 13/17); voces sintéticas que no vio, sola **46/54** y de corrido **81/108**; la grabación termina con bloques de cualquier tamaño (416 en el G435) | Verificado (simulación y real, 2026-10-06) (`resultados_cacao_v4.json`, `resultados_cacao_real_prueba_*.json`). "Cacao" dicho rápido: no detectado |
| RF-36 | Si Whisper no oye "Cacao" al principio de la grabación (primera palabra, o tras "oye/hola"), la activación debe descartarse sin guardar nada (segunda etapa) | `probar_palabra_activacion.py` 41/41; con videos reales, "Entonces el cacao se produce…" ya no pasa | Verificado (simulación y audio real) |
| RF-36a | Debe contarse por día cuántas activaciones pasan la primera etapa, la segunda y cuántas llegan como pedido, sin guardar audio ni texto | `contador_cacao.json`; en la prueba presencial 6 / 3 / 3 | Verificado (simulación y real) |
| RF-37 | El audio debe procesarse en memoria y no guardarse nada hasta detectar la palabra; la escucha se ignora mientras Cacao habla o con Ctrl+Espacio pulsado | `probar_palabra_activacion.py` 27/27 | Verificado (simulación) |
| RF-38 | La escucha debe encenderse y apagarse solo con un clic físico en la bandeja o en la isla, y seguir activa en modo juego (CPU) | Clic inyectado: no físico (`probar_fase7.py` C, 5/5); clic de Reizo en los interruptores de la isla y de la bandeja: físico (`prueba_presencial_isla.py`) | Verificado (simulación y real, 2026-10-06) |
| RF-39 | La palabra sola nunca debe confirmar una acción | `probar_palabra_activacion.py` (confirmación) | Verificado (simulación) |

### 3.5 Memoria, hábitos y wiki (Fase 6)

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-40 | `recordar` debe guardar sin duplicar; los alias y preferencias entran en el prompt de la sesión siguiente | Sesión 2: "abre el editor" → VS Code, 3/3 | Verificado (simulación) (`resultados_fase5.md` §3) |
| RF-41 | El registrador debe guardar cada 30 s la app, la categoría y el estado, **sin títulos**; las apps privadas y el incógnito, sin fila | 7 días simulados: 0 trampas en la base, 56/56 muestras privadas sin fila; en real, el incógnito de Chrome no deja fila y la ventana normal sí | Verificado (simulación y real, 2026-10-05) (`resultados_fase6.md`; guía, Fase 7, "Estado real") |
| RF-42 | Las muestras crudas deben borrarse a los 30 días; el resumen diario se conserva | Purga de 8 672 muestras con el resumen intacto | Verificado (simulación) |
| RF-43 | La reflexión diaria debe escribir perfil, hábitos, apps y rutinas con estructura y fechas puestas por el código | 4 páginas, estructura y frontmatter correctos, 3/3 semillas | Verificado (simulación con el modelo real): 24/24 (`resultados_reflexion.json`) |
| RF-44 | La reflexión no debe contradecir el texto de Reizo, revisando TODO su texto | Comprobación directa 7/7 con una nota de ~4 350 tokens en 2 trozos | Verificado (simulación con el modelo real) |
| RF-45 | La reflexión solo debe arrancar con ≥ 10 min sin teclado, mouse ni mando, sin pantalla completa, sin juego, sin audio bloqueante y con GPU < 20 %; y detenerse con actividad | 11/11 condiciones; guardia detiene en ~0,3–0,6 s. En real: Spotify no bloquea; YouTube en ventana no, en pantalla completa sí (a los 2 s); una llamada de Teams sí | Verificado (simulación y regla de audio en real). Mando: **Pendiente** |
| RF-46 | Las secciones editadas por Reizo no deben sobrescribirse; escribir se pospone si el archivo cambió hace < 5 min o está activo en Obsidian | Pruebas de wiki 22/22 | Verificado (simulación) |
| RF-47 | El lint semanal debe arreglar lo mecánico y anotar el resto en `revision.md` sin acusar al texto de Reizo | 11/11 | Verificado (simulación) |
| RF-48 | Las sugerencias deben ser solo texto: máximo 2 al día, apoyo ≥ 4 de 7 días en el inicio de uso, bloqueo permanente, desbloqueo por número, texto o casilla | 18/18 | Verificado (simulación) |
| RF-49a | La actividad (registro, reflexión) debe medirse solo con entrada física: teclado y mouse por Raw Input con dispositivo y mandos; la entrada inyectada y la deriva del mouse no cuentan; no se usa GetLastInputInfo salvo de respaldo | 10 min sin entrada física → "inactivo" aunque GetLastInputInfo diga 0 s; 1 200 eventos inyectados no reinician el contador (`probar_actividad_fisica.py` 29/29). En vivo: GetLastInputInfo 0,0 s frente a 8,0 s del contador físico | Verificado (simulación y lectura real) |
| RF-49b | Los periodos dudosos (`periodos_dudosos`: desde, hasta, motivo) deben quedar fuera del resumen diario, la actividad por hora y las sugerencias, sin borrar filas | `probar_actividad_fisica.py`; en real, marcado del 2026-10-05 21:33:30 al 2026-10-06 18:22:16 (2 017 filas) | Verificado (simulación); marcado aplicado |
| RF-49 | `consultar_memoria` debe devolver también las 1–2 secciones de la wiki más relacionadas (≤ 2 400 caracteres), nunca de `fuentes/` | "¿qué suelo hacer los lunes?" → consultar_memoria, 3/3 | Verificado (simulación) |

### 3.6 Control y modo juego

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-50 | El atajo `ctrl+alt+shift+q` debe cortar la tarea en curso, apagar el modo sin confirmación y dejar el agente detenido hasta "reanudar" | Corte y rechazo de tareas hasta reanudar | Verificado (real) (`resultados_fase5.md` §3); apagado del modo: verificado en código (`agente_minimo.atender`) |
| RF-51 | Con un juego ACTIVO debe descargar Gemma, la visión y Whisper, y recargarlos al terminar; un pedido en pausa recibe un aviso | Con Roblox: pausa en < 1 s (GPU de 14 GB a 1,4 GB) y recarga sola al cerrarlo (15 s) | Verificado (real) el 2026-10-05 (guía, Fase 7, "Estado real"); lógica: `probar_modo_juego.py` 28/28 |
| RF-52 | Detección por actividad: un proceso de juego (categoría "juegos" o carpeta de juegos; sin lanzadores, Wallpaper Engine ni Game Bar) cuenta como activo solo con una ventana visible o con la GPU ≥ 5 % en el 60 % de las muestras de 30 s; deja de contar tras 120 s sin esas señales. Entra y sale tras 2 comprobaciones seguidas cada 5 s | Un juego que quedó en la bandeja (Roblox al cerrarlo) no cuenta | Verificado (simulación y real, solo lectura) (`config.json` → `memoria_wiki.juegos`, `modo_juego`; `probar_modo_juego.py`) |
| RF-53 | "Estoy jugando" / "ya terminé" los atiende el código, sin el modelo, con el Whisper "base" en la CPU. Sin juego detectado, "estoy jugando" fuerza la pausa hasta "ya terminé"; con un juego ya detectado solo la confirma, y al cerrarlo recarga solo | Frases entendidas en 1,75 s; "ya terminé" recarga en 16 s | Verificado (real) el 2026-10-05 (guía, Fase 7, "Estado real"); `probar_modo_juego.py` 28/28 |
| RF-54 | Con un juego activo, nada (agente, pruebas ni mediciones) debe cargar modelos en la GPU: el agente espera; las pruebas terminan con un aviso | `guardia_juego.exigir_gpu_libre` en `modelo.crear_llm` y `TranscriptorWhisper` | Verificado en código |

### 3.7 Isla y confirmaciones con entrada física

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-60 | La isla debe mostrar el estado del agente (escuchando, pensando, trabajando, confirmación, pregunta, terminado, error, detenido, pausa por juego) y los indicadores de los modos | Mapa de estados de `diseno_fase7.md` §5 | Verificado (real) el 2026-10-05: "los estados se ven bien" (guía, Fase 7, "Estado real"). "Escuchando" y los indicadores de modo, posteriores: **Pendiente** |
| RF-61 | Las confirmaciones deben aceptar solo entrada física: Enter/Esc del teclado, Permitir/Denegar tras un clic físico en la isla o "confirmo la instrucción" (RF-34); teclas y clics inyectados se rechazan; sin respuesta en 30 s = no; gana la primera respuesta | `probar_fase7.py` A y B: 39/39; en real, Permitir y Denegar con clic físico y Enter funcionan | Verificado (simulación y real, 2026-10-05) |
| RF-62 | La isla no debe tomar el foco (`WS_EX_NOACTIVATE`, también tras alternar la transparencia de clics) | La terminal no perdió el foco al usar los botones | Verificado (real) |
| RF-63 | El agente no debe ver ni tocar la isla: fuera de `listar_ventanas`, tapada en `ver_pantalla`, sin clic de la herramienta mouse ni `enfocar`/`cerrar`/`listar_controles` sobre ella | `probar_fase7.py` B con la isla real | Verificado (simulación con la isla real). Grabarla con "Permitir capturas": **Pendiente** |
| RF-64 | Conexión solo en `127.0.0.1:8765`, con token por sesión en `%LOCALAPPDATA%\Asistente\ui.json` (borrado al salir), Origin de Tauri y una sola isla | Token incorrecto, Origin distinto y segunda isla rechazados (`probar_fase7.py` A) | Verificado (simulación) |
| RF-65 | La isla debe cerrarse con el agente aunque se cierre la terminal con la X o el proceso caiga (Job con `KILL_ON_JOB_CLOSE`) | Al cerrar la terminal con la X, la isla se cierra | Verificado (real) el 2026-10-05 (guía, "Corregido durante las pruebas") |
| RF-66 | La isla no debe hablar con internet: sin hooks de Claude Code, API, integraciones, claves ni red saliente; CSP con `connect-src` solo `ipc:` y el WebSocket local | Sin `reqwest`, `keyring` ni `tokio` | Verificado en código (`diseno_fase7.md` §8, decisión 2) |
| RF-67 | El campo de texto de la isla debe tomar el foco solo con un clic físico en él; con Enter o Esc debe devolverlo a la ventana que estaba activa antes, y con un clic fuera dejarlo en la ventana donde se hizo clic (si fue en la propia isla, en la de antes); fuera del campo, la isla mantiene WS_EX_NOACTIVATE y sus botones no quitan el foco | `foco.rs` 10/10 y `npm run probar-campo` 18/18; con Reizo: los cinco casos con el Bloc de notas, y se ve bien (`prueba_presencial_isla.py`) | Verificado (simulación y real, 2026-10-06) |
| RF-68 | El texto del campo debe entrar como un pedido normal (`atender_con_memoria`), con los mismos permisos, bloqueos, modo sin confirmación y confirmaciones que la consola y la voz; hasta 2000 caracteres | `probar_campo_isla.py`: mismo camino que la consola en modo texto y que lo dicho en modo voz; sin token, nada | Verificado (simulación) |
| RF-69 | La herramienta teclado debe negarse (bloqueo, sin pedir confirmación) a escribir o pulsar teclas si la ventana al frente es la isla | `probar_campo_isla.py`: bloqueo sin pulsaciones, en modo normal y sin confirmación | Verificado (simulación) |

### 3.8 Modo sin confirmación

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-70 | El modo debe cambiar solo con un clic físico en la bandeja o en la isla; empieza apagado en cada arranque y el atajo de emergencia lo apaga. Ninguna herramienta, frase ni voz puede cambiarlo | `probar_modo_directo.py` parte 6; clic inyectado: no cambia; con Reizo (2026-10-06): activado y desactivado con su clic; volumen, abrir y cerrar una app, escribir el texto del pedido, mover y deshacer, sin preguntar; PowerShell preguntó | Verificado (simulación y real) |
| RF-71 | Con el modo activo van directas: volumen, abrir_app, enfocar_ventana, buscar_web, cerrar_app normal y deshacer_movimiento | `probar_modo_directo.py` parte 1 | Verificado (simulación) |
| RF-72 | `mouse` y `teclado` van directos en cualquier ventana y en cualquier caso (decisión de Reizo del 2026-10-06), con una sola excepción: escribir un texto que no sale del pedido (con `escribir`, o letras sueltas con `tecla` o un atajo sin Ctrl ni Alt) cuando el modelo leyó contenido de fuera (web, archivo, pantalla, carpetas, PowerShell) en la tarea o en una tarea anterior que sigue en su historial: pregunta. `listar_ventanas` no cuenta: ningún título que controle una página llega al modelo (RF-79b) | Clic tras ver_pantalla, leer un archivo, buscar en la web o PowerShell, en la barra de tareas o en otra app: directo. Texto redactado sin leer nada de fuera, o que sale del pedido: directo. «Escribe un saludo en el Bloc de notas»: directo, también con Chrome abierto. "Contraseña: 1234" tras cualquiera de las 7 herramientas de lectura, o lo leído en la tarea anterior: pregunta. Ctrl+S, Alt+Tab y Enter tras leer contenido de fuera: directos | Verificado (simulación) (`probar_modo_directo.py` partes 2, 3 y 4, 138/138) |
| RF-73 | Los bloqueos de mouse y teclado se comprueban dentro de la propia herramienta, justo antes de actuar, así que valen aunque el modo deje pasar la acción: atajos (RF-78), clic o teclas en la isla (RF-63, RF-69) y ventanas sensibles (RF-79) | Con el modo activo, un clic en la isla y escribir con una ventana sensible al frente: bloqueados | Verificado (simulación) (`probar_modo_directo.py` partes 2 y 3) |
| RF-74 | `mover_archivo` va directo hasta 10 archivos por tarea, sin ejecutables ni scripts y fuera de `carpetas_importantes` (`datos_locales.json`) | 10 archivos directo, 11 preguntan; un `.exe` pregunta | Verificado (simulación) (`probar_modo_directo.py` parte 5) |
| RF-75 | `ejecutar_powershell` y `cerrar_app` forzado preguntan siempre | `probar_modo_directo.py` parte 1 | Verificado (simulación) |
| RF-76 | Si en la tarea entró contenido externo (leer_archivo, buscar_web, ejecutar_powershell), todo lo demás vuelve a preguntar hasta que termine (mouse y teclado siguen RF-72); tras ver_pantalla, listar_controles o listar_ventanas, enfocar_ventana, cerrar_app y abrir_app solo van directas sobre la app nombrada, y buscar_web y mover_archivo vuelven a preguntar | `probar_modo_directo.py` parte 1 | Verificado (simulación) |
| RF-77 | La isla debe mostrar un indicador ámbar mientras el modo está activo | Indicador visible al activar el modo con un clic físico | Verificado en código. A la vista: **Pendiente** |
| RF-79 | En cualquier modo, `teclado` debe negarse (bloqueo, sin pedir confirmación) a escribir o pulsar teclas si la ventana al frente es sensible: su título nombra contraseñas o claves (los 27 patrones que usa `ver_pantalla`) o es una app privada del registro de hábitos (gestores de contraseñas, Seguridad de Windows, `apps_banco`). Si no se puede comprobar, también se niega | KeePassXC y una app de banco: sensibles; el Bloc de notas no. "contraseñas.txt: Bloc de notas", "claves.kdbx - KeePass" y ".env - Visual Studio Code": sensibles | Verificado (simulación) (`probar_modo_directo.py` parte 2) |
| RF-79a | En cualquier modo (bloqueo, sin pedir confirmación): `teclado` no escribe ni pulsa teclas en el menú Inicio ni en la búsqueda de Windows (StartMenuExperienceHost, SearchHost; para abrir apps está `abrir_app`, que respeta los bloqueos), y ni `mouse` ni `teclado` actúan en Configuración (SystemSettings), el Panel de control (control.exe, sus subprogramas en rundll32, SystemProperties*, y el Explorador cuando muestra la carpeta del Panel de control) ni las consolas mmc. La barra de tareas sí se puede usar. Si no se puede mirar la ventana, se bloquea | Simulado: «regedit» y Enter en el Inicio y en la búsqueda, bloqueados (también con el modo activo, sin preguntar); el mouse ahí, no; clic, desplazar y escribir en las 5 ventanas de configuración, bloqueados; una carpeta normal del Explorador y la barra de tareas, permitidas | Verificado (simulación) (`probar_modo_directo.py` parte 4). Reconocer el Panel de control abierto en el Explorador: **Pendiente** en real |
| RF-79b | `listar_ventanas` y lo que devuelven mouse y teclado sobre la ventana al frente deben mostrar las ventanas de navegador (`memoria_wiki.navegadores`) solo con el nombre de la app («Google Chrome»), sin el título de la pestaña, que lo pone cada página web. Los títulos de las demás apps salen tal cual | Con Chrome abierto, `listar_ventanas` real: «Google Chrome» | Verificado (simulación y lectura real). Límite: el modelo ya no distingue pestañas ni ventanas de un mismo navegador por su título |
| RF-78 | En cualquier modo, `teclado` debe bloquear los atajos peligrosos: con la tecla Windows solo valen los de ventanas y escritorios (Win+D, Win+M, Win+Tab, Win+flechas, Win+Shift+S, Win+Ctrl+D/flechas/F4); bloqueados Win sola, Win+R/X/I/S/Q/E/A/U/K/P/N/B/T/V/H/L/G, Win+número, Win+Alt+R, Win+Ctrl+Enter, Win+Ctrl+O, Ctrl+Esc, Ctrl+Shift+Esc, Ctrl+Alt+Supr, Alt+F4 y el atajo de emergencia | `probar_modo_directo.py` parte 4 | Verificado (simulación) |

### 3.9 Nombre del asistente

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-80 | El asistente debe llamarse Cacao en el prompt, la consola, los mensajes de bloqueo, la wiki y la isla; los nombres internos (`%LOCALAPPDATA%\Asistente`, `asistente-ui.exe`, marcas `autor:asistente`) no cambian | Textos del commit ae8f33c | Verificado en código |
| RF-81 | Si un pedido empieza con "Cacao", el modelo debe entenderlo como su nombre y no como parte del pedido | Regla en `prompt_sistema`; en vivo, "Cacao, abre la calculadora" abrió la Calculadora | Verificado en código y en vivo (3 pedidos); no medido en el set de 65 frases |

### 3.10 autocompletar_login (en simulación, apagada)

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-90 | Debe actuar solo en la ventana de Chrome que está al frente y cuyo título es del sitio que Reizo nombró en el pedido (lo comprueba el código con el pedido, no con lo que diga el modelo; "github.com" vale para "GitHub", "git" no vale para "GitLab") | Otra app o Edge al frente, Chrome con otro sitio y sitio no nombrado: error o bloqueo | Verificado (simulación) (`probar_autocompletar_login.py` 46/46) |
| RF-91 | Debe hacer clic en el campo de usuario (el último campo de texto antes del primero de contraseña; sin contraseña, el único campo o el único con etiqueta de usuario) y elegir la primera cuenta de la lista de Chrome con flecha abajo + Enter, sin enviar el formulario | Buscador en la cabecera ignorado; campos ambiguos → error sin adivinar; lista que no aparece → error sin Enter | Verificado (simulación) |
| RF-92 | El modelo nunca debe recibir el usuario, la contraseña, el título, los campos ni las cuentas; la herramienta no lee el valor de ningún campo | Resultados solo con `ok`, `error`, `bloqueado` y `nota`; el módulo no usa ValuePattern ni lecturas de valor | Verificado (simulación y revisión de código) |
| RF-93 | Debe bloquearse si en la tarea entró contenido externo (leer_archivo, buscar_web, ejecutar_powershell) | 3/3 bloqueadas | Verificado (simulación) |
| RF-94 | Debe pedir confirmación siempre, también con el modo sin confirmación, y comprobar el plan antes de preguntar | Ejecutor del agente extraído con ast: pregunta con el modo activo; con plan fallido no pregunta | Verificado (simulación) |
| RF-95 | Debe volver a comprobar la ventana antes del clic y antes de elegir; si cambió, no actúa (o cierra la lista con Esc); el atajo de emergencia la corta | Ventana cambiada antes y con la lista abierta; emergencia antes del clic | Verificado (simulación) |
| RF-96 | La autorización de cada relleno debe ponerla Windows Hello de Chrome ("Usar Windows Hello al completar contraseñas") | Con Hello activado, Chrome pide huella, cara o PIN; al cancelar no rellena | **Pendiente** (en real, cuando Reizo lo active) |

### 3.11 Arranque automático (activado el 2026-10-06) y otros

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-97 | `iniciar_cacao.ps1` debe lanzar `voz.py` (agente con isla y palabra de activación) sin permisos de administrador, esperando 60 s con `-AlInicio` y con `ESPERAR_JUEGO=1` | Doble clic en `Cacao.lnk`: voz, isla y escucha; respondió a "Cacao" | Verificado (real, 2026-10-06) |
| RF-98 | No debe abrir un segundo Cacao si ya hay uno en marcha, y debe avisarlo de forma visible | Segundo doble clic: un solo Cacao y una ventanita de 4 s | Verificado (real) |
| RF-99 | El acceso directo debe crearse en `C:\asistente` y solo pasar a `shell:startup` con `crear_acceso_directo.ps1 -Inicio` (quitarlo con `-Quitar`) | `Cacao.lnk` en la carpeta de Inicio, con `-AlInicio` y ventana minimizada | **Activado** el 2026-10-06. Arranque al iniciar sesión: **Pendiente** |
| RF-100 | Tras cada atajo, tecla o clic, Cacao debe comprobar si tuvo efecto (ventana al frente, título, ventanas del proceso, foco, portapapeles; hasta 1,5 s) y, si no, decírselo al modelo y avisar en la isla; al terminar, decir qué falló y cómo se resolvió, o pedir ayuda | Ctrl+S en el Bloc de notas: aviso en la isla y en la respuesta (real) | Verificado (simulación y real) |
| RF-101 | La tabla `obstaculos` (memoria.db) debe guardar por app y acción el camino que funcionó (atajo o ruta de menú), escrita solo por el código, nunca con contenido externo en la tarea; la próxima vez se usa directo y entra en el prompt | Real: Bloc de notas, Ctrl+S → Ctrl+G, usado 3 veces; `probar_obstaculos.py` 35/35 | Verificado (simulación y real). Límite: guardar algo sin cambios no deja efecto visible |
| RF-102 | Cada pedido debe llevar la fecha y la hora actuales | `[Ahora: martes 6 de octubre de 2026, 21:50]` | Verificado (simulación) |

### 3.12 Isla: tamaño, cierre automático y escucha de seguimiento

| ID | Requisito | Criterio | Estado |
|---|---|---|---|
| RF-103 | La isla debe escalarse según el monitor: tamaño de Ajustes (pequeño 0,70, mediano 0,80 por defecto, grande 0,92) × resolución física respecto a 1920×1080 (el lado más corto) ÷ √escalado de Windows, entre 0,55 y 2,5. La ventana, los clics (Rust) y la zona que el mouse del agente no puede tocar siguen esa escala | En 1920×1080 al 100 %, abierta 448×112 / 512×128 / 589×147 px (antes 640×160); Ajustes con la fila «Tamaño» | Verificado (simulación: navegador con el servidor de desarrollo y `cargo check`). A la vista: **Pendiente** |
| RF-104 | Tras una respuesta, la isla debe quedarse abierta mientras Cacao habla y 4 a 10 s más según el largo del texto (18 caracteres por segundo), y volver al notch pequeño sin pulsar OK; con el mouse encima no se esconde (lo hace 1,5 s después de que sale); las confirmaciones y el campo en uso nunca se esconden solos; el cierre dura 180 ms | Navegador, mensajes simulados: sin voz cerrada a los 4 s; con voz abierta hasta `fin_habla` y 4 s más; mouse encima, abierta, y cerrada 1,5 s tras salir; confirmación, abierta | Verificado (simulación). A la vista: **Pendiente** |
| RF-105 | Tras cada respuesta hablada, Cacao debe seguir oyendo 8 s sin la palabra «Cacao», con un indicador que cuenta atrás en la isla; si Reizo habla (120 ms seguidos de voz), se graba hasta un silencio y entra como pedido normal con los mismos frenos y confirmaciones; si no, termina. No se abre con otra app sonando, ni con la escucha de «Cacao» apagada, en modo juego o detenido; si otra app suena antes de hablar se cierra, y si suena mientras graba no vale. Se enciende y apaga con un clic físico en Ajustes (modo «seguimiento»; empieza según `voz.seguimiento.activa_al_iniciar`) | `probar_seguimiento.py` 35/35 (audio sintético y reloj falso; voz.py extraído con ast) | Verificado (simulación). Con tu voz: **Pendiente** |
| RF-106 | El ticker de la isla no debe encimar el paso anterior con el actual, y debe seguir avanzando pasados 20 pasos | «cerrar_app: Cerré la ventana…» y «Te escucho…» en líneas separadas; 25 pasos | Verificado (simulación: navegador) |

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
| RNF-08 | Modo juego: liberar la VRAM en ≤ 1 s y volver en ≤ 20 s | Simulado: descarga de Gemma + visión **0,19–0,20 s** (12 971 → 1 227 MB), Whisper **0,01 s**; recarga **~12,6 s** en total, más ~10 s de comprobaciones. Real con Roblox: pausa **< 1 s** (14 GB → 1,4 GB), recarga **15 s** | `resultados_modo_juego_gemma.json`, `resultados_modo_juego_whisper.json`; guía, Fase 7, "Estado real" |
| RNF-09 | "Estoy jugando" / "ya terminé" en pausa ≤ 3 s | **1,75 s** con el Whisper de la CPU | guía, Fase 7, "Estado real" |

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
| RNF-23 | Palabra de activación: detección con voces no vistas | Umbral 0,9: sola **37/54**, de corrido con la orden **77/108**. "Oye, Cacao" con el mismo método: **24–32/54** | `resultados_cacao_instalado.json`, `resultados_oye_cacao.json` |
| RNF-24 | Palabra de activación: activaciones falsas antes de la segunda etapa | **0** en 7,9 min de conversación, **0/20** frases que mencionan "cacao", **0** en 15 min de ruido y música, **0** en 30 grabaciones de Reizo (2,3 min); **10,84 por hora** (116 en 10,7 h) en la validación de openWakeWord. "Oye, Cacao": 2,8 por hora con el umbral más alto | `resultados_cacao_instalado.json`, `resultados_oye_cacao.json` |
| RNF-25 | Activaciones falsas que llegan al agente tras la segunda etapa; latencia y uso de CPU de la escucha | **No medido** (la segunda etapa necesita Whisper en la GPU) | — |

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

**Medido otra vez el 2026-10-06** con el prompt actual (nombre "Cacao", `deshacer_movimiento`): 195/195 (100 %)
en primera herramienta y tarea completa, JSON 100 %, frase 58 3/3, **3,71 s** de media (`resultados_pruebas_65_cacao.json`).
Con los atajos comprobados, el aviso de idioma y la fecha en cada pedido: primera herramienta 195/195, tarea completa
193/195 (frase 44: en la simulación la terminal ya está al frente), frase 56 con `listar_ventanas` aceptado como
primer paso, **3,91 s** de media (`resultados_pruebas_65_fecha.json`).

### 4.5 Fiabilidad y mantenimiento

| ID | Requisito | Situación |
|---|---|---|
| RNF-30 | Los errores de llama.cpp/CUDA deben quedar registrados | `modelo.py` los muestra y los guarda en `errores_llama.log` (`resultados_voz.md`, incidencias) |
| RNF-31 | La reflexión, el lint y el modo juego nunca deben tumbar al agente | Capturan sus excepciones, las anotan y reintentan más tarde (código) |
| RNF-32 | Las pruebas no deben tocar datos reales | Bases y vault temporales (`*_prueba*`), borrados al terminar; `probar_voz.py` usa un micrófono falso |
| RNF-33 | Cada fase tiene su script de pruebas | `evaluar_pruebas.py`, `probar_fase6.py` (142/142), `probar_powershell.py` (59/59), `probar_modo_juego.py` (28/28), `probar_voz.py` (11/11), `probar_fase7.py` (A+B 39/39, C 5/5), `probar_modo_directo.py` (138/138), `probar_confirmacion_voz.py` (33/33), `probar_palabra_activacion.py` (41/41), `probar_seguimiento.py` (35/35) |
| RNF-34 | Ctrl+C debe cerrar el modo voz y un comando en pausa no debe tumbarlo | Corregido y verificado en real el 2026-10-05 (guía, "Corregido durante las pruebas") |

---

## 5. Requisitos de seguridad y privacidad

| ID | Requisito | Mecanismo | Estado |
|---|---|---|---|
| RS-01 | Ninguna acción con efecto se ejecuta sin un sí explícito, salvo las del modo sin confirmación (RS-14) | Permiso "confirmar" en 6 herramientas; en voz, toda acción no de solo lectura | Verificado (real) |
| RS-02 | Las acciones prohibidas no deben existir como herramienta (borrar, registro, configuración del sistema, instalar, apagar) | `acciones_prohibidas` y 42 patrones de PowerShell | Verificado (simulación) |
| RS-03 | Un bloqueo debe cortar la tarea sin dar al modelo otro camino | `bloqueado: true` → `terminar()` y registro en `bloqueos` | Verificado (simulación y real): "abre regedit", 1 paso |
| RS-04 | Las apps del sistema sensibles no se abren; las consolas piden confirmación | 9 ejecutables + 5 AppID bloqueados; 5 ejecutables + 24 AppID con confirmación | Verificado (simulación) |
| RS-05 | Los archivos de contraseñas y claves no se listan, leen, mueven ni nombran en PowerShell | 27 patrones sensibles, aplicados a la ruta entera | Verificado (real): el CSV de contraseñas de Descargas no aparece ni se lee (`resultados_fase5.md`) |
| RS-06 | `ver_pantalla` no captura ventanas sensibles | Rechaza la captura si la ventana activa es sensible; tapa en negro las demás | Verificado (real) |
| RS-07 | El contenido externo no debe poder guardar memorias ni tocar sugerencias | Tarea "contaminada" → `recordar`/`sugerencias`/`registro_habitos` piden confirmación; el origen lo pone el ejecutor | Verificado (simulación) |
| RS-08 | La wiki solo se alimenta de lo que dice Reizo, `recordar` y el registro de hábitos; nunca de `fuentes/` ni de salidas de herramientas | Exclusión por ruta; filtro sensible, de secretos y de apps privadas antes de escribir | Verificado (simulación) |
| RS-09 | El registro de hábitos no guarda títulos; privados e incógnito sin fila | Sin columna de título; título del navegador leído en memoria solo para detectar el incógnito | Verificado (simulación y real: incógnito de Chrome) |
| RS-10 | Las consultas de PowerShell no escriben archivos | RF-22 | Verificado (simulación) |
| RS-11 | Los datos personales no van al repositorio | `.gitignore`: `memoria.db`, `habitos.db`, `memoria/`, `datos_locales.json`, `historial_movimientos.json`, resultados y audios. La wiki tiene un git local sin remoto | Verificado (revisión del historial en la Fase 5) |
| RS-12 | Atajo de emergencia siempre disponible | RF-50 | Verificado (real) |
| RS-13 | El agente no puede aprobar sus propias acciones | Confirmaciones solo con entrada física (RF-61); la herramienta mouse no hace clic en la isla (RF-63) | Verificado (simulación y real) |
| RS-14 | El modo sin confirmación solo lo enciende Reizo; cubre acciones acotadas y reversibles, y mouse y teclado en cualquier ventana salvo un texto que puede venir de contenido de fuera | RF-70 a RF-76 y RF-79; los bloqueos siguen igual en cualquier modo | Verificado (simulación) |
| RS-15 | Ni la palabra de activación ni una frase cualquiera confirman: solo "confirmo la instrucción" en su propia grabación, con voz real y sin otro audio | RF-34, RF-39 | Verificado (simulación) |
| RS-16 | Privacidad de la escucha: nada se guarda hasta detectar "Cacao" o, en los 8 s de la escucha de seguimiento, hasta que lo que se dice pasa los frenos como pedido; las activaciones falsas y lo oído en el seguimiento que no es pedido no se guardan; `voz_registro/` no va a git | RF-36, RF-37, RF-105; `.gitignore` | Verificado (simulación) |
| RS-17 | La isla no tiene red saliente ni acepta conexiones de otras páginas o procesos sin el token | RF-64, RF-66 | Verificado (simulación) |
| RS-18 | Ninguna herramienta entrega usuarios ni contraseñas al modelo; el autocompletado lo autoriza Windows Hello | RF-90 a RF-96 | Verificado (simulación); Windows Hello: Pendiente |
| RS-19 | El agente no puede dictarse pedidos por la isla: su campo solo se abre con un clic físico y teclado no escribe en ella | RF-67, RF-69 | Verificado (simulación) |

**Límite reconocido:** los patrones son una red de seguridad, no un sandbox. La barrera principal es la confirmación
(`herramientas_powershell.py`), y la confirmación supone que quien está frente al PC es Reizo (R-16).

---

## 6. Interfaces

### 6.1 Usuario

- **Consola** (`agente_minimo.py`): pedidos por texto, confirmación con Enter/Esc físicos y "reanudar".
- **Voz** (`voz.py`):
  - Ctrl+Espacio para hablar o la palabra "Cacao";
  - confirmación con Enter/Esc, los botones de la isla o "confirmo la instrucción";
  - respuesta con Piper.
- **Isla** (`C:\asistente-ui`):
  - estados del agente con Mochi;
  - confirmaciones con Permitir/Denegar (solo clics físicos);
  - interruptores de "escucha" y del modo sin confirmación, con su indicador;
  - icono de bandeja con los mismos interruptores y "Permitir capturas (para grabar la isla)".
- **Obsidian**:
  - lectura y edición de la wiki;
  - notas en "Notas de Reizo" o `mis_notas/`;
  - casillas de desbloqueo en `rutinas.md`.

### 6.2 Software

| Interfaz | Detalle |
|---|---|
| Modelo | llama-cpp-python (CUDA) con `LlamaRapida`; JSON por gramática; visión por mtmd + mmproj |
| Windows | Win32 (pywin32/ctypes), UI Automation (pywinauto), pycaw (audio), `Get-StartApps` (PowerShell), `RegisterHotKey`, hooks de bajo nivel de teclado y mouse, Job objects, XInput y Raw Input (mandos) |
| Voz | faster-whisper (CTranslate2), Piper, sounddevice, openWakeWord (características) + scikit-learn (clasificador) |
| Isla | WebSocket local (`websockets` en Python, cliente en el webview), mensajes de `diseno_fase7.md` §4 |
| Datos | SQLite (`memoria.db`, `habitos.db` en WAL), Markdown en el vault, git |
| Configuración | `config.json` (modelo, voz, palabra_activacion, memoria_wiki, modo_juego, ui), `herramientas.json` (catálogo, permisos y límites), `wiki_esquema.json`, `datos_locales.json` (`apps_banco`, `carpetas_importantes`) |

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
| CU-07 Orden por voz | Ctrl+Espacio | Graba → frenos → Whisper → agente → Piper | Silencio o texto inventado → descartado; acción → confirmación |
| CU-08 Emergencia | `ctrl+alt+shift+q` | Corta la tarea, apaga el modo sin confirmación y queda detenido | "reanudar" lo desbloquea |
| CU-09 Recordar | "cuando digo el editor me refiero a VS Code" | `recordar{alias}` → en el prompt desde la sesión siguiente | Tras contenido externo → pide confirmación |
| CU-10 Reflexión diaria | Planificador (día cerrado, PC inactivo) | Datos del código → frases del modelo → comprobación → escritura → índice → commit | Actividad, juego, audio o pantalla completa → se detiene y sigue después |
| CU-11 Sugerencia | Reizo habla a la hora de una rutina | "A esta hora (09:00) sueles abrir Spotify. ¿Lo abro?" | "no me sugieras eso" → bloqueada; listar o desbloquear |
| CU-12 Modo juego | Un juego pasa a estar activo | Descarga Gemma, la visión y Whisper → pausa | Pedido en pausa → aviso; "ya terminé" o 2 min sin señales → recarga |
| CU-13 Palabra de activación | Reizo: "Cacao, sube el volumen" | Detección en la CPU → isla "escuchando" → grabación hasta el silencio → frenos → Whisper → segunda etapa → agente | Sin "Cacao" al principio → descartado sin guardar; escucha apagada → solo Ctrl+Espacio |
| CU-14 Confirmar por voz | El agente pregunta por una acción | Reizo pulsa Ctrl+Espacio o dice "Cacao" y luego "confirmo la instrucción" → sí | "Sí" solo, otra app sonando, casi sin voz o Espacio inyectado → no vale; Esc o Denegar → no |
| CU-15 Modo sin confirmación | Clic físico de Reizo en la isla o la bandeja | Indicador ámbar; volumen, abrir_app… van directos; mouse/teclado solo en la app nombrada | Contenido externo, PowerShell o cerrar forzado → pregunta; clic inyectado → no cambia; emergencia → se apaga |
| CU-16 Iniciar sesión | "inicia sesión en GitHub" (con la función activada) | `listar_ventanas` → `enfocar_ventana` → `autocompletar_login{sitio: github}` → confirmación → clic en el usuario, primera cuenta → Windows Hello → "Listo, no envié el formulario" | Otro sitio al frente o sin cuentas → error; contenido externo en la tarea → bloqueo; Hello cancelado → no rellena |
| CU-17 Arranque | Reizo inicia sesión en Windows (con el acceso en Inicio) | 60 s → `voz.py` → isla y escucha | Ya en marcha → no abre otro; juego activo → espera para cargar la GPU |

---

## 8. Riesgos

| ID | Riesgo | Probabilidad / impacto | Mitigación actual | Pendiente |
|---|---|---|---|---|
| R-01 | Inyección de instrucciones desde archivos, web, pantalla o títulos | Media / alto | Confirmación de acciones, bloqueos, tarea contaminada (RS-07), la wiki excluye `fuentes/`; en el modo sin confirmación, el contenido externo devuelve todo a preguntar (RF-76) | Revisar con contenido real |
| R-02 | El modelo elige mal o da pasos de más (p. ej. frase 58) | Baja / medio | Set de 65 frases con 3 semillas por cada cambio | Volver a pasar el set tras el nombre "Cacao" (§4.4) |
| R-03 | VRAM insuficiente con juegos u otras apps | Media / alto | Modo juego (RF-51), probado con Roblox en real: de 14 GB a 1,4 GB; un juego en la bandeja ya no cuenta (RF-52) | Probar con un juego que no tenga ventana visible (solo GPU) |
| R-04 | El sistema se queda sin memoria comprometida (~16,2 GB con voz); Claude Code cortó procesos | Media / medio | `use_mmap` false; lanzar `voz.py` desde una terminal propia | — |
| R-05 | Error de CUDA intermitente (una vez al arrancar `voz.py`) | Baja / medio | Registro en `errores_llama.log` | Reproducir si vuelve |
| R-06 | Actualizar llama-cpp-python rompe `LlamaRapida` (método interno) | Media / alto | `requirements.txt` fija 0.3.36; `modo_gramatica: null` como vuelta atrás | Volver a medir al actualizar |
| R-07 | Windows de la rama Insider (26300): cambios de API o comportamiento | Media / medio | — | Volver a probar tras cada actualización grande |
| R-08 | Los patrones de PowerShell no son un sandbox (alias raros, ofuscación) | Media / alto | La confirmación es la barrera principal; `-enc`, `iex` e `Invoke-Expression` bloqueados; PowerShell pregunta siempre, también en el modo sin confirmación | — |
| R-09 | Algo reinicia la inactividad sin que nadie use el PC y la reflexión no arranca | Media / bajo | Diagnóstico del 2026-10-06: GetLastInputInfo se reiniciaba sin ninguna entrada (ni física ni inyectada). Ahora se mide con entrada física por Raw Input, sin deriva del mouse (RF-49a) | Ver en real que salga "inactivo"; qué reiniciaba GetLastInputInfo (`powercfg /requests`, administrador); revisar con un mando |
| R-10 | Whisper inventa texto en silencio o ruido | Alta sin frenos / alto | Frenos de silencio, palabras/s y frases de subtítulos; la frase de confirmación no vale casi sin voz | — |
| R-11 | Choque entre ediciones en Obsidian y escritura del agente | Baja / medio | Hash por sección, posponer 5 min, pestaña activa, escritura atómica | Probar en real |
| R-12 | Privacidad del registro de hábitos | Media / alto | Sin títulos, privados sin fila, purga a 30 días, base fuera de git | Lista de apps de banco (`apps_banco` vacío en este PC) |
| R-13 | Licencia de los assets de Coucou (isla) | Baja / medio | Uso personal y local, repositorio sin remoto | Cambiar nombre, personaje y sonidos si algún día se comparte |
| R-14 | Falsos positivos de la palabra de activación: Cacao empieza a grabar sin que Reizo lo llame | Media / bajo | `cacao_v4`, umbral 0,9 y paciencia 2: 16,7 por hora en el audio general de openWakeWord, filtradas por la segunda etapa (más estricta desde el 2026-10-06); nada se guarda; las acciones con efecto siguen pidiendo confirmación física | Ver `contador_cacao.json` tras unos días |
| R-15 | Audio de videos, series, streams o llamadas que digan "Cacao, …" (o "confirmo la instrucción") | Media / medio | Probado con 4 min de videos sobre cacao: 2 activaciones en la primera etapa; la frase "Entonces el cacao…" pasaba la segunda etapa y se corrigió. La confirmación por voz no vale con otra app sonando (RF-34) | Apagar la escucha al ver videos si molesta |
| R-16 | Otra persona usa el PC: Cacao obedece a cualquier voz, y quien esté frente al teclado puede confirmar con Enter o un clic | Media / alto | El modo sin confirmación empieza apagado y la emergencia lo apaga; la escucha se apaga con un clic en la bandeja; los bloqueos valen para todos; el registro de hábitos atribuye a Reizo lo que haga otro | Sin reconocimiento de quién habla (fuera de alcance). Costumbre: apagar la escucha y el modo antes de prestar el PC |
| R-17 | El modo sin confirmación queda encendido y olvidado | Media / medio | Empieza apagado en cada arranque; indicador ámbar en la isla; emergencia lo apaga | Valorar que se apague solo tras un tiempo sin uso |
| R-18 | La isla deja de mostrarse o no conecta y Reizo no ve una confirmación | Baja / bajo | Enter/Esc físicos en la consola siguen valiendo; sin respuesta en 30 s = no | — |
| R-19 | Un arranque automático del agente le quita la GPU a un juego o carga sin que Reizo esté | Baja / medio | El agente espera a que el juego se cierre antes de cargar (RF-54) | Activarlo solo con Reizo presente (§3.11) |
| R-20 | `autocompletar_login` sin Windows Hello activado en Chrome: el relleno solo depende de la confirmación de Cacao, que puede dar cualquiera frente al PC (R-16) | Media / alto | Apagada por defecto; sitio del pedido, Chrome al frente, sin contenido externo, confirmación siempre; no envía el formulario | Activar Hello antes que la función (guía, Fase 7 punto 13) |
| R-22 | Con el modo sin confirmación activo, mouse y teclado actúan en cualquier ventana sin preguntar: un error del modelo, o contenido de fuera que lo empuje a hacer clics, cambia cosas sin que Reizo lo apruebe | Media / medio | Empieza apagado y solo lo enciende un clic físico; indicador ámbar; emergencia lo apaga; un texto que no sale del pedido tras leer contenido de fuera pregunta; bloqueos en cualquier modo: atajos, isla, ventanas sensibles, escribir en el Inicio o la búsqueda, y Configuración y el Panel de control (RF-79a); PowerShell y cerrar a la fuerza siguen preguntando | Probar en real el Panel de control abierto en el Explorador |
| R-23 | La escucha de seguimiento toma como pedido lo que se dice en la sala justo después de una respuesta (otra persona, una conversación, la tele sin sonar por el PC) | Media / medio | Solo 8 s tras una respuesta; no con otra app sonando por el PC; mismos frenos de Whisper; las acciones con efecto siguen pidiendo confirmación (salvo el modo sin confirmación); se apaga en Ajustes | Ver en `contador_cacao.json` («seguimiento») cuántos pedidos llegan así |
| R-21 | Página con varios campos o una lista de Chrome distinta de la esperada: el clic cae en otro campo o se elige otra opción | Baja / medio | Sin un único campo claro da error; si la lista no se abre no pulsa Enter; si sigue abierta tras Enter, error | Probar en 2-3 sitios reales |

---

## 9. Trazabilidad y pendientes

- **Requisitos → pruebas:**
  - RF-01..08 y RNF-21 → `evaluar_pruebas.py` y `pruebas.json` (65 frases);
  - RF-18 y RF-70..78 → `probar_modo_directo.py`;
  - RF-20..23 → `probar_powershell.py`;
  - RF-30..33 → `probar_voz.py`, `validar_transcripcion.py`;
  - RF-34 → `probar_confirmacion_voz.py`;
  - RF-35..39 y RNF-23/24 → `probar_palabra_activacion.py`, `entrenar_cacao.py`;
  - RF-40..49 → `probar_fase6.py`, `probar_reflexion.py`; RF-49a/b → `probar_actividad_fisica.py`;
  - RF-50 → `probar_emergencia.py`, `prueba_real.py 3`;
  - RF-51..53 y RNF-08 → `probar_modo_juego.py`;
  - RF-60..66 → `probar_fase7.py` (A, B y C);
  - RF-67..69 → `foco.rs` y `npm run probar-campo` (en `C:\asistente-ui\windows`), `probar_campo_isla.py`;
  - RF-90..95 → `probar_autocompletar_login.py`;
  - RF-97..98 → `iniciar_cacao.ps1 -Simular`;
  - RF-103, RF-104 y RF-106 → la isla con `npm run dev` y `window.cacao` (mensajes simulados);
  - RF-105 → `probar_seguimiento.py`.
- **Probado en real el 2026-10-05:** rechazo con Esc en voz; Whisper de la CPU con "estoy jugando" y "ya terminé";
  isla con clic físico en Permitir/Denegar y Enter, sin quitar el foco; modo juego con Roblox; incógnito en Chrome;
  regla de audio (música, video en ventana y en pantalla completa, llamada); registro de hábitos al arrancar.
- **Probado en simulación el 2026-10-06:** modo sin confirmación (73/73), confirmación por voz (33/33), palabra
  "Cacao" (27/27 y las mediciones de RNF-23/24), clic inyectado en el interruptor de la isla real (5/5).
- **Probado en simulación el 2026-10-06 (tarde):** `autocompletar_login` (46/46) y el arranque (`-Simular`, instancia
  única).
- **Pendientes en real** (orden y detalle en la guía, Fase 7, "Pendiente para cuando estés frente al PC"):
  - los interruptores con tu clic; "Cacao" y "confirmo la instrucción" con tu voz; videos que digan "cacao";
  - el modo sin confirmación con acciones reales;
  - `autocompletar_login` con Windows Hello (RF-96);
  - el arranque al iniciar sesión (RF-99);
  - el campo de texto de la isla a la vista (RF-67);
  - grabar la isla con "Permitir capturas"; actividad con un mando;
  - registro de hábitos durante una semana (reflexión y sugerencias con datos reales) y Obsidian.
- **Pendientes de medición:** el set de 65 frases con el prompt actual (§4.4); activaciones falsas tras la segunda
  etapa, latencia y CPU de la escucha (RNF-25).
