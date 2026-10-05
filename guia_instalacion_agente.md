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

## Fase 6. Aprendizaje y recomendaciones

1. **Registro de hábitos:** un hilo en segundo plano que cada 30–60 segundos guarda en SQLite la ventana activa y la hora.
2. **Reflexión periódica:** una vez al día, el modelo lee el registro y escribe un resumen de patrones que se guarda como memoria de tipo `habito`.
3. **Perfil en el prompt:** al iniciar, las memorias más relevantes se agregan al prompt de sistema.
4. **Recomendaciones:** cuando detecta un patrón claro (por ejemplo, abres las mismas apps a la misma hora), sugiere la acción. Ofrece siempre, nunca la ejecuta sola.

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
   - las acciones que cambian algo se confirman con el teclado: **Enter = sí, Esc = no**. Las de solo lectura van directas.
5. **Registro:** cada comando queda en `voz_registro/` (WAV + `registro.jsonl`); esa carpeta no va a git.
6. **Configuración:** sección `voz` de `config.json`, con su nota.
7. **Uso:** `.venv\Scripts\python voz.py`. Lánzalo desde tu propia terminal: con Gemma y Whisper cargados, el proceso compromete ~16 GB de memoria virtual, porque la VRAM de CUDA cuenta así en Windows. Cierra apps pesadas si el sistema anda justo.
8. **Palabra de activación (opcional):** openWakeWord.
4. **Interfaz:** ícono en la bandeja del sistema y ventana de chat con PySide6, más un atajo global para invocarlo.
5. **Inicio automático:** un acceso directo en `shell:startup`.

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
- [ ] Herramientas restantes y atajo de emergencia
- [ ] Memoria, hábitos y recomendaciones
- [ ] Voz, interfaz e inicio automático
