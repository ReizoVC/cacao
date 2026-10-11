---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [protecciones_ejecucion.py, agente_minimo.py, herramientas_grupo4.py, obstaculos.py, emergencia.py, resultados_swa_y_recursos.md]
---
# Protecciones del ejecutor

Son deterministas: no dependen del modelo. Se añadieron en el commit 9e2c1f1 y se reforzaron en 5889dda.

## 1. Sin efecto verificado, no hay «hecho»

- `resultado_verificado()` acepta un resultado como evidencia según la herramienta (`volumen_actual`,
  `app_abierta`, `cerrada`, `ruta_final`…, o `efecto_visible`).
- `afirmaciones_sin_evidencia(mensaje, verificadas)` busca con las expresiones regulares de `_CLAIMS` («cerré»,
  «moví», «escribí», «desplacé», «volumen al 40 %»…) y excluye las cláusulas negadas (`_NEGATED_CLAIM`).
- En `atender()`, un `finalizar` con afirmaciones sin evidencia recibe una corrección. Con 2 correcciones, la tarea
  termina preguntando al usuario.
- Además, un clic o atajo sin comprobar (`sin_verificar`) obliga a comprobarlo, como máximo 2 recordatorios.

**Falsos positivos conocidos** ([[riesgos]]):
- «escrita» coincide con `escrit[oa]`;
- «sonido … está» activa el patrón de volumen;
- «no he podido» y «no puedo» no cuentan como negación, porque `_NEGATED_CLAIM` solo reconoce «no pude», «no
  logré»…

Hay casos con las tres formas en `resultados_swa_y_recursos.md`.

## 2. Dos alternativas fallidas, alto

`registrar_resultado()` acumula los fallos distintos de la tarea (no cuenta las lecturas, salvo listar_controles,
ni los bloqueos o rechazos). Con 2, la tarea se corta: «Probé dos alternativas…».

## 3. Atajos solo estructurados

`parece_atajo()` detecta «Ctrl+G», «Alt+F4»… escritos como texto. La herramienta `teclado` los rechaza; los atajos
van con `accion: "atajo"` y el arreglo `teclas` (`herramientas_grupo4.py`).

## Relacionadas

- **Obstáculos** (`obstaculos.py`): si un atajo o clic no tuvo efecto visible y otra acción en la misma app sí lo
  tuvo, el código guarda el camino alternativo en `memoria.db` (tabla `obstaculos`). Nunca lo escribe a partir de
  contenido externo.
- **Bloqueo:** un resultado con `bloqueado: true` corta la tarea (`terminar`) sin ofrecer otro camino.
- **Emergencia** (`emergencia.py`): Ctrl+Alt+Shift+Q con `RegisterHotKey`. Se comprueba en cada token, antes de
  cada paso y dentro de `teclado`. Deja el agente detenido hasta «reanudar».

## Pruebas

`probar_protecciones_ejecucion.py` y `probar_obstaculos.py` (ver [[suites]]). El banco de comparación las aplica
igual (`comparacion_modelos/ejecutar.py`).
