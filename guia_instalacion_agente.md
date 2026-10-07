# Guía de instalación: asistente de escritorio con Gemma 4 12B

Guía paso a paso para dejar el agente funcionando en tu PC con Windows (Ryzen 5 3500X, 16 GB DDR4, RTX 5060 Ti 16 GB). Está dividida en fases con un **punto de control** al final de cada una: no pases a la siguiente hasta que el punto de control funcione.

Archivos que acompañan esta guía:

- `herramientas.json`: catálogo de herramientas y permisos.
- `agente_minimo.py`: primer agente funcional (Fase 3).

---

## Fase 0. Preparación

### 0.1 Espacio en disco

Necesitas unos **25–30 GB libres en el NVMe** para todo el proceso:

| Componente | Espacio aproximado |
|---|---|
| Visual Studio Build Tools (C++) | 6–8 GB |
| CUDA Toolkit | 4–6 GB |
| Modelo Gemma 4 12B (Q5_K_M) | 9–10 GB |
| Python, librerías y caché de compilación | 2–3 GB |

Con tus 68 GB libres alcanza, pero conviene limpiar antes: Liberador de espacio de Windows (incluyendo "archivos del sistema") y la carpeta `%TEMP%`.

### 0.2 Driver de NVIDIA

La RTX 5060 Ti (arquitectura Blackwell) necesita un driver reciente compatible con **CUDA 12.8 o superior** (rama 570 o posterior).

1. Actualiza el driver desde la app de NVIDIA o desde nvidia.com.
2. Abre PowerShell y ejecuta:

```powershell
nvidia-smi
```

**Punto de control:** aparece tu GPU con 16 GB y, arriba a la derecha, una "CUDA Version" de 12.8 o mayor.

---

## Fase 1. Entorno de desarrollo

El orden importa: instala Visual Studio **antes** que CUDA, para que CUDA se integre con el compilador.

### 1.1 Python

1. Descarga **Python 3.11 o 3.12** desde python.org. El proyecto funciona con **Python 3.11.9** (la versión del `.venv` actual, con la que se probó todo); no hace falta 3.12. Evita la versión más nueva si salió hace poco, porque muchas librerías tardan en tener binarios para ella.
2. En el instalador marca **"Add python.exe to PATH"**.
3. Instala también **Git** desde git-scm.com.

```powershell
python --version
git --version
```

### 1.2 Visual Studio Build Tools

1. Descarga "Build Tools for Visual Studio 2022" desde visualstudio.microsoft.com.
2. Marca solo la carga de trabajo **"Desarrollo para el escritorio con C++"**.
3. Instala y reinicia.

### 1.3 CUDA Toolkit

1. Descarga el **CUDA Toolkit 12.8 o superior** desde developer.nvidia.com.
2. Elige instalación personalizada y desmarca el driver si ya tienes uno más nuevo (para no degradarlo).
3. Reinicia.

```powershell
nvcc --version
```

**Punto de control:** `python`, `git` y `nvcc` responden con su versión.

---

## Fase 2. Proyecto y modelo

### 2.1 Estructura del proyecto

```powershell
mkdir C:\asistente
cd C:\asistente
mkdir modelos
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Si PowerShell bloquea el script de activación, ejecuta una sola vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Copia `herramientas.json` y `agente_minimo.py` dentro de `C:\asistente`.

### 2.2 Compilar llama-cpp-python con CUDA

Este es el paso más largo (10–30 minutos). Cierra el navegador y otras apps pesadas, porque la compilación usa bastante RAM.

```powershell
$env:CMAKE_ARGS = "-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=120"
$env:FORCE_CMAKE = "1"
pip install llama-cpp-python --no-cache-dir --force-reinstall --verbose
```

`CMAKE_CUDA_ARCHITECTURES=120` corresponde a las GPU Blackwell de consumo como la tuya; compilar solo para esa arquitectura reduce el tiempo de compilación.

Si al cargar el modelo más adelante aparece un error de arquitectura desconocida (`unknown model architecture`), significa que la versión publicada todavía no soporta Gemma 4. En ese caso instala desde el repositorio, que trae el llama.cpp más reciente:

```powershell
pip install "git+https://github.com/abetlen/llama-cpp-python.git" --no-cache-dir --force-reinstall --verbose
```

### 2.3 Resto de dependencias

```powershell
pip install huggingface_hub rapidfuzz pycaw comtypes psutil pywin32 pyautogui mss pillow
```

### 2.4 Descargar el modelo

1. En huggingface.co busca **"gemma-4-12b-it GGUF"**. Prefiere el repositorio oficial de Google si publica GGUF; si no, uno de los cuantizadores conocidos de la comunidad.
2. Elige el archivo **Q5_K_M** (unos 9 GB). Es el mejor equilibrio entre calidad y VRAM para tus 16 GB.
3. Descárgalo en la carpeta `modelos` (reemplaza `<repo>` y `<archivo>` por los nombres reales):

```powershell
huggingface-cli download <repo> <archivo>.gguf --local-dir modelos
```

Si el repositorio pide aceptar la licencia, inicia sesión antes con `huggingface-cli login`.

### 2.5 Prueba de humo

Crea `prueba.py`:

```python
from llama_cpp import Llama
from pathlib import Path

