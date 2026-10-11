---
estado: verificado
verificado_commit: d4b36dd
verificado_fecha: 2026-10-10
fuentes: [probar_protecciones_ejecucion.py, probar_obstaculos.py, probar_modo_directo.py, probar_fase6.py, probar_fase7.py, probar_campo_isla.py, probar_autocompletar_login.py, probar_confirmacion_voz.py, probar_modo_juego.py, probar_palabra_activacion.py, probar_seguimiento.py, probar_segundo_plano.py, probar_actividad_fisica.py, probar_powershell.py, probar_apps.py, probar_grupo4.py, probar_carga_modelo.py, probar_salida_utf8.py, probar_gramatica_json.py, agente_minimo.py, comparacion_modelos/verificar.py]
---
# Suites de pruebas sin modelo

Se corren con `.venv\Scripts\python <suite>`. No cargan Gemma ni Whisper, salvo con las opciones indicadas.
Desde 14c17cb, importar `agente_minimo` (o `voz`) **ya no carga el modelo**: lo carga `cargar_modelo()`. Antes,
`probar_fase7.py` A (`pruebas_rechazo`) y `probar_modo_juego.py` (`pruebas_filtrar_en_pausa`) cargaban Gemma sin
avisar.

**Línea base:** todas pasadas el 2026-10-10 en eb5a9c4 (después de 9e2c1f1 y de la Fase 1), con
`PYTHONIOENCODING=utf-8`. Las salidas no se guardaron en el repositorio; las cifras salen de la ejecución de ese día
([[log]]).

| Suite | Cubre | Baseline |
|---|---|---|
| `probar_protecciones_ejecucion.py` | Afirmaciones sin evidencia (también los falsos positivos), atajos como texto, dos alternativas | 44/44 |
| `probar_obstaculos.py` | Efecto de clics y atajos, tabla de obstáculos | 35/35 |
| `probar_modo_directo.py` | Política del modo sin confirmación | 138/138 |
| `probar_fase6.py [seccion…]` | Hábitos, wiki, reflexión con modelo falso, sugerencias, lint (vault y bases temporales) | 142/142 |
| `probar_fase7.py A` | Confirmaciones físicas e inyectadas (simuladas), WebSocket, rechazo con el agente | 26/26 (≈40 s por esperas de 30 s) |
| `probar_fase7.py B` / `C` | B: **isla real**. C: **clic inyectado de verdad** en la isla | no se corren sin permiso; últimas: 13/13 y 5/5 (491b45e / d80ea7f) |
| `probar_campo_isla.py` | Campo de texto de la isla, lado del agente | 29/29 |
| `probar_autocompletar_login.py` | Autocompletado con Chrome simulado | 46/46 |
| `probar_confirmacion_voz.py` | «confirmo la instrucción» | 33/33 |
| `probar_modo_juego.py` | Lógica con juego simulado; `--medir` **carga modelos** | 32/32 |
| `probar_palabra_activacion.py` | Detector «Cacao» con audio de prueba (CPU) | 41/41 |
| `probar_seguimiento.py` | Escucha de 8 s | 35/35 |
| `probar_segundo_plano.py` | Lanzador, registro, avisos, instancia única | 23/23 |
| `probar_actividad_fisica.py` | Raw Input, periodos dudosos | 29/29 |
| `probar_powershell.py` | Planificador, patrones, tiempo máximo; `--modelo` **carga Gemma** | «TODO OK», 54 líneas OK. El 59/59 de aa4c561 era la corrida `--modelo` |
| `probar_apps.py` | Elección de apps contra `apps_categorias.json` (datos personales: mira solo el total) | «TODO OK», 72 líneas OK |
| `probar_grupo4.py` | Planes del grupo 4 | «TODO OK», 51 líneas OK |
| `probar_carga_modelo.py` | Importar sin modelo, `cargar_modelo()`, orden del arranque, `swa_full` | 13/13 |
| `probar_salida_utf8.py` | UTF-8 en `voz.py` y en el modo texto sin el lanzador | 6/6 |
| `probar_gramatica_json.py` | Regla `char` estricta: lee **solo el vocabulario** del GGUF (sin pesos, 0 capas en la GPU) y pasa respuestas por el muestreador de gramática | 11/11 |
| `comparacion_modelos`: `probar_criterios` | Criterio oficial del banco (`python -m unittest`, desde esa carpeta) | 7/7 |
| `comparacion_modelos`: `probar_integracion` | Contrato de las rondas 2 y 3. Necesita `jsonschema`, que solo está en `.venv-pruebas` | 4/4 con `.venv-pruebas`; con `.venv`, error de importación |

**Atención con `probar_fase7.py`:** sin argumentos corre A y B. Corre `probar_fase7.py A`, salvo con el usuario
presente o con permiso.

`comparacion_modelos/verificar.py` no es una suite: falla a propósito si cambia producción ([[comparacion-modelos]]).

## Orden recomendado tras un cambio

1. Las suites del módulo tocado.
2. `probar_protecciones_ejecucion.py`, `probar_obstaculos.py` y `probar_modo_directo.py` (núcleo de seguridad).
3. Si cambió el prompt, el esquema o las herramientas: [[evaluacion-65-frases]] (con modelo).

Con modelo y GPU: [[suites-con-modelo]].
