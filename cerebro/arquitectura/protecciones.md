---
estado: verificado
verificado_commit: 76250a2
verificado_fecha: 2026-10-11
fuentes: [protecciones_ejecucion.py, probar_protecciones_ejecucion.py, probar_modo_directo.py, probar_grupo4.py, agente_minimo.py, herramientas_grupo4.py, obstaculos.py, emergencia.py, resultados_swa_y_recursos.md]
---
# Protecciones del ejecutor

Son deterministas: no dependen del modelo. Se añadieron en el commit 9e2c1f1, se reforzaron en 5889dda y el
detector de afirmaciones se rehízo en c6a74f3.

## 1. Sin efecto verificado, no hay «hecho»

- `resultado_verificado()` acepta un resultado como evidencia según la herramienta (`volumen_actual`,
  `app_abierta`, `cerrada`, `ruta_final`…, o `efecto_visible`).
- `afirmaciones_sin_evidencia(mensaje, verificadas)` busca candidatas con los patrones de `_CLAIMS`. Cada patrón
  marca con `(?P<v>…)` la palabra que afirma la acción. Después, `_afirma()` analiza la frase:
  - descarta las preguntas y las frases con «no puedo / no he podido verificar…» (`_SIN_COMPROBAR`);
  - descarta un negador («no», «nunca», «ni», «sin»…) dentro de la misma cláusula. Las cláusulas se separan por
    puntuación y por «pero», «y», «aunque»…;
  - descarta el subjuntivo («se haya cerrado») y los infinitivos;
  - un participio solo cuenta con auxiliar («he escrito», «quedó guardado», «está cerrada») o al final de una
    cláusula corta sin cópula («Calculadora abierta.»);
  - descarta «de sonido» sin artículo («Grabadora de sonido», «tarjeta de sonido»).
- En `atender()`, un `finalizar` con afirmaciones sin evidencia recibe una corrección. Con 2 correcciones, la tarea
  termina preguntando al usuario.
- Además, un clic o atajo sin comprobar (`sin_verificar`) obliga a comprobarlo, como máximo 2 recordatorios.

**Falsos positivos corregidos** (casos de `resultados_swa_y_recursos.md`, ahora en la suite):
- «escrita» como adjetivo;
- «la Grabadora de sonido está instalada»;
- «no he podido» y «no puedo verificar».

**Límite conocido (falso negativo):** una negación anterior en la misma cláusula también anula la afirmación
(«La ventana que no respondía la cerré» no se detecta). Hay que tenerlo en cuenta si se amplía la lista de
negadores.

## 2. Dos alternativas fallidas, alto

`registrar_resultado()` acumula los fallos distintos de la tarea (no cuenta las lecturas, salvo listar_controles,
ni los bloqueos o rechazos). Con 2, la tarea se corta: «Probé dos alternativas…».

## 3. Atajos solo estructurados

`parece_atajo()` detecta «Ctrl+G», «Alt+F4»… escritos como texto. La herramienta `teclado` los rechaza; los atajos
van con `accion: "atajo"` y el arreglo `teclas` (`herramientas_grupo4.py`).

## 4–6. Frenos de cerrar_app y listar_controles

Desde 2026-10-11: [[frenos-cierre]] (`forzar` no pedido, `listar_controles` sin ventana válida y `cerrar_app` sin
intención de cerrar).

## Relacionadas

- **Obstáculos** (`obstaculos.py`): si un atajo o clic no tuvo efecto visible y otra acción en la misma app sí lo
  tuvo, el código guarda el camino alternativo en `memoria.db` (tabla `obstaculos`). Nunca lo escribe a partir de
  contenido externo.
- **Bloqueo:** un resultado con `bloqueado: true` corta la tarea (`terminar`) sin ofrecer otro camino.
- **Emergencia** (`emergencia.py`): Ctrl+Alt+Shift+Q con `RegisterHotKey`. Se comprueba en cada token, antes de
  cada paso y dentro de `teclado`. Deja el agente detenido hasta «reanudar».

## Pruebas

- `probar_protecciones_ejecucion.py`: 94/94 en 98c763e (también `forzar`, el freno de cerrar y las 65 + 30 frases);
  `probar_modo_directo.py` 143/143 (cableado en `ejecutar`); `probar_grupo4.py` con ventanas simuladas (e9a580d).
- `probar_obstaculos.py`.

Detalles en [[suites]]. El banco de comparación las aplica igual (`comparacion_modelos/ejecutar.py`). Las cifras de
las rondas 2 y 3 se midieron con el detector anterior.
