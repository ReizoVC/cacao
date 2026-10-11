---
estado: verificado
verificado_commit: d95855d
verificado_fecha: 2026-10-11
fuentes: [comparacion_modelos/ejecutar.py, comparacion_modelos/integracion.py, comparacion_modelos/criterios.py, comparacion_modelos/resumir_ronda3.py, comparacion_modelos/README.md, comparacion_modelos/verificar.py]
---
# Banco de comparación de modelos (`comparacion_modelos/`)

Banco aislado para comparar modelos y motores sin tocar producción.

## Cómo funciona `ejecutar.py`

- `prepare()` copia el código a `.comparacion-runtime/<modelo>[_<ronda>]/`:
  - escribe allí su propio `config.json` (el modelo de `MODELS`, `n_ctx` 16384, KV q8_0, sin mmap), sin los perfiles
    de producción (17bb46c);
  - deja `datos_locales.json` vacío;
  - quita el atajo de emergencia global.
- Variables de entorno: `SIN_REALES=1` y `CONFIRMAR=s`. Comprueba que no haya juego (`guardia_juego`).
- Opciones:
  - `--round2` o `--round3`: aplica el contrato de `integracion.py` (sin `mensaje_final`, regla JSON sin
    caracteres de control y protecciones);
  - `--server-url` y `--engine-tag`: llama-server ya iniciado (b11429);
  - `--swa-full`, `--test-set` (30 frases nuevas), `--vision-only`, `--smoke` y `--diagnostic`;
  - `--salida DIR` (945fa17): datos crudos y runtime aparte; se niega si la carpeta ya tiene datos del modelo.
- `--swa-full` está roto desde eb5a9c4: inyecta una línea de `modelo.py` que ya no existe y se para.
- Antes de cada caso vacía la caché KV (`llm.reset()` y `kv_cache_clear()`); producción no lo hace.
- Salida en `comparacion_modelos/datos/` (ignorado por Git): JSON por caso, muestras de GPU y conversación de 10
  preguntas.

## Resumir y publicar

- Los `resumir_*.py` leen los datos crudos y escriben `metricas_*.json` y `resumen_*.json`, que sí van a Git.
- Los informes `resultados_*.md` se publican con `git add -f`.
- Criterio oficial: `integracion.complete_round2` + `criterios.complete`. Auditoría: `resumir_ronda3.stats`.

## Evaluación a ciegas

- Las respuestas de conversación se mezclan con A/B sorteados por pregunta, con la clave en un archivo aparte.
- Archivos: `resultados_ciegas.md` (Gemma Q5 frente a Qwen Q5) y `resultados_ciegas_q4.md` (Q5 frente a Q4). El
  segundo y su clave entraron en cabf3ed y se sacaron del índice en 4daa737: siguen en el disco, fuera de Git.
- Las dos están **sin puntuar**.

## `verificar.py` (este directorio)

Comprueba hashes congelados y entregables sin cargar modelos. Si llega al final, **reescribe `integridad.json`** y
guarda el hash de `apps_categorias.json`. Por eso no se ejecutó tal cual. El 2026-10-10 se repitieron sus
comparaciones en una copia de solo lectura:
- `config.json`: coincidía hasta 68d0b4a (con CRLF). Desde eb5a9c4 (`swa_full`) ya no coincide, y es la primera
  aserción.
- `ronda3_congelado.json`:
  - `ejecutar.py` dejó de coincidir en 84fbe0b;
  - `protecciones_ejecucion.py`, en 5889dda;
  - `agente_minimo.py` no coincide con ninguna versión en Git (se congeló con cambios sin commit).
- Ronda 2, visión de la ronda 2, conversación nueva y motor `.venv` = `.venv-pruebas`: coinciden.

Conclusión: **falla de verdad desde 84fbe0b/5889dda**, porque congela la producción de la ronda 3. No indica
corrupción. Actualizar sus hashes es una decisión del usuario. Las comprobaciones de la sección de Gemma Q4 (por
ejemplo, el tamaño del GGUF en `modelos/comparacion`) no se repitieron.

## Avisos

- `ejecutar.py` está en Git desde cabf3ed (`--swa-full`, `--test-set` y las rutas). En 0b90b51 Qwen pasó a leerse de
  `modelos/comparacion_local`.
- Los runtimes y scripts de WSL viven en `.comparacion-runtime/`, que Git ignora: una clonación no los trae
  ([[mapa-archivos]]).

Resultados: [[cifras-medidas]].
