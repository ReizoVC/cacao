---
estado: verificado
verificado_commit: 829fea9
verificado_fecha: 2026-10-11
fuentes: [comparacion_modelos/resumen_ronda3.json, comparacion_modelos/resumen_qwen9b_2026-10-11.json, comparacion_modelos/probar_swa_cache.py, config.json, modelo.py, clasificacion_fallos_qwen.md, comparacion_modelos/ronda3_protocolo.md]
---
# Qwen 3.5 9B como cerebro

**Decisión:** probado en producción de forma reversible por decisión del usuario (2026-10-11), **no pasó y se
volvió a Gemma** (829fea9). El perfil `qwen9b` sigue en `config.json` ([[configuracion-vigente]]). La evaluación a
ciegas Gemma/Qwen se **descartó** (el usuario la considera redundante con la prueba de uso).

## Historia

1. **Ronda 3** (`resumen_ronda3.json`): Qwen 189/195 frente a 195; criterio ≥ 192 y 0 acciones distintas.
   No pasó.
2. **Contrato de la ronda 2, mismo código** (2026-10-11, [[resultado-qwen9b-2026-10-11]]): 189/195, VRAM pico
   7 781 frente a 13 076 MiB. Un caso (c), #56 s22: escaló a `cerrar_app` con `forzar: true` sin que se pidiera.
   No pasó.
3. **Producción, perfil `qwen9b`** (17bb46c). Mismo prompt y esquema que Gemma, con `mensaje_final`.
   `probar_swa_cache.py A --casos todos` con semillas 11, 22 y 33. **58 / 58 / 57 = 173/195**, por debajo del mínimo
   de 185. Gemma da 194/195 (`resumen_65x3_C.json`). Vuelta a Gemma.

## Blindajes nacidos de estas pruebas (protegen a los dos modelos)

- 0a3ea28: `cerrar_app` ignora `forzar` si el pedido no lo pide ([[protecciones]] §4). En la corrida 3 no se repitió
  ningún `forzar`.
- e9a580d: `listar_controles` con id ausente, 0 o inexistente usa la ventana al frente.

## Por qué falló en producción

El cierre rápido `mensaje_final` se saltaba `validar_finalizacion`. En pedidos de dos pasos, Qwen hacía el primero y
cerraba afirmando los dos. Ejemplo: #30, en las tres semillas, «abrí la Calculadora y puse el volumen al 20%» sin
tocar el volumen. Son 6 confirmaciones falsas (c). Detalle en [[resultado-qwen9b-2026-10-11]].
El banco quitaba `mensaje_final` (contrato de la ronda 2): por eso allí no se vio. Decisión del usuario, pendiente
de implementar: validar `mensaje_final` en los dos modelos y apagarlo en Qwen ([[cierre-rapido-mensaje-final]]).

## No hacer

- No volver a activar `qwen9b` antes de implementar esa decisión y repetir la 65 × 3 con producción.
- No reabrir Qwen solo por velocidad o VRAM sin un criterio fijado de antemano.
