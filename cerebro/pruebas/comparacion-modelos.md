---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [comparacion_modelos/ejecutar.py, comparacion_modelos/integracion.py, comparacion_modelos/criterios.py, comparacion_modelos/resumir_ronda3.py, comparacion_modelos/README.md, comparacion_modelos/verificar.py]
---
# Banco de comparación de modelos (`comparacion_modelos/`)

Banco aislado para comparar modelos y motores sin tocar producción.

## Cómo funciona `ejecutar.py`

- `prepare()` copia el código a `.comparacion-runtime/<modelo>[_<ronda>]/`:
  - escribe allí su propio `config.json` (el modelo de `MODELS`, `n_ctx` 16384, KV q8_0, sin mmap);
  - deja `datos_locales.json` vacío;
  - quita el atajo de emergencia global.
- Variables de entorno: `SIN_REALES=1` y `CONFIRMAR=s`. Comprueba que no haya juego (`guardia_juego`).
- Opciones:
  - `--round2` o `--round3`: aplica el contrato de `integracion.py` (sin `mensaje_final`, regla JSON sin
    caracteres de control y protecciones);
  - `--server-url` y `--engine-tag`: llama-server ya iniciado (b11429);
  - `--swa-full`, `--test-set` (30 frases nuevas), `--vision-only`, `--smoke` y `--diagnostic`.
- Salida en `comparacion_modelos/datos/` (ignorado por Git): JSON por caso, muestras de GPU y conversación de 10
  preguntas.

## Resumir y publicar

- Los `resumir_*.py` leen los datos crudos y escriben `metricas_*.json` y `resumen_*.json`, que sí van a Git.
- Los informes `resultados_*.md` se publican con `git add -f`.
- Criterio oficial: `integracion.complete_round2` + `criterios.complete`. Auditoría: `resumir_ronda3.stats`.

## Evaluación a ciegas

- Las respuestas de conversación se mezclan con A/B sorteados por pregunta, con la clave en un archivo aparte.
- Archivos: `resultados_ciegas.md` (Gemma Q5 frente a Qwen Q5) y `resultados_ciegas_q4.md` (Q5 frente a Q4, sin
  commit).
- Las dos están **sin puntuar**.

## Avisos

- `verificar.py` compara hashes congelados, entre ellos el de `config.json`. Según `REPORTE_TRABAJO_CACAO.md`
  puede fallar porque los archivos cambiaron después (**sin verificar**: no se ejecutó).
- `ejecutar.py` tiene cambios **sin commit** (`--swa-full`, `--test-set` y la ruta de Gemma Q4 en otro disco)
  ([[backlog]]).
- Los runtimes y scripts de WSL viven en `.comparacion-runtime/`, que Git ignora: una clonación no los trae
  ([[mapa-archivos]]).

Resultados: [[cifras-medidas]].
