---
estado: verificado
verificado_commit: 62cd4fc
verificado_fecha: 2026-10-11
fuentes: [comparacion_modelos/cache_estado.py, comparacion_modelos/probar_cache_estado.py, comparacion_modelos/medir_prompt.py, comparacion_modelos/probar_swa_cache.py, comparacion_modelos/ejecutar.py, agente_minimo.py, contrato_ronda2.py]
---
# Prompt de sistema y caché de prefijo (2026-10-11)

Medidas sin GPU y de las corridas ya hechas. Las usan [[filtrado-herramientas]] y [[camino-rapido]].

**Tokens del prompt de sistema** (`medir_prompt.py`, tokenizador con `vocab_only`, memoria y wiki vacías;
`datos/prompt_tokens_2026-10-11_1821.json`):

| | Gemma | Qwen (con contrato) |
|---|---:|---:|
| Total | 3 802 | 4 141 |
| Reglas (+ ejemplo de `mensaje_final` en Gemma / RULES en Qwen) | 670 + 81 | 527 + 491 |
| Las 21 herramientas | 3 023 (80 %) | 3 094 (75 %) |
| Más pesadas: mouse, teclado, ver_pantalla, abrir_app | 287, 241, 226, 223 | 306, 240, 230, 221 |

**Caché de prefijo, medida en las 65 × 3** (`datos/swa_cache/*.json`, campo `llamadas`):
- **Gemma** reutiliza unos 3 965 tokens en el 100 % de las llamadas (449/449, `gemma65x3cierre_C`).
- **Qwen no reutiliza nada** (0/593, `qwen65x3contrato_A`): `kv_cache_seq_rm` falla con su memoria híbrida
  (recurrente), así que recalcula el prompt entero, 4 300–4 450 tokens, en cada llamada.

**Coste de recalcular**, medido en el banco, que vacía la caché por caso (`datos/{qwen9b,gemma}_2026-10-11`):
- **Qwen:** 1,54 s por llamada (≈ 0,35 ms/token), el 59 % del tiempo del modelo.
- **Gemma:** unos 2,1 s con el prompt entero (p90) y 0,73 s reutilizando (p10). Perder el prefijo le cuesta
  ≈ 1,3 s por llamada.

## Fase A: caché por estados para Qwen (banco, 2026-10-11; producción no lo usa)

`comparacion_modelos/cache_estado.py` guarda el estado de llama.cpp tras el prompt de sistema, alineado a `n_batch`:
4 096 de los 4 194–4 265 tokens comunes. Lo restaura antes de cada llamada; tras restaurar, `kv_cache_seq_rm` sí
funciona (94/94 y 499/499).

- **Corrección** (`probar_cache_estado.py`, `datos/cache_estado/comparacion_qwen9b.json`): 42 casos de la secuencia
  larga, semilla 11, greedy y con la hora del pedido fija. **Salidas idénticas** con y sin caché.
  - Sin alinear a `n_batch` o sin fijar la hora salían diferencias: en el primer caso, por cómo se trocea el prompt
    en bloques; en el segundo, porque cada pedido lleva la hora.
- **Tiempos** (mismos 42 casos): llamada 2,86 → 1,25 s; tarea 6,34 → 2,77 s.
- **Memoria:** el estado ocupa 118 MB de RAM y no añade VRAM (7 654 / 7 575 MiB cargado). Crearlo cuesta 1,8 s, una
  vez; restaurarlo, 26 ms de media (44 ms como máximo).
- **65 × 3 del banco** (`ejecutar.py qwen_q5 --round2 --cache-estado`, `datos/qwen9b_cache_2026-10-11`):
  - 62 / 65 / 62 = **189/195**, igual que sin caché;
  - primera acción 2,44 → 0,94 s (mediana); tarea 6,83 → 3,05 s; lectura del prompt 1,54 → 0,03 s por llamada;
  - 193 de 195 casos, idénticos a la corrida sin caché. Los 2 distintos (#56 s22 y s33) pasaban por
    `ver_pantalla`: la caché restauraba encima de la imagen ya evaluada.
  - Repetida con la caché corregida (`datos/qwen9b_cache2_2026-10-11`): 189/195. Las dos corridas con caché son
    idénticas entre sí. Los mismos 2 casos difieren de la corrida sin caché, pero **no por la caché**: esa corrida
    (10:23) es anterior a los frenos de `forzar` (0a3ea28, 10:49) y de `listar_controles` (e9a580d, 10:51).
    - #56 s33: `listar_controles` con id 1 daba error y ahora da la ventana del primer plano;
    - #56 s22: `forzar: true` ya no se ejecuta.
    - La corrección de d7e0ba2 (no restaurar si el estado ya tiene el prompt entero) no llegó a actuar: el banco no
      usa visión (`mmproj` vacío), pero protege la ruta de visión de producción.
  - Para una comparación estricta, con el mismo código, falta una 65 × 3 sin caché con el código de hoy.
- Gemma no se probó: ya reutiliza el prefijo.

