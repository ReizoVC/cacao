---
estado: verificado
verificado_commit: dd51ba6
verificado_fecha: 2026-10-11
fuentes: [comparacion_modelos/ejecutar.py, comparacion_modelos/ronda2_protocolo.md, comparacion_modelos/resumir_ronda2.py, comparacion_modelos/resumen_ronda2.json, comparacion_modelos/resumen_ronda3.json, config.json]
---
# Lista de comprobación: prueba de Qwen 3.5 9B Q5 (contrato de la ronda 2)

Punto 2 del «Siguiente» de [[hoja-de-ruta]]. **Preparada, sin lanzar**: espera la orden del coordinador y el permiso
del usuario (usa la GPU). No cambia producción: todo corre en `.comparacion-runtime/` con `.venv-pruebas`.

## A. Decidir antes de lanzar (no es técnico)

1. **Criterio fijado de antemano.** [[qwen-como-cerebro]] dice que no se reabre Qwen sin un criterio nuevo. Hay
   dos escritos:
   - ronda 2 (`ronda2_protocolo.md`): ≥ 186/195 completas, 0 vacías (195 tareas y 10 preguntas) y no empeorar en
     la evaluación a ciegas;
   - ronda 3 (`ronda3_protocolo.md`): ≥ 192/195, 0 vacías, 0 confirmaciones falsas y 0 acciones distintas.
   Referencias: ronda 2, Qwen 188/195 (`resumen_ronda2.json`); ronda 3, 189/195 y `qwen_pass: false`
   (`resumen_ronda3.json`).
2. **¿Gemma Q5 como referencia en la misma tanda?** El protocolo exige los mismos cambios para los dos. El código
   copiado hoy no es el congelado de la ronda 2 (Fase 1: regla JSON, protecciones, carga perezosa). Sin repetir
   Gemma, la comparación es con números de otro código.

## B. Comprobaciones sin GPU

| # | Qué | Cómo | Estado al 2026-10-11 |
|---|---|---|---|
| 1 | GGUF en C: íntegro | SHA256 = `96CF42DD…F9673` (`D:\Cacao\manifiesto_movimientos.md`) | tamaño correcto (6 743 680 224); hash verificado el 2026-10-10 |
| 2 | Ruta en `ejecutar.py` | `MODELS['qwen_q5']` → `modelos/comparacion_local/` | sí (0b90b51) |
| 3 | Motor de pruebas | `.venv-pruebas`: llama_cpp 0.3.36 y jsonschema | 0.3.36 y 4.26.0 |
| 4 | Suites del banco | desde `comparacion_modelos/`: `.venv-pruebas\Scripts\python -m unittest probar_criterios probar_integracion` | sin correr hoy (antes 7/7 y 4/4) |
| 5 | **Respaldo de la evidencia** | copiar `comparacion_modelos/datos/ronda2/` a otra carpeta: `ejecutar.py` escribe `qwen_q5.json` y `gemma_q5.json` **encima** de los de la ronda 2 | pendiente |
| 6 | `swa_full` heredado | `prepare()` copia `config.json`; desde 397d0a2 no trae `swa_full` (valor por defecto). Con `--swa-full` se fija y el archivo lleva `_swa_false` | anotar en el informe |
| 7 | Visión (opcional) | el mmproj de Qwen está en `modelos/comparacion/` (D:, disco duro: carga lenta, sin efecto en la medición) | existe (918 MB) |

## C. Justo antes de lanzar (con el usuario)

1. Sin juego: `guardia_juego.juego_abierto()` → None. Si hay juego, se para y se avisa.
2. Cacao cerrado (`ejecutar.py` se niega si ve `voz.py`) y GPU con ≥ 12 000 MiB libres (`ejecutar.py` lo exige).
3. Permiso explícito del usuario para cargar el modelo.

## D. Ejecución

```
.venv-pruebas\Scripts\python comparacion_modelos\ejecutar.py qwen_q5 --round2
.venv-pruebas\Scripts\python comparacion_modelos\ejecutar.py gemma_q5 --round2      (si A.2 = sí)
```

Fija `SIN_REALES=1` y `CONFIRMAR=s` por sí mismo. Son 195 casos más 10 preguntas por modelo. Opcional:
`--test-set comparacion_modelos\pruebas_nuevas_30.json` (generalización, 90 casos).

## E. Resumen e informe

- Métricas con `integracion.complete_round2` (criterio oficial), importando `resumir_ronda2.stats` desde un
  script aparte. **No correr `resumir_ronda2.py` entero:** reescribe archivos en Git (`resumen_ronda2.json`,
  `metricas_ronda2.json`, `auditoria_qwen_ronda2.json`, `vision_ronda2.json`, `ronda2_pilotos.json`), anexa al
  informe y regenera `respuestas_integracion_ciegas.md` con su clave (evaluación a ciegas).
- Cada cifra con su archivo de origen; los datos crudos no van a Git.

## F. Reversión

- Producción no cambia: nada que revertir en `config.json` ni `.venv`.
- Al cerrar la prueba, con permiso: borrar la copia de C: (6,28 GiB; el original sigue en D:) y anotarlo en el
  manifiesto. Restaurar `datos/ronda2/` desde el respaldo del paso B.5 si se quiere conservar la ronda 2 original
  en su sitio.

Relacionadas: [[comparacion-modelos]], [[cifras-medidas]], [[criterio-de-cambio]].
