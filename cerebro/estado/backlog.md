---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [config.json, modelo.py, agente_minimo.py, protecciones_ejecucion.py, comparacion_modelos/ejecutar.py, REPORTE_TRABAJO_CACAO.md, SRS.md, guia_instalacion_agente.md, resultados_swa_y_recursos.md]
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
| 2 | Salida UTF-8 | hecho (solo con el lanzador) | `iniciar_cacao.py:70`, 99fd1bc |
| 3 | Regla JSON sin caracteres de control en producción | pendiente | regla `char` de `.venv` sin cambios; solo `integracion.py` la parchea |
| 4 | Decidir el cierre rápido `mensaje_final` frente al contrato de pruebas | pendiente | `agente_minimo.py:433` y 817-827 |
| 5 | `swa_full=False` en producción | pendiente | ni `modelo.py` ni `config.json` lo pasan |
| 6 | Corregir los falsos positivos de la protección («escrita», «sonido… está», «no he podido») | pendiente | `_CLAIMS` y `_NEGATED_CLAIM` sin cambios desde 5889dda |
| 7 | Volver a pasar las suites sin modelo después de 9e2c1f1 | desconocido | ningún commit posterior registra totales |
| 8 | 65 frases con el prompt de producción después de las protecciones | pendiente | la última pasada (`resultados_pruebas_65_fecha.json`) es del 2026-10-06 |
| 9 | Commit o descarte de los cambios de `comparacion_modelos/ejecutar.py` (swa_full, conjunto nuevo, ruta de Q4) y de `pruebas_nuevas_30.json` | pendiente | `git status` |
| 10 | Revisar la línea base de `verificar.py` | desconocido | `REPORTE` dice que falla; no se ejecutó |
| 11 | Apagado automático del modo sin confirmación (SRS R-17, «valorar») | pendiente | `modo_directo.py` no tiene temporizador |

## Modelos y voz (experimental)

| # | Punto | Estado | Evidencia |
|---|---|---|---|
| 12 | Mover WSL al disco D | hecho | existe `D:\WSL\Ubuntu-24.04` |
| 13 | Perfil lean de Qwen3-TTS | hecho | `.comparacion-runtime/qwen3_tts_lean.yaml`, b7270b4 |
| 14 | Lanzador experimental supervisado en WSL conectado a Cacao | pendiente | ningún archivo de producción usa los puertos 18080 u 8091 |
| 15 | Prueba prolongada del conjunto en WSL (recuperación, suspensión, modo juego) | pendiente | sin archivos de resultados |
| 16 | Migrar producción a llama.cpp servidor | pendiente | `modelo.py` usa llama_cpp; [[motor-llama-cpp]] |
| 17 | Sustituir Piper por Qwen3-TTS | pendiente | `config.voz.piper_voz` |
| 18 | MTP | pendiente | `mtp_probado: false` |
| 19 | Gemma 26B A4B | pendiente (no se persigue) | sin datos |
| 20 | Puntuar la evaluación a ciegas Gemma Q5 / Qwen Q5 | pendiente | `resultados_ciegas.md`: 20 casillas `__/5` vacías |
| 21 | Puntuar la evaluación a ciegas Q5 / Q4 | pendiente | `resultados_ciegas_q4.md`: 20 vacías, sin commit |
| 22 | Reducir el margen de RAM en la recarga WSL (99,96 % de uso) | pendiente | `resultados_swa_y_recursos.md` |

## Con el usuario delante

Ver [[pendientes-presenciales]]. Ese estado no se puede comprobar desde el repositorio.
