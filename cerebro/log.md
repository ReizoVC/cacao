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
