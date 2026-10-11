# Registro del cerebro

Una entrada por tarea, la más reciente al final: fecha, qué cambió y commit.

Entradas anteriores: [[log-2026-10-10]], [[log-2026-10-11-isla]] y [[log-2026-10-11-b]].

## 2026-10-11: 65 × 3 con producción restaurada (sin swa_full)

- `probar_swa_cache.py C --casos todos` (dbb0e42): 1.ª herramienta 195/195, completas 194/195 (base 193/195).
  Semilla 11 sin fallos en #26–42. Detalle en `evaluacion-65-frases`.

## 2026-10-11: brazo A sobre #1–42 (swa_full=false, sin vaciar): 42/42

- Los fallos de la primera corrida no se reproducen ni con la secuencia larga; ningún umbral de tokens coincide
  (tabla en `swa-full-false`). Causa abierta; sin arreglos ni entrada en `lecciones.md`.

## 2026-10-11: música en la isla implementada (protocolo v3), sin compilar

- Isla, rama `claude/musica`: 1daebe0 (Rust), 712a893 (protocolo v3 y arnés) y a90ddc9 (invariante 11).
- Cacao, rama `claude/musica-v3`: a9797ed (`ui_isla.PROTOCOLO = 3` y `musica` informativa).
- No van a `main` hasta compilar: v2 y v3 no se conectan (4003). Página `musica-isla` al día.
- Al revisar la línea mínima de Codex (e30e4fe, e441b90) se pidieron correcciones: con la línea apagada cambiaba
  el comportamiento. No se fusionó.

## 2026-10-11: Qwen 9B frente a Gemma, contrato de la ronda 2 (0bedb0f)

- Gemma y luego Qwen con `--salida` (`datos/gemma_2026-10-11`, `datos/qwen9b_2026-10-11`); resumen
  `comparacion_modelos/resumen_qwen9b_2026-10-11.json`. Gemma 195/195; Qwen 189/195, VRAM pico 7 781 frente a 13 076.
- Clasificación de 49 casos distintos: 37 (a), 11 (b), 1 (c) (#56 s22, cierre forzado no pedido). **No pasa.**
  Página nueva `resultado-qwen9b-2026-10-11`. `qwen-como-cerebro` sin cambiar: propuesta en el reporte.

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

