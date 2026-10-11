---
estado: verificado
verificado_commit: d4b36dd
verificado_fecha: 2026-10-10
fuentes: [agente_minimo.py, comparacion_modelos/integracion.py, resultados_comparacion_modelos.md, resultados_swa_y_recursos.md, iniciar_cacao.py, modelo.py, voz.py]
---
# Cierre rápido con mensaje_final y contrato de las rondas 2 y 3

**Estado: decidido por el usuario (2026-10-11), pendiente de implementar.**
- En los dos modelos, `mensaje_final` pasa por `validar_finalizacion`: si afirma algo sin verificar, no se usa y la
  tarea sigue.
- En el perfil de Qwen el cierre rápido se apaga, como en el banco. Sin cambiar el prompt ni el esquema: el ejecutor
  ignora `mensaje_final`.
- **Motivo:** Qwen en producción (semilla 11) usó `mensaje_final` tras el primer paso en #29, #30, #31 y #34 y
  confirmó lo que no hizo. Esa ruta se saltaba `validar_finalizacion`.

Antes había una diferencia abierta entre producción y el banco de pruebas:

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

## Qué hay en producción (comprobado en el código)

| Cambio | En producción |
|---|---|
| Regla JSON sin caracteres de control | Sí desde 7d31aa7: `modelo.py` cambia la regla en el proceso (`.venv` no se toca); `probar_gramatica_json.py` |
| UTF-8 | Sí: el lanzador (`PYTHONIOENCODING`) y, desde 8e72787, `agente_minimo.salida_utf8()` en `voz.py` y en el modo texto |
| Contrato sin cierre rápido | Decidido el 2026-10-11 (arriba), sin implementar |

## Consecuencia

Las cifras de las rondas 2 y 3 valen para el contrato de pruebas, no para el agente tal como está hoy. Si se lleva
el contrato a producción:
- cambia el prompt y el esquema → volver a pasar las 65 frases;
- cuesta una llamada más en los pedidos de un paso.

Pendiente de decidir: [[backlog]].
