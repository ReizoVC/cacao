---
estado: verificado
verificado_commit: d4b36dd
verificado_fecha: 2026-10-10
fuentes: [memoria.py, wiki.py, reflexion.py, lint.py, sugerencias.py, deteccion.py, obstaculos.py, config.json, diseno_fase6.md]
---
# Memoria, wiki, reflexión y sugerencias

Diseño completo: `diseno_fase6.md`, con el patrón «LLM Wiki»: fuentes → ingest → wiki → lint.

## Capas

1. **`memoria.db`** (SQLite, `memoria.py`), con las tablas:
   - `memorias` (`recordar`; `origen` lo pone el ejecutor, nunca el modelo);
   - `obstaculos` ([[protecciones]]);
   - sugerencias y bloqueos (`sugerencias.py`).

   Las memorias de tipo preferencia y alias van al prompt (`memorias_para_prompt`).
2. **`habitos.db`**: la capa de fuentes ([[registro-habitos]]).
3. **Wiki:** vault de Obsidian en `memoria/` (`config.memoria_wiki.vault`), con su propio git local sin remoto.
   Contiene páginas del esquema (`wiki_esquema.json`), `index.md`, `log.md`, `mis_notas/` (texto del usuario) y
   `fuentes/` (nunca se usa como fuente).

Las tres son datos personales: **no las leas** ([[mapa-datos]]).

## consultar_memoria

`memoria.consultar_memoria()` busca:
- en `memorias`, por similitud difusa;
- en la wiki, con `wiki.buscar()`, que recorre solo `VAULT = BASE / "memoria"`.

`cerebro/` está fuera de ese alcance ([[mantenimiento]]).

## Reflexión diaria (`reflexion.py`)

- **Cuándo arranca:** con inactividad física, sin juego, sin pantalla completa, sin audio que bloquee y con poca GPU
  (`deteccion.py`, `memoria_wiki.reflexion`).
- **Cuándo se detiene:** con cualquier entrada o señal (la vigilancia `Guardia`).
- **Qué hace:** el código resume y mide; el modelo redacta frases por página con gramática; un filtro sensible
  revisa; se escribe por secciones y se hace commit en el git del vault.
- **El texto del usuario es verdad:** lo que lo contradice se omite y queda en `log.md`.

## Revisión semanal (`lint.py`)

Cada `lint_dias` = 7. El código arregla lo mecánico; el modelo solo propone contradicciones en `revision.md`.

## Sugerencias (`sugerencias.py`)

- Candidatas calculadas por el código a partir de los hábitos: como máximo 2 al día, con 2 h de separación.
- Solo se muestran al final de una respuesta; nunca ejecutan nada.
- Se bloquean con la herramienta `sugerencias`; tras 3 ignoradas seguidas, se pausan 30 días.

## Seguridad

- La wiki solo se alimenta de lo que dice el usuario, `recordar` y los hábitos; nunca de salidas de herramientas.
- Un `recordar` en una tarea contaminada pide confirmación ([[permisos-y-bloqueos]]).

## Pruebas

`probar_fase6.py` (sin modelo, con vault y bases temporales), `probar_memoria.py` y `probar_reflexion.py` (con
modelo real) ([[suites]]).
