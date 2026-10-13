---
estado: verificado
verificado_commit: f83dd1a
verificado_fecha: 2026-10-13
fuentes: [agente_minimo.py, config.json, probar_cierre_rapido.py, benchmark_gramatica.py, comparacion_modelos/integracion.py, resultados_comparacion_modelos.md, resultados_swa_y_recursos.md, iniciar_cacao.py, modelo.py, voz.py]
---
# Cierre rápido con mensaje_final y contrato de las rondas 2 y 3

**Estado: implementado (2026-10-11)**, por decisión del usuario.
- **69297e4, los dos modelos:** `mensaje_final` pasa por `validar_finalizacion`. Si afirma algo sin verificar, se
  descarta, la corrección entra en el historial y la tarea sigue. Cuenta en `correcciones` como `finalizar`; con
  2, la tarea termina preguntando.
- **d95855d, por perfil:** `"cierre_rapido"` en `config.json`, true en `gemma` y false en `qwen9b`. Con false, el
  ejecutor ignora `mensaje_final` y exige `finalizar`. El prompt y el esquema no cambian.
- **Pruebas:** `probar_cierre_rapido.py` 13/13, con los textos de Qwen. Rechaza las 6 confirmaciones falsas.
- **Límite conocido:** #29, #31 y #34 de la semilla 11 («…y abro Spotify», «Ahora abro…», o solo el volumen) no
  afirman nada falso. La validación los acepta aunque la tarea quede a medias. Por eso, en Qwen, el cierre rápido
  está apagado. No se ampliaron los patrones de `_CLAIMS`.
- **Motivo:** Qwen en producción (17bb46c) usó `mensaje_final` tras el primer paso y confirmó lo que no hizo
  ([[resultado-qwen9b-2026-10-11]]).

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
| Contrato sin cierre rápido | Solo en el perfil `qwen9b` (d95855d); `mensaje_final` siempre validado (69297e4) |

## Consecuencia

Las cifras de las rondas 2 y 3 valen para el contrato de pruebas, no para producción: allí el prompt y el esquema
no tenían `mensaje_final`. En producción el prompt y el esquema siguen con `mensaje_final`; en `qwen9b` el ejecutor
lo ignora, y eso cuesta una llamada más en los pedidos de un paso. Las 65 frases se repiten con cada perfil
([[evaluacion-65-frases]]).

Backlog #4: hecho ([[backlog]]).
