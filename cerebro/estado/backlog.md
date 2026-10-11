---
estado: verificado
verificado_commit: 945fa17
verificado_fecha: 2026-10-11
fuentes: [entrenar_cacao.py, medir_arranque.py, config.json, modelo.py, agente_minimo.py, protecciones_ejecucion.py, comparacion_modelos/ejecutar.py, REPORTE_TRABAJO_CACAO.md, SRS.md, guia_instalacion_agente.md, resultados_swa_y_recursos.md]
---
# Backlog

El pedido original remitía a «la lista de abajo», pero esa lista no venía en el mensaje. Esta se armó con los
pendientes documentados en `REPORTE_TRABAJO_CACAO.md` §15–16, el SRS §9, la guía y `resultados_swa_y_recursos.md`.

Cada punto se comprobó contra Git y los archivos el 2026-10-10:
- **hecho**: hay evidencia;
- **pendiente**: no está y hay evidencia de que falta;
- **desconocido**: no se puede comprobar sin ejecutar, sin datos personales o sin el usuario.

## Producción y código

| # | Punto | Estado | Evidencia |
|---|---|---|---|
| 1 | Protecciones del ejecutor en producción | hecho | 9e2c1f1 y 5889dda; `protecciones_ejecucion.py` |
| 2 | Salida UTF-8 | hecho | lanzador (99fd1bc) y también `voz.py` y el modo texto (8e72787, suite `probar_salida_utf8.py`) |
| 3 | Regla JSON sin caracteres de control en producción | hecho en código, sin medir con el modelo | 7d31aa7; `probar_gramatica_json.py` 11/11 |
| 4 | Decidir el cierre rápido `mensaje_final` frente al contrato de pruebas | pendiente | `agente_minimo.py:433` y 817-827 |
| 5 | `swa_full=False` en producción | **revertido** (397d0a2); los 7 fallos no se reproducen | A con 7 casos 7/7 y con #1–42 42/42 (dbb0e42). [[swa-full-false]] |
| 6 | Corregir los falsos positivos de la protección (también «no puedo verificar») | hecho en código | c6a74f3; `probar_protecciones_ejecucion.py` 44/44 |
| 7 | Volver a pasar las suites sin modelo después de 9e2c1f1 | hecho (2026-10-10, eb5a9c4) | todas pasan; totales en [[suites]] |
| 8 | 65 frases × 3 con producción después de las protecciones, la regla JSON y el detector nuevo (necesita GPU y permiso) | hecho (2026-10-11, producción sin swa_full) | 1.ª herramienta 195/195, completas 194/195 (base 193). [[evaluacion-65-frases]] |
| 9 | Commit de los cambios de `ejecutar.py`, `pruebas_nuevas_30.json` y `medir_recarga_completa.ps1` | hecho | cabf3ed |
| 10 | Revisar la línea base de `verificar.py` | hecho: falla de verdad | hashes de la ronda 3 desde 84fbe0b; detalle en [[comparacion-modelos]]. Actualizarlos: decisión del usuario |
| 11 | Apagado automático del modo sin confirmación (SRS R-17, «valorar») | pendiente | `modo_directo.py` no tiene temporizador |
| 11b | `entrenar_cacao.py` lee los datos movidos a `D:\Cacao\entrenamiento\` | hecho (permiso del usuario) | 3ad35c7 y 76baceb; rutas comprobadas sin entrenar |
| 11c | Carga perezosa del modelo: importar `agente_minimo` ya no usa la GPU | hecho y probado con Gemma | 14c17cb; `medir_arranque.py` (ac148e6), sin micrófono ni isla |
| 11d | Recompilar la isla (bandeja y protocolo v2) | hecho y probado en físico | [[compilar-isla]] |

## Temas sin código todavía

Ordenados por el usuario en [[hoja-de-ruta]] (2026-10-11). La prueba de Qwen 9B ya está preparada (0b90b51).

## Modelos y voz (experimental)

| # | Punto | Estado | Evidencia |
|---|---|---|---|
| 12 | Mover WSL al disco D | hecho | existe `D:\WSL\Ubuntu-24.04` |
| 13 | Perfil lean de Qwen3-TTS | hecho | `.comparacion-runtime/qwen3_tts_lean.yaml`, b7270b4 |
| 14 | Lanzador experimental supervisado en WSL conectado a Cacao | descartado (WSL, 2026-10-11) | ningún archivo de producción usa los puertos 18080 u 8091 |
| 15 | Prueba prolongada del conjunto en WSL (recuperación, suspensión, modo juego) | descartado (WSL) | sin archivos de resultados |
| 16 | Migrar producción a llama.cpp servidor | descartado por ahora (2026-10-11) | `modelo.py` usa llama_cpp; [[motor-llama-cpp]] |
| 17 | Sustituir Piper por Qwen3-TTS | pendiente: medir si cabe en Windows (RAM de 16 GB) | `config.voz.piper_voz` |
| 18 | MTP | descartado por ahora | `mtp_probado: false` |
| 19 | Gemma 26B A4B | descartado por ahora | sin datos |
| 20 | Puntuar la evaluación a ciegas Gemma Q5 / Qwen Q5 | pendiente | `resultados_ciegas.md`: 20 casillas `__/5` vacías |
| 21 | Puntuar la evaluación a ciegas Q5 / Q4 | pendiente | `resultados_ciegas_q4.md`: 20 vacías, sin commit |
| 22 | Reducir el margen de RAM en la recarga WSL (99,96 % de uso) | descartado (WSL) | `resultados_swa_y_recursos.md` |

## Con el usuario delante

Ver [[pendientes-presenciales]]. Ese estado no se puede comprobar desde el repositorio.
