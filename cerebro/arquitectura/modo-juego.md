---
estado: verificado
verificado_commit: d4b36dd
verificado_fecha: 2026-10-10
fuentes: [modo_juego.py, guardia_juego.py, deteccion.py, agente_minimo.py, config.json, SRS.md]
---
# Modo juego y guardia de la GPU

## Detección de juego activo (`deteccion.DetectorJuegos`)

- **Qué cuenta como proceso de juego:** categoría «juegos» o una carpeta de `carpetas_juegos`. No cuentan los
  `lanzadores` (Steam, Epic…) ni lo de `no_son_juegos` (Wallpaper Engine, Game Bar…).
- **Cuándo está activo:** si tiene una ventana visible o usa la GPU (motor 3D) de forma sostenida
  (`memoria_wiki.juegos`: umbral 5 %, ventana de 30 s, fracción 0,6).
- **Cuándo termina:** tras `gracia_s` = 120 s sin esas señales. Un juego que queda en la bandeja no cuenta.

## Modo juego (`modo_juego.py`)

- **Activo** según `config.modo_juego.activo`.
- **Entrada:** `confirmar` = 2 comprobaciones seguidas con juego, cada `intervalo_s` = 5 s.
- **Salida:** igual, 2 comprobaciones sin juego.
- **Al entrar:** descarga Gemma, mmproj y Whisper (`descargar_modelos`) con el cerrojo del planificador; nunca a mitad
  de una tarea o de una reflexión. Al salir los recarga (`cargar_modelos`).
- **En pausa:** responde sin modelo con un mensaje. «estoy jugando» y «ya terminé» fuerzan la entrada y la salida
  (`comando_modo_juego`), reconocidas con el Whisper base de la CPU ([[voz]]).
- **Isla:** queda compacta y dormida.

## Guardia (`guardia_juego.py`)

`modelo.crear_llm` y `TranscriptorWhisper` llaman a `exigir_gpu_libre`: con un juego activo no se carga nada en la
GPU.
- **Scripts de prueba y medición:** terminan con un aviso «[GPU] … está abierto». Con `ESPERAR_JUEGO=1`, esperan.
- **El agente** (y el lanzador, que pone `ESPERAR_JUEGO=1`): espera a que se cierre el juego.

Regla para Claude Code: si una prueba sale por la guardia, avisa; no la esquives ([[lecciones]]).

## Cifras (SRS RNF-08, sin volver a medir)

Origen: `resultados_modo_juego_gemma.json` y `resultados_modo_juego_whisper.json`.
- **En simulación:** descarga de Gemma con visión en 0,19–0,20 s; recarga en ~12,6 s.
- **En real con Roblox:** de 14 GB a 1,4 GB en menos de 1 s; recarga en 15 s.

## Pruebas

`probar_modo_juego.py` (lógica con juego simulado; `--medir` carga modelos) y `medir_isla_juego.py`
([[suites]]).
