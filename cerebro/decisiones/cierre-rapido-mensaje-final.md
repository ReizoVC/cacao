---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [agente_minimo.py, comparacion_modelos/integracion.py, resultados_comparacion_modelos.md, resultados_swa_y_recursos.md, iniciar_cacao.py]
---
# Cierre rápido con mensaje_final y contrato de las rondas 2 y 3

**Estado:** hay una **diferencia abierta entre producción y el banco de pruebas**.

## En producción (`agente_minimo.py`)

- `ESQUEMA_ACCION` acepta `mensaje_final` opcional en cualquier acción.
- Si la acción quedó verificada, no hay imagen ni un clic o atajo sin comprobar, el bucle termina con ese mensaje
  sin otra llamada al modelo.

## En las rondas 2 y 3 (`comparacion_modelos/integracion.py`)

- Se excluye `mensaje_final` y se exige siempre `finalizar` con `oneOf` (mensaje no vacío y `exito`).
- La regla `char` de la gramática excluye los caracteres de control U+0000–U+001F (un salto de línea literal rompía
  `json.loads`).
- La salida es UTF-8 (antes había `UnicodeEncodeError` al imprimir).

## Por qué

El piloto documentó que `mensaje_final` terminaba toda la tarea después de una sola acción en pedidos de varias
(#29, #30, #31 y #34) (`resultados_comparacion_modelos.md`, ronda 2).

## Qué hay en producción (comprobado en `resultados_swa_y_recursos.md` §4)

| Cambio | En producción |
|---|---|
| Regla JSON sin caracteres de control | No (la regla de `.venv` sigue igual) |
| UTF-8 | Sí, al arrancar desde el lanzador (`iniciar_cacao.py` pone `PYTHONIOENCODING`) |
| Contrato sin cierre rápido | No |

## Consecuencia

Las cifras de las rondas 2 y 3 valen para el contrato de pruebas, no para el agente tal como está hoy. Si se lleva
el contrato a producción:
- cambia el prompt y el esquema → volver a pasar las 65 frases;
- cuesta una llamada más en los pedidos de un paso.

Pendiente de decidir: [[backlog]].
