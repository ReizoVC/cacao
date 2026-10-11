---
estado: verificado
verificado_commit: 8a78d51
verificado_fecha: 2026-10-11
fuentes: [SRS.md, protecciones_ejecucion.py, herramientas.json, herramientas_powershell.py, resultados_swa_y_recursos.md, muestreo_gramatica.py, wiki.py, herramientas_grupo1.py]
---
# Riesgos vigentes

La lista completa con mitigaciones está en `SRS.md` §8 (R-01 a R-23). Aquí, los que más afectan al trabajo de
Claude Code, más los nuevos.

| Riesgo | Por qué importa | Mitigación / estado |
|---|---|---|
| Inyección desde archivos, web o pantalla (R-01) | El modelo lee contenido externo | Tarea contaminada; confirmaciones; en el modo sin confirmación lo externo vuelve a preguntar ([[permisos-y-bloqueos]]) |
| PowerShell no es un sandbox (R-08) | Alias y ofuscación | La barrera es la confirmación; siempre pregunta |
| Otra persona frente al PC (R-16) | Cualquiera puede confirmar con Enter o con la voz | Costumbre: apagar la escucha y el modo |
| Actualizar llama-cpp-python rompe `LlamaRapida` y la visión (R-06) | Partes internas de 0.3.36 | Versión fijada ([[motor-llama-cpp]]) |
| Windows Insider (R-07) | Cambios de API | Volver a probar tras cada actualización grande |
| Falsos positivos de la protección | Respuestas correctas rechazadas que acaban confusas | Corregidos en c6a74f3. Queda un falso negativo conocido con una negación anterior en la misma cláusula ([[protecciones]]) |
| Producción ≠ banco de pruebas | Las cifras de las rondas 2 y 3 no describen producción | [[cierre-rapido-mensaje-final]] |
| `swa_full=False` y la regla JSON sin medir en producción | Se aplican en el próximo arranque de Cacao. La VRAM real y las 65 frases no se han medido | [[swa-full-false]], [[backlog]] |
| `verificar.py` falla | Congela la producción de la ronda 3, que ya cambió | Esperado; actualizar los hashes es decisión del usuario ([[comparacion-modelos]]) |
| RAM al recargar la pila WSL | Windows llegó al 99,96 %; 1,15 GiB de swap en WSL | Medido en `resultados_swa_y_recursos.md` |
| Margen de VRAM en la pila WSL | 1,5–1,9 GiB libres en el pico | Modo juego; no reducir Whisper ni el contexto |
| Licencia de assets de la isla (R-13) | La isla adapta Coucou | Uso personal; repositorio sin publicar. En `AGENTS.md` de la isla: sin remoto ni distribución |
| Bandeja de la isla sin clic físico | «Permitir capturas» quitaba la exclusión de capturas con cualquier clic | Cerrado (b15a349; isla 5554214), compilado y probado en físico el 2026-10-11: un clic inyectado sobre el menú no hace nada ([[compilar-isla]]) |
| Volver a la isla v1 | Exige revertir también 8a78d51 en Cacao (si no, 4003) | Procedimiento y respaldo en [[compilar-isla]]. La v2 se probó en físico el 2026-10-11 |
| La isla en manos de otro agente (Codex) | Podría romper un invariante o el protocolo | Rama `codex/isla`, archivos PROTEGIDOS y `probar_invariantes.py` ([[isla-websocket]]) |

## Alcance de `cerebro/` frente a Cacao (comprobado en el código)

| Vía | ¿Alcanza `cerebro/`? |
|---|---|
| `consultar_memoria` | No: busca en `memoria.db` y `wiki.buscar()` |
| `wiki.py`, `lint.py`, `reflexion.py` | No: `VAULT = BASE / "memoria"` |
| `listar_carpeta`, `leer_archivo`, `mover_archivo` | No: solo `carpetas_permitidas` del perfil, y `C:\asistente` no está entre ellas |
| `ejecutar_powershell` | **Sí, en teoría**: un `Get-Content` no está bloqueado por ruta. Necesita confirmación física |
| `ver_pantalla` | Si el usuario tiene una página del cerebro abierta en pantalla, el modelo la vería |

Por eso el cerebro no debe contener datos personales ni secretos ([[mantenimiento]]).