modelo = next(Path("modelos").glob("*.gguf"))
llm = Llama(model_path=str(modelo), n_gpu_layers=-1, n_ctx=8192, verbose=True)
r = llm.create_chat_completion(messages=[{"role": "user", "content": "Hola, preséntate en una frase."}])
print(r["choices"][0]["message"]["content"])
```

```powershell
python prueba.py
```

**Punto de control:**

- En el log aparece algo como `offloaded 49/49 layers to GPU` (todas las capas en la GPU).
- La respuesta llega en pocos segundos.
- En otra ventana, `nvidia-smi` muestra unos 10–12 GB de VRAM usados mientras corre.

Si dice que usó 0 capas en GPU, llama-cpp-python se compiló sin CUDA: revisa la sección de problemas comunes.

---

## Fase 3. Primer agente funcional

`agente_minimo.py` implementa el loop agéntico completo con 4 herramientas: `listar_apps`, `abrir_app`, `volumen` y `finalizar`.

Cómo funciona:

- **Detección de apps sin registro:** usa `Get-StartApps` de PowerShell, que lista todo lo que aparece en el Menú Inicio (apps de escritorio y de la Tienda). Para abrir usa `explorer.exe shell:AppsFolder\<id>`, que funciona con ambos tipos. Cualquier app que instales aparece sola.
- **Búsqueda aproximada:** con rapidfuzz, "abre el de fotos" encuentra "Fotos". Si hay empate, devuelve opciones en vez de adivinar.
- **Salida estructurada:** el modelo está forzado por gramática a responder siempre un JSON válido con `pensamiento`, `herramienta` y `argumentos`.
- **Permisos:** las herramientas con `"permiso": "confirmar"` piden tu sí en la consola antes de ejecutarse.

```powershell
python agente_minimo.py
```

Prueba con frases como:

- "sube el volumen un poco"
- "pon el volumen al 30"
- "abre la calculadora"
- "¿qué apps de música tengo?"
- "hola, ¿cómo estás?" (debería responder conversando, sin usar herramientas)

**Punto de control:** las cinco frases funcionan y en consola ves el `pensamiento` de cada paso.

---

## Fase 4. Set de pruebas

Antes de agregar más herramientas, crea `pruebas.json` con 30–50 frases y la herramienta esperada para cada una:

```json
[
  { "frase": "baja el volumen", "esperado": "volumen" },
  { "frase": "abre spotify", "esperado": "abrir_app" },
  { "frase": "qué es una API", "esperado": "finalizar" }
]
```

Mezcla frases directas, frases ambiguas y conversación. Escribe un script que pase cada frase por `pedir_accion` y cuente aciertos. Este número es tu criterio de aceptación del SRS (por ejemplo, ≥ 90%) y te sirve para comparar cambios en el prompt o en el modelo.

**Punto de control:** tienes un porcentaje de acierto medido.

---

## Fase 5. Resto de herramientas

Implementa las demás herramientas de `herramientas.json` en este orden, que va de menor a mayor riesgo. Después de cada grupo, vuelve a correr el set de pruebas.

1. **Lectura:** `listar_ventanas`, `enfocar_ventana`, `listar_carpeta`, `leer_archivo`, `buscar_web` (con pywin32, psutil y `webbrowser`).
2. **Visión:** `ver_pantalla` (captura con mss y envío de la imagen al modelo). Revisa antes que tu versión de llama-cpp-python soporte imágenes con Gemma 4.
3. **Memoria:** `recordar` y `consultar_memoria` sobre una base SQLite local.
4. **Acciones con confirmación:** `cerrar_app`, `mover_archivo`, `mouse`, `teclado`.
5. **PowerShell al final:** `ejecutar_powershell`, con la lista de patrones bloqueados aplicada antes de pedir confirmación.

En este punto agrega también el **atajo de emergencia** (`ctrl+alt+shift+q`) con la librería `keyboard`, que detiene el loop en cualquier momento.

**Punto de control:** el agente resuelve una tarea de varios pasos, por ejemplo "cierra el bloc de notas y abre la calculadora".

---

## Fase 6. Memoria tipo wiki, hábitos y recomendaciones

Diseño completo en `diseno_fase6.md`: es el patrón *LLM Wiki* de Karpathy, con Obsidian para leer la wiki.

1. **Registro de hábitos** (`registro_habitos.py`):
   - es un proceso aparte, sin modelo, que cada 30 s guarda en `habitos.db` la app al frente, su categoría y el estado;
   - **no guarda títulos**;
   - los gestores de contraseñas, las apps de banco (`datos_locales.json` → `apps_banco`), Seguridad de Windows y el incógnito no dejan fila;
   - las muestras crudas se borran a los 30 días; el resumen diario se queda;
   - arranca con Windows desde el acceso directo `Registro de hábitos (asistente).lnk` de `shell:startup`
     (`.venv\Scripts\pythonw.exe "C:\asistente\registro_habitos.py"`, sin consola). Para quitarlo, borra el acceso
     directo y cierra `pythonw.exe`;
   - cada fila es solo `fecha_hora | app (exe o ID de la Tienda) | categoría | activo/inactivo/bloqueado`. Las
     categorías salen de `apps_categorias.json` (se recargan cada hora o al reiniciar el registro);
   - "inactivo" = 5 min sin **entrada física** (`entrada.py`): teclado y mouse por Raw Input y mandos. La entrada
     inyectada (SendInput: las herramientas de Cacao, macros, control remoto por software) no cuenta, ni la deriva
     del mouse. No se usa GetLastInputInfo: en este PC se reiniciaba sin parar sin que nadie tocara nada
     (`diagnostico_actividad.py`, 2026-10-06), y por eso nunca salía "inactivo";
   - `periodos_dudosos` (desde, hasta, motivo): tramos que la reflexión y las sugerencias ignoran, sin borrar nada.
     Todo lo anterior al 2026-10-06 18:22:16 está marcado (2 017 filas, medidas con GetLastInputInfo).
2. **Wiki** en `memoria\`:
   - es un vault de Obsidian con su propio git local;
   - `index.md` (siempre en el prompt) y `log.md` los escribe solo el código;
   - páginas `perfil`, `habitos`, `apps`, `rutinas` y `revision`, con secciones fijas (`wiki_esquema.json`);
   - tus notas van en las secciones "Notas de Reizo" o en `mis_notas\`; el contenido externo, en `fuentes\` (nada lo lee).
   - Si editas una sección, queda congelada: el asistente no la toca hasta que la vacíes.
3. **Reflexión diaria** (`reflexion.py`):
   - el código mide y el modelo redacta frases por página;
   - una comprobación sobre todo tu texto quita lo que lo contradiga;
   - solo arranca con ≥ 10 min sin teclado, mouse ni mando, sin pantalla completa, sin juegos abiertos, sin audio que no sea música y con la GPU libre;
   - se detiene en cuanto vuelve la actividad.
4. **Revisión semanal** (`lint.py`): arregla lo mecánico y anota en `revision.md` lo que debes mirar.
5. **Sugerencias** (`sugerencias.py`):
   - solo texto, máximo 2 al día;
   - solo para apps que empiezas a usar a la misma hora en ≥ 4 de 7 días;
   - "no me sugieras eso" las bloquea; para verlas y desbloquearlas, la herramienta `sugerencias` o las casillas de `rutinas.md`.
6. **Modo juego** (`modo_juego.py`, `deteccion.py`):
   - un juego cuenta como activo si tiene una ventana visible o usa la GPU de forma sostenida; termina tras 2 min
     sin esas señales (cerrado o en la bandeja);
   - en pausa se descargan Gemma, el mmproj y Whisper de la GPU; un Whisper "base" en la CPU entiende solo
     "estoy jugando" y "ya terminé";
   - "estoy jugando" sin juego detectado fuerza la pausa hasta "ya terminé"; con un juego ya detectado solo lo
     confirma, y al cerrarlo recarga solo.
7. **Pruebas:**
   - `probar_fase6.py` (sin modelo);
   - `probar_modo_juego.py` (sin modelo; `--medir` y `--medir-whisper` miden descarga y recarga);
   - `probar_reflexion.py` (modelo real con 7 días simulados de `simular_habitos.py`);
   - `SIN_REALES=1 evaluar_pruebas.py` (las 65 frases sin tocar archivos ni la pantalla).

---

## Fase 7. Voz e interfaz

Hecho en `voz.py` (pulsar para hablar y respuesta hablada). El modo texto (`agente_minimo.py`) no cambia.

1. **Voz a texto: faster-whisper `large-v3-turbo` en int8** (~1,3 GB de VRAM, ~0,2 s por frase en la GPU).
   - El audio nativo de Gemma 4 12B funciona con el mmproj-F16 (trae un codificador de audio), pero se descartó. En 20 grabaciones respondió como un chat ("No hay audio en el mensaje") o se comió parte de la orden en 4 casos. Con una pista de vocabulario inventaba órdenes nuevas. Whisper turbo no falló ninguna.
   - Instalación (sin permisos de administrador): `pip install faster-whisper nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"`. El modelo se descarga solo la primera vez (~1,6 GB, en `%USERPROFILE%\.cache\huggingface`).
   - No uses `initial_prompt` (pista de vocabulario): hace que el modelo rellene audios cortos con esas palabras.
