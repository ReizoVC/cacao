---
estado: verificado
verificado_commit: c297bcb
verificado_fecha: 2026-10-11
fuentes: [cache_estados.py, modelo.py, comparacion_modelos/comparar_corridas.py, comparacion_modelos/cache_estado.py, comparacion_modelos/probar_cache_estado.py, comparacion_modelos/medir_prompt.py, comparacion_modelos/probar_swa_cache.py, comparacion_modelos/ejecutar.py, agente_minimo.py, contrato_ronda2.py]
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

**Caché por estados para Qwen** (fase A en el banco y producción en `qwen9b`): [[cache-estados]].
