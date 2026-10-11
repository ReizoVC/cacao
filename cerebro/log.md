# Registro del cerebro

Una entrada por tarea, la más reciente al final: fecha, qué cambió y commit.

Entradas anteriores: [[log-2026-10-10]], [[log-2026-10-11-isla]], [[log-2026-10-11-b]] y [[log-2026-10-11-c]].

## 2026-10-11: blindajes, Qwen 9B en producción (reversible) y memoria liberable

- 0a3ea28: `cerrar_app` ignora `forzar` si el pedido no lo pide. e9a580d: `listar_controles` usa la ventana al
  frente si el id falta o no existe (backlog #11e y #11f). Página `protecciones` §4–5.
- 17bb46c (permiso del usuario): `config.json` con `modelo_activo` y perfiles `gemma` / `qwen9b`; `modelo.py`
  aplica el perfil y apaga el pensamiento de Qwen. `probar_carga_modelo.py` 23/23.
- 65 × 3 con producción y Qwen: 58/58/57 = 173/195, con 6 confirmaciones falsas con `mensaje_final`. 829fea9:
  vuelta a Gemma. Páginas `qwen-como-cerebro`, `resultado-qwen9b-2026-10-11` y backlog (#4, #5, #20, #24).
- Memoria liberable con Qwen (`medir_memoria.py`): pico de 10 424 MiB con todo; flash attention es casi todo el
  ahorro. Página nueva `memoria-liberable`.
- Cambios en `configuracion-vigente`, `comandos` (cómo volver a Gemma) y `swa-full-false` (solo en el perfil
  `qwen9b`).

## 2026-10-11: cierre rápido implementado; Qwen 182/195, Gemma 195/195

- 69297e4: `mensaje_final` pasa por `validar_finalizacion` en los dos modelos. Rechaza las 6 confirmaciones falsas
  de Qwen; acepta #29, #31 y #34 de s11, que no afirman nada falso (límite conocido, sin ampliar `_CLAIMS`).
- d95855d: `cierre_rapido` por perfil (gemma true, qwen9b false); `probar_cierre_rapido.py` 13/13,
  `probar_carga_modelo.py` 25/25.
- Qwen activo, 65 × 3 completa: 59/61/62 = 182/195 y un (c) (#19 s33 intentó cerrar Windows Terminal). No pasa.
- Gemma activo, 65 × 3 completa: 65/65/65 = 195/195. **Queda Gemma.**
- Páginas: `cierre-rapido-mensaje-final` (implementado), `qwen-como-cerebro`, `resultado-qwen9b-2026-10-11`,
  `evaluacion-65-frases`, `suites`, backlog (#4 hecho, #24), `swa-full-false`. 34 páginas revisadas tras los cambios
  de producción y re-selladas en d95855d.

## 2026-10-11: contrato de la ronda 2 en el perfil qwen9b; Qwen 182/195, no pasa

- f21e746 (permiso del usuario): `contrato_ronda2.py` y la clave `contrato_ronda2` (solo qwen9b).
  `probar_contrato_ronda2.py` 16/16: igual al `adjust` del banco; Gemma sin cambios byte a byte; el esquema rechaza
  `mensaje_final`.
- e3dfe04: el banco valida JSON con `oneOf`; la primera corrida se paró en el calentamiento por eso.
- 65 × 3 con qwen9b: 63/60/59 = 182/195 y dos (c) (#58 s22 y #43 s22). Vuelta a Gemma. El simulador de producción no
  mueve el foco (backlog #26). Páginas: `qwen-como-cerebro`, `resultado-qwen9b-produccion` §3,
  `configuracion-vigente`, `suites`, `mapa-archivos` y el backlog (#25, #26).

## 2026-10-11: freno de cerrar_app y Qwen 9B en uso real una semana

- 98c763e: `cerrar_app` solo si el pedido expresa intención de cerrar (`protecciones` §6). Las 4 frases de las
  65 + 30 que esperan `cerrar_app` pasan; #58 y #43 quedan frenados.
- 5e9eee0 (decisión del usuario): `modelo_activo` = `qwen9b` una semana, sin otra 65 × 3 y sin haber pasado el
  criterio. Vuelta atrás: `"gemma"`.
- 77370e8: `comparacion_modelos/resumir_semana_qwen.py` para el final de la semana (solo con `--con-permiso`; lee
  `registro_cacao.log`).
- Páginas: `qwen-como-cerebro`, `protecciones`, `configuracion-vigente` y el backlog (#27).

## 2026-10-11: rediseño de la isla, cargo check y voz

- Isla: rediseño de Codex (4ead7c5) en `main`; rama `claude/musica` con el panel de 800 (858d001) y `cargo check` limpio (3bfef0f).
- Página nueva `voz-candidatas`: investigación web de motores de voz en Windows nativo, sin medir.

## 2026-10-11: diseño del camino rápido y del filtrado de herramientas (sin código de producción)

- ef06fb8: `medir_prompt.py`. Prompt de sistema: Gemma 3 802 tokens y Qwen 4 141; las herramientas son el 75–80 %.
- Hallazgo: Qwen no reutiliza la caché de prefijo (0/593 llamadas) y recalcula ≈ 4 300 tokens por llamada
  (1,54 s); Gemma reutiliza ≈ 3 965 (100 %).
- Páginas nuevas (propuestas): `camino-rapido` (14 de las 95 frases), `filtrado-herramientas` (variante C y, antes,
  la caché por estados para Qwen) y `frases-simples`. `simular_filtrado.py`: 53 de 95 con el núcleo solo.