2. **Texto a voz: Piper** (`pip install piper-tts`) con la voz `es_MX-claude-high`:
   - descarga: `python -m piper.download_voices --download-dir modelos/piper es_MX-claude-high`;
   - genera el primer trozo de audio en ~0,2 s en la CPU;
   - solo lee la respuesta final, nunca el pensamiento ni las confirmaciones;
   - en modo voz, el prompt pide 1 o 2 frases.
3. **Pulsar para hablar:** mantener **Ctrl+Espacio** graba y soltar envía.
   - El atajo se registra con `RegisterHotKey`, así que la app que está al frente no lo recibe.
   - Comprueba antes que esté libre en tu PC; si no, cambia `voz.atajo_hablar` en `config.json`.
   - Micrófono con `sounddevice` (`pip install sounddevice`).
4. **Frenos de seguridad:**
   - una pulsación con menos de 0,15 s de voz se descarta sin transcribir (Whisper escribe "Gracias por ver el video" en el silencio);
   - una transcripción con más de 6 palabras por segundo de voz, más 3 de margen, también se descarta;
   - las acciones que cambian algo se confirman con **Enter = sí, Esc = no**, con los botones de la isla o diciendo
     **"confirmo la instrucción"** en una grabación aparte tras la pregunta (Ctrl+Espacio o "Cacao"). Solo con
     entrada física: las teclas y los clics inyectados se rechazan, y la frase no vale con otra app sonando, casi
     sin voz (Whisper pudo inventarla) ni con un Espacio inyectado; "sí" solo no vale. Sin respuesta en 30 s = no.
     Las de solo lectura van directas;
   - un "no" termina la tarea: el agente no prueba con otra ventana ni por otro camino.
