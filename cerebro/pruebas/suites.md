---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [probar_protecciones_ejecucion.py, probar_obstaculos.py, probar_modo_directo.py, probar_fase6.py, probar_fase7.py, probar_campo_isla.py, probar_autocompletar_login.py, probar_confirmacion_voz.py, probar_modo_juego.py, probar_palabra_activacion.py, probar_seguimiento.py, probar_segundo_plano.py, probar_actividad_fisica.py, probar_powershell.py, probar_apps.py, probar_grupo4.py, SRS.md]
---
# Suites de pruebas sin modelo

Se corren con `.venv\Scripts\python <suite>`. No cargan Gemma ni Whisper, salvo con las opciones indicadas.
**Cuidado:** importar `agente_minimo` carga el modelo (línea `llm = crear_llm(...)`), así que una prueba nueva sin
modelo no debe importarlo.

La baseline es el último total registrado en un mensaje de commit. Nadie volvió a correrlas después de 9e2c1f1, que
cambió `agente_minimo.py`, `herramientas.json` y `herramientas_grupo4.py` ([[backlog]]).

| Suite | Cubre | Baseline (commit) |
|---|---|---|
| `probar_protecciones_ejecucion.py` | Afirmaciones sin evidencia, atajos como texto, dos alternativas | 25/25 según `REPORTE_TRABAJO_CACAO.md`; **sin verificar** en un commit |
| `probar_obstaculos.py` | Efecto de clics y atajos, tabla de obstáculos | 35/35 (99fd1bc) |
| `probar_modo_directo.py` | Política del modo sin confirmación | 138/138 (99fd1bc) |
| `probar_fase6.py [seccion…]` | Hábitos, wiki, reflexión con modelo falso, sugerencias, lint (vault y bases temporales) | 142/142 (99fd1bc) |
| `probar_fase7.py` | A: confirmaciones físicas e inyectadas, WebSocket. B: **isla real**. C: clic inyectado | A 26/26 (99fd1bc); B 13/13 y C 5/5 (491b45e / d80ea7f) |
| `probar_campo_isla.py` | Campo de texto de la isla, lado del agente | 29/29 (99fd1bc) |
| `probar_autocompletar_login.py` | Autocompletado con Chrome simulado | 46/46 (99fd1bc) |
| `probar_confirmacion_voz.py` | «confirmo la instrucción» | 33/33 (99fd1bc) |
| `probar_modo_juego.py` | Lógica con juego simulado; `--medir` **carga modelos** | 32/32 (6d4825d) |
| `probar_palabra_activacion.py` | Detector «Cacao» con audio de prueba | 41/41 (6d4825d) |
| `probar_seguimiento.py` | Escucha de 8 s | 35/35 (6d4825d) |
| `probar_segundo_plano.py` | Lanzador, registro, avisos, instancia única | 23/23 (99fd1bc) |
| `probar_actividad_fisica.py` | Raw Input, periodos dudosos | 29/29 (bfa46ee) |
| `probar_powershell.py` | Planificador, patrones, tiempo máximo; `--modelo` **carga Gemma** | 59/59 (aa4c561) |
| `probar_apps.py`, `probar_grupo4.py` | Elección de apps; planes del grupo 4 | sin total registrado (**desconocido**) |

**Atención con `probar_fase7.py` B:** abre la isla real. Solo con el usuario presente o con permiso.

## Orden recomendado tras un cambio

1. Las suites del módulo tocado.
2. `probar_protecciones_ejecucion.py`, `probar_obstaculos.py` y `probar_modo_directo.py` (núcleo de seguridad).
3. Si cambió el prompt, el esquema o las herramientas: [[evaluacion-65-frases]] (con modelo).

Con modelo y GPU: [[suites-con-modelo]].
