# Registro del cerebro

Una entrada por tarea, la más reciente al final: fecha, qué cambió y commit.

## 2026-10-10: creación del cerebro

- **Contenido:** `CLAUDE.md` y `cerebro/` con arquitectura, decisiones, modelos, pruebas, estado y operación.
- **Verificación:** todas las páginas contra el código en 10b63cc.
- **Sin verificar:** `gemma-26b`, `criterio-de-cambio` y `pendientes-presenciales`, además de las líneas que citan
  `REPORTE_TRABAJO_CACAO.md`.
- **Hallazgos:**
  - la regla raíz `modelos/` ignoraba `cerebro/modelos/` (se reincluyó en `cerebro/.gitignore`);
  - la lista del backlog no venía en el pedido, así que se armó con los pendientes documentados.
- **Commits:**
  - 1b7da5b: CLAUDE.md y arquitectura;
  - 95c663b: decisiones y modelos;
  - 6e7fa9f: pruebas y estado;
  - 8b8c4ec: operación, índice, log y `frescura.py`;
  - d6fc896: arreglo de `frescura.py`.

## 2026-10-10: verificación de navegación

Páginas leídas después de `CLAUDE.md` e `index.md`, en cinco preguntas. En ninguna hizo falta reorganizar.

| Pregunta | Páginas |
|---|---|
| ¿Dónde se decide si una acción pide confirmación? | 1: `permisos-y-bloqueos` |
| ¿Qué cambiaría para añadir una herramienta nueva? | 1: `agente-y-herramientas` |
| ¿Por qué Q4 no está en producción y qué falta para cambiar? | 2: `gemma-q4-por-ahora`, `criterio-de-cambio` |
| ¿Cómo pruebo un cambio del modo sin confirmación sin tocar el PC? | 1: `suites` |
| ¿Puede Cacao leer `cerebro/`? | 1: `riesgos` |

**Tamaño:** `CLAUDE.md` (67 líneas) más `index.md` suman unos 1.800–2.300 tokens. Es una estimación por caracteres
(entre 4 y 3,2 por token); no se usó el tokenizador real.

**Frescura:** `frescura.py` solo avisa de los cambios sin commit de `comparacion_modelos/ejecutar.py`, que son
trabajo previo pendiente (backlog #9).

## 2026-10-10: liberación de espacio en C: (0b90b51, 4daa737, 16e25a8)

- Datos de entrenamiento de «Cacao» movidos a `D:\Cacao\entrenamiento\`, con SHA256 verificado y manifiesto en
  `D:\Cacao\manifiesto_movimientos.md`.
- Borrados, porque se regeneran: la caché de pip y `target\debug` de la isla.
- Qwen 3.5 9B Q5 copiado a `modelos/comparacion_local/`. `modelos/comparacion/` es una unión a D: (00c36fb).
- Otra sesión cambió producción en paralelo: 8e72787, 14c17cb, c6a74f3, 7d31aa7 y eb5a9c4. El backlog ya lo
  refleja. **Hay 29 páginas por volver a verificar** (`frescura.py`).