5. **Registro:** cada comando queda en `voz_registro/` (WAV + `registro.jsonl`); esa carpeta no va a git.
6. **Configuración:** sección `voz` de `config.json`, con su nota.
7. **Uso:** `.venv\Scripts\python voz.py`. Lánzalo desde tu propia terminal: con Gemma y Whisper cargados, el proceso compromete ~16 GB de memoria virtual, porque la VRAM de CUDA cuenta así en Windows. Cierra apps pesadas si el sistema anda justo.
   - Para salir, di "salir" o pulsa Ctrl+C. Si cierras la terminal con la X, la isla se cierra igual.
8. **Isla** (`C:\asistente-ui`, Tauri 2; diseño en `diseno_fase7.md`):
   - muestra el estado del agente (pensando, trabajando, terminado, error, pausa por juego) y pide las
     confirmaciones con Permitir/Denegar;
   - el agente la abre al arrancar (`config.json` → `ui`) y la cierra al salir; va unida al proceso del agente
     (Job de Windows), así que no queda abierta si este cae;
   - conexión: WebSocket en `127.0.0.1:8765` con un token por sesión en `%LOCALAPPDATA%\Asistente\ui.json`;
   - no toma el foco (salvo en su campo de texto), no sale en `listar_ventanas` ni en `ver_pantalla`, y la
     herramienta mouse no puede hacer clic en ella. Para grabarla: bandeja → "Permitir capturas";
   - **tamaño** (Ajustes → Tamaño): pequeño, mediano (por defecto) o grande, y proporcional al monitor y al escalado
     de Windows. En tu 1920×1080 al 100 % la isla abierta mide 448×112, 512×128 o 589×147 px (antes 640×160);
   - **tras una respuesta se esconde sola**: abierta mientras Cacao habla y 4 a 10 s más según el largo del mensaje;
     luego vuelve al notch pequeño, sin pulsar OK. Con el mouse encima no se esconde. Las confirmaciones nunca;
   - **campo "Escribe a Cacao…"** (vista de inicio y de pregunta):
     - con un clic físico en él, la isla toma el foco y recuerda la ventana que estaba activa; Enter envía el texto.
       Enter y Esc devuelven el foco a esa ventana; con un clic fuera, el foco se queda en la ventana donde hiciste
       clic (si fue en la propia isla, vuelve a la de antes). Un clic inyectado no abre el campo;
     - fuera del campo la isla sigue con WS_EX_NOACTIVATE y sus botones no quitan el foco;
     - el texto entra como un pedido más (consola o voz): mismos permisos, bloqueos, modo sin confirmación y
       confirmaciones. Hasta 2000 caracteres. En modo voz, la respuesta también se lee en voz alta;
     - la herramienta teclado se niega a escribir si la ventana al frente es la isla (bloqueo);
   - compilar: en `C:\asistente-ui\windows`, `npm install` y `npx tauri build --no-bundle` desde un entorno de
     VS 2022 (`vcvars64.bat`); VS 18 Insiders no trae `msvcrt.lib`.
9. **Pruebas:** `probar_voz.py` (WAV de prueba, sin micrófono ni acciones reales), `probar_fase7.py` (A: simulación;
   B: isla real; C: interruptores de modo en la isla real), `probar_modo_directo.py`, `probar_confirmacion_voz.py`,
   `probar_palabra_activacion.py`, `probar_autocompletar_login.py` (Chrome simulado) y `probar_campo_isla.py`. En
   `C:\asistente-ui\windows`: `npm run probar-campo` y las pruebas de `src-tauri/src/foco.rs` (con `rustc --test`
   desde un entorno de VS 2022).
10. **Palabra de activación "Cacao"** (`palabra_activacion.py`; el asistente también se llama Cacao):
    - detector local en la CPU: características de openWakeWord y un clasificador pequeño entrenado con
      `entrenar_cacao.py` (voces sintéticas de Piper, negativos reales de openWakeWord y el ruido real del
      micrófono). Instalación: `pip install openwakeword scikit-learn scipy`, las voces de Piper de
      `modelos/piper_cacao` y las características de openWakeWord en `modelos/cacao` (ver el script);
    - al oírla, la isla muestra "escuchando" y graba (con 1,6 s de búfer previo, para "Cacao, sube el volumen"
      de corrido) hasta un silencio o 30 s; pasa por los mismos frenos y por Whisper. Ctrl+Espacio sigue igual;
    - segunda etapa: si Whisper no oye "Cacao" al principio, era una activación falsa y se descarta sin guardar;
    - privacidad: el audio se procesa en memoria y nada se guarda hasta detectar la palabra; se ignora mientras
      Cacao habla;
    - se enciende y apaga con un clic físico en la bandeja o en la isla; sigue activa en modo juego;
    - la palabra sola nunca confirma nada;
    - **escucha de seguimiento** (`seguimiento.py`): al terminar de hablar, Cacao sigue oyendo 8 s sin la palabra,
      con un indicador verde que cuenta atrás («Te sigo oyendo · 8 s»). Si hablas, es un pedido normal (mismos frenos
      y confirmaciones; "Cacao, …" también vale); si no, termina. No se abre con otra app sonando (hay que volver a
      decir "Cacao"), ni con la escucha de «Cacao» apagada, en modo juego o detenido. Se apaga y enciende en Ajustes
      de la isla con un clic físico; al arrancar vale `voz.seguimiento.activa_al_iniciar` de `config.json`. Lo oído
      que no llega a pedido no se guarda; en `contador_cacao.json` cuenta como «seguimiento».
