---
estado: verificado
verificado_commit: a04c212
verificado_fecha: 2026-10-12
fuentes: [entrenar_cacao.py, medir_arranque.py, config.json, modelo.py, agente_minimo.py, protecciones_ejecucion.py, comparacion_modelos/ejecutar.py, REPORTE_TRABAJO_CACAO.md, SRS.md, guia_instalacion_agente.md, resultados_swa_y_recursos.md]
---
# Backlog

Armado con los pendientes de `REPORTE_TRABAJO_CACAO.md` §15–16, el SRS §9, la guía y `resultados_swa_y_recursos.md`.

Cada punto se comprobó contra Git y los archivos el 2026-10-10:
- **hecho**: hay evidencia;
- **pendiente**: no está y hay evidencia de que falta;
- **desconocido**: no se puede comprobar sin ejecutar, sin datos personales o sin el usuario.

## Producción y código

| # | Punto | Estado | Evidencia |
|---|---|---|---|
| 1 | Protecciones del ejecutor en producción | hecho | 9e2c1f1 y 5889dda; `protecciones_ejecucion.py` |
| 2 | Salida UTF-8 | hecho | lanzador (99fd1bc) y también `voz.py` y el modo texto (8e72787, suite `probar_salida_utf8.py`) |
| 3 | Regla JSON sin caracteres de control en producción | hecho y medido (65 × 3, #8) | 7d31aa7; `probar_gramatica_json.py` 11/11 |
| 4 | Cierre rápido `mensaje_final`: validarlo y apagarlo en Qwen | hecho | 69297e4 y d95855d ([[cierre-rapido-mensaje-final]]) |
| 5 | `swa_full=False` en producción | revertido para Gemma (397d0a2); solo en el perfil `qwen9b` | `ejecutar.py --swa-full` roto (se deja). [[swa-full-false]] |
| 6 | Corregir los falsos positivos de la protección (también «no puedo verificar») | hecho en código | c6a74f3; `probar_protecciones_ejecucion.py` 44/44 |
| 7 | Volver a pasar las suites sin modelo después de 9e2c1f1 | hecho (2026-10-10, eb5a9c4) | todas pasan; totales en [[suites]] |
| 8 | 65 frases × 3 con producción tras la Fase 1 | hecho (2026-10-11) | 195/195 y 194/195 (base 193). [[evaluacion-65-frases]] |
| 9 | Commit de `ejecutar.py`, `pruebas_nuevas_30.json` y `medir_recarga_completa.ps1` | hecho | cabf3ed |
| 10 | Revisar la línea base de `verificar.py` | hecho: falla de verdad | hashes de la ronda 3 desde 84fbe0b; detalle en [[comparacion-modelos]]. Actualizarlos: decisión del usuario |
| 11 | Apagado automático del modo sin confirmación (SRS R-17, «valorar») | pendiente | `modo_directo.py` no tiene temporizador |
| 11b | `entrenar_cacao.py` lee los datos movidos a `D:\Cacao\entrenamiento\` | hecho (permiso del usuario) | 3ad35c7 y 76baceb; rutas comprobadas sin entrenar |
| 11c | Carga perezosa del modelo: importar `agente_minimo` ya no usa la GPU | hecho y probado con Gemma | 14c17cb; `medir_arranque.py` (ac148e6), sin micrófono ni isla |
| 11d | Recompilar la isla (bandeja y protocolo v2) | hecho y probado en físico | [[compilar-isla]] |
| 11e | `listar_controles` con id ausente, 0 o inexistente usa la ventana al frente | hecho | e9a580d ([[frenos-cierre]] §2) |
| 11f | `cerrar_app` ignora `forzar` si el pedido no lo pide | hecho | 0a3ea28 ([[frenos-cierre]] §1) |

## Temas sin código todavía

Ordenados por el usuario en [[hoja-de-ruta]] (2026-10-11). La prueba de Qwen 9B se lanzó el 2026-10-11 ([[lista-qwen9b-ronda2]]).

## Modelos y voz (experimental)

| # | Punto | Estado | Evidencia |
|---|---|---|---|
| 12 | Mover WSL al disco D | hecho | existe `D:\WSL\Ubuntu-24.04` |
| 13 | Perfil lean de Qwen3-TTS | hecho | `.comparacion-runtime/qwen3_tts_lean.yaml`, b7270b4 |
| 14–15 | Lanzador y prueba prolongada en WSL | descartados (WSL) | — |
| 16 | Migrar producción a llama.cpp servidor | descartado por ahora | [[motor-llama-cpp]] |
| 17 | Sustituir Piper por Qwen3-TTS | pendiente: medir si cabe en Windows (RAM de 16 GB) | `config.voz.piper_voz` |
| 18 | MTP | descartado por ahora | `mtp_probado: false` |
| 19 | Gemma 26B A4B | descartado por ahora | sin datos |
| 20 | Puntuar la evaluación a ciegas Gemma Q5 / Qwen Q5 | descartada por el usuario | la sustituye la prueba en producción |
| 21 | Puntuar la evaluación a ciegas Q5 / Q4 | pendiente | `resultados_ciegas_q4.md`: 20 vacías, sin commit |
| 22 | Margen de RAM en la recarga WSL | descartado (WSL) | — |
| 23 | Qwen 9B: banco 189/195; producción 173, 182 y 182 con contrato (no pasa) | **en uso real una semana** desde 5e9eee0, sin pasar el criterio | [[qwen-como-cerebro]]; `resumir_semana_qwen.py` |
| 26 | El simulador de producción no mueve el foco al enfocar | candidata | `benchmark_gramatica.py:180` |
| 28 | Camino rápido (17 frases, volumen en pausa) | **hecho** y activo (fdf84d1) | [[camino-rapido]] |
| 29 | Caché por estados para Qwen | **hecho**: activa en qwen9b | [[cache-estados]] |
| 31 | `mouse_sim` mira la ventana real | candidata | `benchmark_gramatica.py:206` |
| 30 | Filtrado | aparcado | [[filtrado-herramientas]] |

## Con el usuario delante

Ver [[pendientes-presenciales]]. Ese estado no se puede comprobar desde el repositorio.
