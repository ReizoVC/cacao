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

## 2026-10-10: Fase 1 de producción (14c17cb, 7d31aa7, 8e72787, c6a74f3, eb5a9c4)

- **Código:**
  - carga perezosa con `cargar_modelo()`;
  - regla JSON estricta en `modelo.py`;
  - `salida_utf8()` en `voz.py` y en el modo texto;
  - detector de afirmaciones por cláusula, sin los falsos positivos;
  - `swa_full: false` preparado (Cacao sin reiniciar y sin medir).
- **Suites nuevas:** `probar_carga_modelo.py`, `probar_salida_utf8.py` y `probar_gramatica_json.py`.
- **Suites sin modelo:** todas pasan. Totales en `suites.md` (backlog #7).
- **`verificar.py`:** falla de verdad desde 84fbe0b y 5889dda (hashes de la ronda 3). No se ejecutó tal cual,
  porque reescribe `integridad.json`. El detalle está en `comparacion-modelos` (backlog #10).
- **Páginas con errores o atrasadas ya antes del cambio (6):**
  - `backlog`: UTF-8 marcado «hecho», #9 y #10;
  - `swa-full-false` y `comparacion-modelos`: «sin commit» tras cabf3ed;
  - `suites`: el 59/59 de PowerShell era la corrida con modelo, y `probar_fase7` A y `probar_modo_juego` cargaban
    Gemma;
  - `lecciones`: «las suites no lo importan» era falso;
  - `mapa-archivos`: faltaban el informe de cabf3ed y `verificar.py`.
- **Páginas actualizadas por el cambio (9):** `protecciones`, `cierre-rapido-mensaje-final`, `configuracion-vigente`,
  `voz`, `arrancar-detener`, `riesgos`, `pendientes-presenciales`, `motor-llama-cpp` y `vision-general`. Otras 15 se
  revisaron sin cambios de contenido; solo se actualizó su commit verificado.
- **Huecos que obligaron a leer código:**
  - la importación de `agente_minimo` también ejecutaba `sincronizar_apps()`;
  - dónde está `verificar.py`;
  - qué suites importaban `agente_minimo`;
  - `jsonschema` solo está en `.venv-pruebas`.
- **Backlog:** 11 temas pedidos no tienen rastro en el repositorio. Quedan como desconocidos.
- **Frescura:** 0 páginas por revisar tras el cambio.