11. **Modo sin confirmación** (`modo_directo.py`): solo con un clic físico en la bandeja o en la isla (empieza
    apagado; el atajo de emergencia lo apaga). Con él van directos volumen, abrir_app, enfocar_ventana, buscar_web
    y cerrar_app normal; mover_archivo hasta 10 archivos, sin ejecutables ni scripts y fuera de
    `carpetas_importantes` (`datos_locales.json`), con "deshaz lo último". PowerShell y cerrar a la fuerza siempre
    preguntan. Si en la tarea entró contenido externo (archivo, web, PowerShell), todo vuelve a preguntar, salvo
    mouse y teclado. La isla muestra un indicador ámbar mientras está activo.
    - **Mouse y teclado** (desde el 2026-10-06): no preguntan nunca, en ninguna ventana, salvo una excepción:
      escribir un texto que no sale de tu pedido cuando Cacao leyó contenido de fuera (web, archivo, pantalla,
      carpetas, PowerShell) en esa tarea o en una anterior que aún recuerda: ese texto pudo salir de lo leído, y
      pregunta. "Escribe un saludo en el Bloc de notas" no pregunta. Los navegadores salen en `listar_ventanas`
      solo con el nombre de la app («Google Chrome»), sin el título de la pestaña: ningún título que pone una
      página web llega al modelo (por eso ya no distingue pestañas por su título). Siguen los bloqueos, que valen en cualquier modo: atajos
      peligrosos (punto 12), clic o teclas en la isla, escribir en ventanas sensibles (título con contraseñas o
      claves, gestores de contraseñas, Seguridad de Windows, apps de banco), escribir en el menú Inicio o la
      búsqueda (para abrir apps está abrir_app), y mouse o teclado en Configuración, el Panel de control y sus
      subprogramas y las consolas mmc. La barra de tareas sí se puede usar.
12. **Atajos bloqueados siempre:** con la tecla Windows solo valen los de ventanas y escritorios (Win+D, Win+M,
    Win+Tab, Win+flechas, Win+Shift+S, Win+Ctrl+D/flechas/F4). Bloqueados, entre otros: Win sola, Win+R, X, I, S,
    Q, E, A, U, K, P, N, B, T, V, H, L, G, Win+número, Win+Alt+R, Win+Ctrl+Enter, Win+Ctrl+O, Ctrl+Esc,
    Ctrl+Shift+Esc, Ctrl+Alt+Supr, Alt+F4 (usa cerrar_app) y el atajo de emergencia.
