---
estado: verificado
verificado_commit: c297bcb
verificado_fecha: 2026-10-11
fuentes: [agente_minimo.py, voz.py, iniciar_cacao.py, modelo.py, muestreo_gramatica.py, config.json, herramientas.json]
---
# Visión general y flujo de un pedido

## Piezas

| Pieza | Archivo | Página |
|---|---|---|
| Lanzador sin terminal | `iniciar_cacao.py` | [[arrancar-detener]] |
| Modo voz (proceso principal) | `voz.py` | [[voz]] |
| Agente: prompt, esquema, bucle, ejecutor | `agente_minimo.py` | [[agente-y-herramientas]] |
| Carga del modelo | `agente_minimo.cargar_modelo()` → `modelo.py` + `muestreo_gramatica.py` (importar no carga) | [[configuracion-vigente]] |
| Protecciones del bucle | `protecciones_ejecucion.py` | [[protecciones]] |
| Permisos, bloqueos, confirmaciones | `herramientas.json`, `ui_isla.py`, `entrada_fisica.py`, `modo_directo.py` | [[permisos-y-bloqueos]] |
| Isla (interfaz) | `ui_isla.py` ↔ repositorio `C:\asistente-ui` | [[isla-websocket]] |
| Palabra «Cacao» y seguimiento | `palabra_activacion.py`, `seguimiento.py` | [[palabra-activacion]] |
| Modo juego | `modo_juego.py`, `guardia_juego.py`, `deteccion.py` | [[modo-juego]] |
| Memoria, wiki, reflexión | `memoria.py`, `wiki.py`, `reflexion.py`, `lint.py`, `sugerencias.py` | [[memoria-y-wiki]] |
| Registro de hábitos | `registro_habitos.py`, `habitos.py` | [[registro-habitos]] |
| Actividad física | `entrada.py`, `entrada_fisica.py` | [[entrada-fisica]] |

Hay un solo proceso de agente (`voz.py`, que importa `agente_minimo` como `a`). El registrador de hábitos es un
proceso aparte, sin modelo.

## Flujo de un pedido (modo voz)

1. **Entrada.** Ctrl+Espacio, la palabra «Cacao», los 8 s de seguimiento o el campo de texto de la isla
   (`pedidos.py`, misma cola).
2. **Frenos de audio** (`voz.py`): silencio, demasiadas palabras para la voz oída y frases típicas de alucinación.
   Después transcribe con faster-whisper.
3. **`atender_con_memoria()`.** Atiende las frases de modo juego («estoy jugando», «ya terminé»), toma el cerrojo del
   planificador (que detiene la reflexión), refresca el prompt si cambió el índice de la wiki o los obstáculos y
   llama a `atender()`. En la pausa del modo juego solo atiende el volumen por el camino rápido, sin el modelo.
4. **`atender()`:** antes del modelo, el [[camino-rapido]] (17 frases simples, por el mismo `ejecutar()`). Si no
   entra, como máximo `max_pasos_por_tarea` = 15 pasos:
   - comprueba el atajo de emergencia;
   - `pedir_accion()`: `create_chat_completion` con `response_format` JSON y el esquema `ESQUEMA_ACCION`
     (temperatura 0,3, top_p 0,95, top_k 64, 512 tokens). Si el historial tiene una imagen, pasa por el handler de
     visión;
   - si la acción es `finalizar`, la validan las [[protecciones]] (efecto verificado y sin afirmaciones sin
     evidencia) y se devuelve el mensaje;
   - si no, llama a `ejecutar()`: permisos, planificadores sin efecto, confirmación física y luego la
     implementación. El resultado vuelve al historial como mensaje de usuario;
   - `registrar_resultado()`: con dos alternativas fallidas corta y pregunta;
   - cierre rápido: si la acción trae `mensaje_final`, su efecto quedó verificado y `validar_finalizacion` lo
     acepta, termina sin otra llamada al modelo. El perfil `qwen9b` lo apaga ([[cierre-rapido-mensaje-final]]).
5. **Respuesta.** La lee Piper. El pensamiento y los pasos solo van al registro. Se añade una sugerencia si toca y
   se notifica el estado a la isla.

En modo texto (`agente_minimo.py` sin voz) el flujo es el mismo, sin audio.

## Dónde se decide qué

- Qué herramienta usar: el modelo, guiado por `prompt_sistema()` y las descripciones de `herramientas.json`.
- Si una acción se pregunta: `ejecutar()` + `decision_modo()` en `agente_minimo.py`, y `ejecutar_voz()` en
  `voz.py` ([[permisos-y-bloqueos]]).
- Si se puede confirmar «hecho»: `protecciones_ejecucion.py` ([[protecciones]]).