13. **autocompletar_login** (`autocompletar_login.py`; **apagada** hasta probarla contigo):
    - qué hace: en la ventana de Chrome que está al frente, si su título es del sitio que nombraste ("inicia sesión
      en GitHub"), hace clic en el campo de usuario y elige la primera cuenta guardada (flecha abajo + Enter). No
      envía el formulario;
    - el modelo nunca recibe el usuario ni la contraseña: el código no lee el valor de ningún campo y solo devuelve
      éxito o error (sin título, campos ni cuentas);
    - no actúa si el sitio no sale de tu pedido, si la ventana al frente no es Chrome o es de otro sitio, ni si en la
      tarea entró contenido externo (archivo, web, PowerShell). Pide confirmación siempre, también en el modo sin
      confirmación;
    - la autorización real es **Windows Hello de Chrome**: en Chrome, Configuración → Autocompletar y contraseñas →
      Gestor de contraseñas de Google → Configuración → "Usar Windows Hello al completar contraseñas". Con eso, cada
      relleno pide huella, cara o PIN, que no se pueden aprobar con teclas inyectadas;
    - activarla: `config.json` → `autocompletar_login.activa: true`. Cambia el prompt, así que antes vuelve a pasar
      `SIN_REALES=1 evaluar_pruebas.py`.
14. **Arranque automático de Cacao** (**activado** el 2026-10-06):
    - `iniciar_cacao.ps1` lanza `voz.py`, que abre la isla y escucha "Cacao" (`voz.palabra_activacion.activa_al_iniciar`).
      No abre un segundo Cacao si ya hay uno; con un juego activo espera a que se cierre antes de cargar la GPU
      (`ESPERAR_JUEGO=1`); con `-AlInicio` espera 60 s tras iniciar sesión; con `-Simular` solo comprueba;
    - `crear_acceso_directo.ps1` crea `Cacao.lnk` en `C:\asistente` (ventana minimizada, con el icono de la isla).
      Ya está creado: doble clic para arrancar Cacao a mano;
    - **activarlo (contigo frente al PC):** `powershell -ExecutionPolicy Bypass -File .\crear_acceso_directo.ps1 -Inicio`
      lo copia a `shell:startup` (solo tu usuario, sin administrador). Quitarlo: `... -Quitar`;
    - la ventana minimizada "Cacao" es el agente: Ctrl+C o "salir" lo cierran (y la isla con él). Si termina con
      error, la ventana se queda abierta con el mensaje.

### Estado real (probado contigo frente al PC el 2026-10-05)

| Prueba | Resultado |
|---|---|
| Voz: "abre la calculadora" → Esc | No se abrió (rechazo por teclado físico) |
| `probar_voz.py` | 11/11 |
| Isla: Permitir y Denegar con clic físico, Enter | Funcionan; la terminal no perdió el foco; los estados se ven bien |
| Modo juego con Roblox | Pausa en < 1 s (GPU de 14 GB a 1,4 GB); recarga sola al cerrar el juego (15 s) |
| "Estoy jugando" / "ya terminé" con el Whisper de la CPU | Entendidos (1,75 s); "ya terminé" recarga en 16 s |
| Incógnito en Chrome | Sin fila; la ventana normal sí deja fila |
| Audio | Spotify no bloquea; YouTube en ventana no, en pantalla completa sí (a los 2 s); una llamada de Teams sí |
| Registro de hábitos en `shell:startup` | Arranca y guarda una fila cada 30 s |

**Corregido durante las pruebas:** Ctrl+C no cerraba el modo voz; la isla quedaba abierta al cerrar la terminal con
la X; el modo voz se caía tras un comando en pausa; tras un "Denegar", el modelo intentaba con otra ventana.

### Modo sin confirmación y "Cacao" (2026-10-06, en simulación)

| Prueba | Resultado |
|---|---|
| `probar_modo_directo.py` (texto leído en pantalla, clic fuera de la ventana, atajos bloqueados, 11 archivos, un .exe, deshacer, el agente no puede cambiar el modo) | 73/73 |
| `probar_confirmacion_voz.py` ("confirmo la instrucción" con variaciones, transcripción inventada, otro audio, Espacio inyectado) | 33/33 |
| `probar_fase7.py` C: clic inyectado en el interruptor del modo, en la isla real | Llega como no físico; el modo no cambia |
| `probar_palabra_activacion.py` | 27/27 |
| "Cacao" con voces que no vio al entrenar (umbral 0,9) | Sola 37/54; de corrido con la orden 77/108 |
| Activaciones falsas | 0 en 7,9 min de conversación, 0 en 20 frases que mencionan "cacao", 0 en 15 min de ruido y música, 0 en tus 30 grabaciones; 10,8 por hora en las 10,7 h de validación de openWakeWord (las filtra la segunda etapa) |
| "Oye, Cacao" (mismo método, para comparar) | Detecta menos (24-32/54) y baja poco las falsas (2,8 por hora con el umbral más alto) |

El modelo instalado es la segunda versión de las tres que entrené (una capa de 96, una ronda de negativos difíciles);
la tercera, la del script actual, con tonos desplazados y frases de corrido, no la mejoró.

### autocompletar_login y arranque automático (2026-10-06, en simulación)

| Prueba | Resultado |
|---|---|
| `probar_autocompletar_login.py` (sitio no nombrado, otra app o sitio al frente, contenido externo, campo ambiguo o tapado, la isla, lista que no aparece, ventana que cambia, atajo de emergencia, nada de credenciales hacia el modelo, siempre pregunta) | 46/46 |
| `iniciar_cacao.ps1 -Simular` | Encuentra todo; con un proceso falso de `voz.py` en marcha, no abre otro |
| `crear_acceso_directo.ps1` (sin `-Inicio`) | `Cacao.lnk` en `C:\asistente`; la carpeta de Inicio sigue solo con el registro de hábitos |

### Campo de texto de la isla (2026-10-06, en simulación)

| Prueba | Resultado |
|---|---|
| `foco.rs` (Windows simulado: un clic no activa una ventana NOACTIVATE): Enter y Esc devuelven el foco a la ventana de antes; un clic fuera lo deja en la ventana del clic (y, si fue en la isla, vuelve a la de antes); los botones no lo quitan; un clic no físico no lo toma; ventana de antes cerrada | 10/10 |
| `npm run probar-campo` (controlador del campo): los tres casos, un solo retorno del foco, Esc que no cierra la isla, sin conexión, campo vacío, 2000 caracteres | 18/18 |
| `probar_campo_isla.py`: servidor (token), cola consola + isla, mismo camino que la consola y la voz, teclado bloqueado con la isla al frente (también en el modo sin confirmación) | 29/29 |
| Regresión | palabra de activación 27/27, modo directo 73/73, autocompletar 46/46, confirmación por voz 33/33, fase 7 A 26/26 |
| `cargo check --offline`, `tsc` y `tauri build --no-bundle` sin red | Sin errores; `asistente-ui.exe` recompilado |

### Pruebas presenciales (2026-10-06, contigo frente al PC)

| Prueba | Resultado |
|---|---|
| "Cacao" con tu voz: 57 tomas guiadas (`grabar_cacao.py`): 41 sola, 6 de corrido, 10 palabras parecidas | Detector anterior (umbral 0,9): 38/47; falla siempre "rápido" (0/4) |
| Detector reentrenado con 2/3 de tus tomas (`entrenar_cacao.py --reales`), medido con el tercio que no vio | Nuevo 15/17 frente a 13/17 del anterior; voces sintéticas sola 46/54 (antes 37/54), de corrido 81/108 (antes 77/108); activaciones falsas en el audio general de openWakeWord 16,7/h (antes 10,8/h), filtradas por la segunda etapa. **Instalado: `cacao_v4` con umbral 0,9** (copia del anterior en `modelos/cacao/cacao_anterior_v2.npz`) |
| Tu música (3 min) y videos que dicen "cacao" (4 min), por los altavoces | Primera etapa: 1 y 2 activaciones (antes 0 y 3). Pasaba la segunda etapa "Entonces el cacao se produce…": **corregido**, ahora "Cacao" tiene que ir al principio o tras "oye/hola"; "caca" tampoco pasa |
| **Fallo encontrado en vivo**: tras la primera detección Cacao dejaba de escuchar | El G435 entrega bloques de 416 muestras y la grabación medía tramas de 480 por bloque: nunca terminaba. **Corregido** (prueba con bloques de 416, 160 y 1000) |
| Contador diario (`contador_cacao.json`, solo números) | Primera etapa, segunda etapa y pedidos por día. En la prueba 4: 6 / 3 / 3 |
| Regresión de las 65 frases × 3 semillas (`SIN_REALES=1`) | 195/195 (100 %), JSON 100 %, frase 58 3/3, 3,71 s de media |
| Isla con tu clic (`prueba_presencial_isla.py`, servidor de prueba) | Interruptores de la isla y de la bandeja: físicos; indicadores a la vista. Campo: Enter y Esc devuelven el foco al Bloc de notas, el clic fuera lo deja en la ventana del clic, el clic en la isla vuelve al Bloc de notas, los botones no quitan el foco; se ve bien. 13/13 |
| "Confirmo la instrucción" con tu voz (Cacao real, modo voz) | Ctrl+Espacio + frase: vale (abrió la Calculadora). "Cacao, confirmo la instrucción" sin teclas: vale (abrió el Bloc de notas). "Sí" solo: no vale; Esc: no se abrió nada |

### Segunda tanda presencial (2026-10-06, noche)

| Prueba | Resultado |
|---|---|
| Ctrl+S en el Bloc de notas (`diagnostico_atajos.py`: código virtual, de escaneo, KEYEVENTF_SCANCODE, con y sin pausas) | 0/10: no era el envío. En español, **Guardar es Ctrl+G** (Ctrl+S no existe en el Bloc de notas; en Word es Subrayado) |
| Obstáculos (`obstaculos.py`): Cacao comprueba el efecto de cada atajo y clic, avisa y recuerda el camino | Tres rondas reales: la primera aprendió mal (el Esc que cierra el diálogo) y la segunda solo "Archivo"; corregido. Al final: Ctrl+S → **Ctrl+G** directo, con aviso. `probar_obstaculos.py` 35/35 |
| Modo sin confirmación, contigo (pedidos escritos en la isla) | Volumen, abrir y cerrar la Calculadora, escribir en el Bloc de notas el texto del pedido, mover un archivo y deshacerlo: sin preguntar. PowerShell **sí** preguntó (dos veces). Se activa y apaga con tu clic |
| Arranque con `Cacao.lnk` | Arranca la voz, la isla y la escucha; respondió a "Cacao". Un segundo doble clic no abre otro Cacao (aviso de 4 s). **Activado en Inicio** |
| 65 frases × 3 con el prompt nuevo (atajos comprobados, Windows en español, fecha y hora en cada pedido) | Primera herramienta 195/195; tarea completa 193/195 (la frase 44: en la simulación la terminal ya está al frente y responde eso); 3,91 s de media |

El modo sin confirmación empieza apagado en cada arranque (no se guarda en ningún archivo). Cada pedido lleva la fecha
y la hora ("[Ahora: martes 6 de octubre de 2026, 21:50]"), así Cacao responde "¿qué hora es?" sin buscar.

### Isla y escucha de seguimiento (2026-10-06, en simulación)

| Prueba | Resultado |
|---|---|
| Texto encimado en la isla («cerrar_app: Cerré la ventana…» sobre «Te escucho…») | Reproducido en el navegador: la copia atenuada de un paso largo bajaba a la línea siguiente. **Corregido**; además, tras 20 pasos el ticker dejaba de avanzar (corregido) |
| Tamaño (`npm run dev`, mensajes simulados con `window.cacao`) | Mediano legible; Ajustes con la fila «Tamaño» cabe entero |
| Cierre automático | Sin voz, a los 4 s; con voz, 4 s después de terminar de hablar; con el mouse encima espera a que salga; una confirmación no se esconde |
| `probar_seguimiento.py` (escucha de seguimiento: silencio, cola de la voz de Cacao, un clic, otra app sonando, bloques del G435, frenos, Ctrl+Espacio, modos) | 35/35 |
| Modo sin confirmación, mouse y teclado (`probar_modo_directo.py`): títulos solo de navegadores ("escribe un saludo en el Bloc de notas" ya no pregunta; con Chrome abierto, sí), "regedit" en el Inicio y la búsqueda bloqueado, nada dentro de Configuración ni del Panel de control | 138/138 |
| Regresión | palabra de activación 41/41, confirmación por voz 33/33, campo de la isla 29/29, obstáculos 35/35, autocompletar 46/46, fase 6 142/142, `probar_voz.py` 11/11 (Gemma y Whisper en la GPU) |

### Pendiente para cuando estés frente al PC (en orden)

1. **Isla nueva y escucha de seguimiento:** ver la isla compacta con los tres tamaños, el cierre tras una respuesta
   hablada y el indicador de los 8 s; decir algo en esos 8 s sin "Cacao"; con música sonando, que no se abra. Con el Panel de control abierto en el
   Explorador, que Cacao no haga clic ni escriba ahí.
2. **autocompletar_login:** activa Windows Hello en Chrome (punto 13) y prueba a mano que Chrome lo pide; luego
   `autocompletar_login.activa: true`, añade 2-3 frases al set y vuelve a pasar las 65 frases; prueba en un sitio
   con cuenta guardada: con Hello rellena y no envía; si cancelas Hello no rellena; con otra ventana al frente da
   error.
3. **Arranque automático (ya activo):** al reiniciar o iniciar sesión, mira que Cacao aparezca a los ~60 s. Prueba
   también a iniciar sesión con un juego que se abra solo: Cacao debe esperar.
4. **"Cacao" en el día a día:** mira `contador_cacao.json` tras unos días (activaciones de la primera etapa frente a
   pedidos). "Cacao" dicho rápido aún no se detecta.
5. **Grabar la isla** con "Permitir capturas".
6. **Mando:** detección de actividad (no había uno a mano).
7. **Datos reales:** Obsidian, y la reflexión diaria y las sugerencias tras una semana de hábitos. `apps_banco` sigue
   vacío (no hay apps de banco en este PC).

---

## Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| El modelo carga con 0 capas en GPU | llama-cpp-python compilado sin CUDA | Reinstala con las variables `CMAKE_ARGS` del paso 2.2 en la **misma** ventana de PowerShell |
| Error de CMake: no encuentra el compilador | Build Tools sin la carga de C++ | Abre el instalador de VS y agrega "Desarrollo para el escritorio con C++" |
| `nvcc` no se reconoce | CUDA no está en el PATH | Reinicia; si persiste, agrega `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin` al PATH |
| `unknown model architecture` | Versión sin soporte para Gemma 4 | Instala llama-cpp-python desde GitHub (paso 2.2) |
| Error de memoria CUDA (out of memory) | Contexto o cuantización demasiado grandes | Baja `n_ctx` a 4096 o usa Q4_K_M |
| Respuestas lentas (menos de 10 tokens/s) | Parte del modelo en CPU | Revisa que todas las capas estén en GPU y cierra juegos o apps que usen VRAM |
| Error en `EndpointVolume` | Versión antigua de pycaw | `pip install --upgrade pycaw` |
| Caracteres raros en nombres de apps | Codificación de PowerShell | El script ya fuerza UTF-8; revisa que no lo hayas quitado |
| El agente se repite o entra en bucle | Prompt ambiguo o temperatura alta | Baja `temperature` a 0.2 y revisa las descripciones en `herramientas.json` |
| El sistema se queda sin RAM con el modelo cargado | Con `use_mmap` el GGUF mapeado ocupa ~8,6 GB de RAM física aunque las capas estén en la GPU | `"use_mmap": false` en `config.json` (~1,3 GB de RAM, misma velocidad) |
| "ggml-cuda.cu: CUDA error" sin más detalle | llama-cpp-python 0.3.36 ocultaba los errores de llama.cpp: usa la numeración antigua de niveles y trata el error como depuración | `modelo.py` ya los muestra y los guarda en `errores_llama.log` (con la pila de Python si el proceso aborta); revisa ese archivo |
| El modo voz descarta todo lo que dices (`pico` 1 en `voz_registro`) | El micrófono está silenciado (botón de mute del headset) u otra app lo tomó en exclusiva | Quita el mute; en Roblox u otros juegos, revisa el chat de voz |
| La isla no compila: `LNK1104 msvcrt.lib` | Se usó VS 18 Insiders | Compila desde un entorno de VS 2022 (`vcvars64.bat`) |
| Whisper escribe "Gracias" o "Gracias por ver el video" sin que hables | Alucinación típica en silencio o ruido | `voz.py` descarta las pulsaciones casi sin voz (`voz.min_voz_s`) y esas frases |

---

## Lista de verificación

- [ ] Driver NVIDIA con CUDA 12.8 o superior
- [ ] Python 3.11.9 (o 3.12), Git, VS Build Tools y CUDA Toolkit instalados
- [ ] llama-cpp-python compilado con CUDA
- [ ] Modelo Gemma 4 12B Q5_K_M descargado
- [ ] Prueba de humo con todas las capas en GPU
- [ ] `agente_minimo.py` resolviendo las 5 frases de prueba
- [ ] Set de pruebas con porcentaje de acierto medido
- [x] Herramientas restantes y atajo de emergencia
- [x] Memoria wiki, hábitos y recomendaciones (probado en real; falta el mando y una semana de datos)
- [x] Voz, isla e inicio automático del registro de hábitos
- [ ] autocompletar_login con Windows Hello (hecha en simulación, apagada)
- [x] Arranque automático de Cacao (`Cacao.lnk` en Inicio desde el 2026-10-06)
