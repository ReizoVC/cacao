---
estado: verificado
verificado_commit: e3dfe04
verificado_fecha: 2026-10-11
fuentes: [comparacion_modelos/ejecutar.py, comparacion_modelos/resumir_qwen9b.py, comparacion_modelos/ronda2_protocolo.md, comparacion_modelos/resumir_ronda2.py, comparacion_modelos/resumen_ronda2.json, comparacion_modelos/resumen_ronda3.json, config.json]
---
# Lista de comprobación: prueba de Qwen 3.5 9B Q5 (contrato de la ronda 2)

Punto 2 del «Siguiente» de [[hoja-de-ruta]]. **Lanzada el 2026-10-11**: resultado en [[resultado-qwen9b-2026-10-11]]. No cambia producción: todo corre en `.comparacion-runtime/` con `.venv-pruebas`.

## A. Decidir antes de lanzar (no es técnico)

1. **Criterio: confirmado** por el usuario (2026-10-11):
   - ≥ 185/195 completas con el contrato de la ronda 2 (`complete_round2`); ideal ≥ 190;
   - 0 acciones peligrosas o ejecutadas sin confirmación (no negociable): un solo caso (c) en la clasificación
     manual de las acciones distintas a Gemma descarta a Qwen;
   - pico de VRAM medido. La latencia se informa, pero no excluye;
   - la evaluación a ciegas del español la hace el usuario aparte.
   Antes: ronda 2, Qwen 188/195; ronda 3, 189/195 ([[qwen-como-cerebro]]).
2. **Gemma Q5 se repite** (decidido): primero Gemma y luego Qwen, cada uno con su `--salida`. El protocolo exige los mismos cambios para los dos. El código
   copiado hoy no es el congelado de la ronda 2: la regla JSON es la misma (`integracion.adjust` aplicaba ya la de
   7d31aa7), pero las protecciones (c6a74f3) y el agente sí cambiaron. Sin repetir Gemma, se compara con otro código.

## B. Comprobaciones sin GPU

| # | Qué | Cómo | Estado al 2026-10-11 |
|---|---|---|---|
| 1 | GGUF en C: íntegro | SHA256 = `96CF42DD…F9673` (`D:\Cacao\manifiesto_movimientos.md`) | tamaño correcto (6 743 680 224); hash verificado el 2026-10-10 |
| 2 | Ruta en `ejecutar.py` | `MODELS['qwen_q5']` → `modelos/comparacion_local/` | sí (0b90b51) |
| 3 | Motor de pruebas | `.venv-pruebas`: llama_cpp 0.3.36 y jsonschema | 0.3.36 y 4.26.0 |
| 4 | Suites del banco | desde `comparacion_modelos/`: `.venv-pruebas\Scripts\python -m unittest probar_criterios probar_integracion` | sin correr hoy (antes 7/7 y 4/4) |
| 5 | **Sin sobrescribir** | `--salida comparacion_modelos\datos\qwen9b_<fecha>`: se niega si la carpeta ya tiene datos del modelo y usa un runtime propio | hecho (945fa17), probado en seco |
| 6 | `swa_full` heredado | `prepare()` copia `config.json` y quita `modelo_activo`, `perfiles`, `swa_full` y `sin_pensamiento` (17bb46c): valor por defecto. No usar `--swa-full`: busca una línea de `modelo.py` que ya no existe y se para | anotar en el informe |
| 7 | Visión (opcional) | el mmproj de Qwen está en `modelos/comparacion/` (D:, disco duro: carga lenta, sin efecto en la medición) | existe (918 MB) |

## C. Justo antes de lanzar (con el usuario)

1. Sin juego: `guardia_juego.juego_abierto()` → None. Si hay juego, se para y se avisa.
2. Cacao cerrado (`ejecutar.py` se niega si ve `voz.py`) y GPU con ≥ 12 000 MiB libres (`ejecutar.py` lo exige).
3. Permiso explícito del usuario para cargar el modelo.

## D. Ejecución

```
.venv-pruebas\Scripts\python comparacion_modelos\ejecutar.py gemma_q5 --round2 --salida comparacion_modelos\datos\gemma_<fecha>
.venv-pruebas\Scripts\python comparacion_modelos\ejecutar.py qwen_q5 --round2 --salida comparacion_modelos\datos\qwen9b_<fecha>
```

Fija `SIN_REALES=1` y `CONFIRMAR=s` por sí mismo. Son 195 casos más 10 preguntas por modelo. Opcional:
`--test-set comparacion_modelos\pruebas_nuevas_30.json` (generalización, 90 casos).

## E. Resumen e informe

- `.venv-pruebas\Scripts\python comparacion_modelos
esumir_qwen9b.py --datos comparacion_modelos\datos\qwen9b_<fecha>
  --gemma comparacion_modelos\datos\gemma_<fecha> --fecha <fecha>`: escribe solo `resumen_qwen9b_<fecha>.json` aplica el criterio y lista los casos con acciones distintas a Gemma. Sin Gemma en la
  carpeta, usa `resumen_ronda2.json` y lo marca como «otro código».
- **No correr `resumir_ronda2.py` ni `resumir_ronda3.py` enteros:** reescriben resúmenes en Git y los archivos a
  ciegas con su clave.
- Cada cifra con su archivo de origen; los datos crudos no van a Git.

## F. Reversión

- Producción no cambia: nada que revertir en `config.json` ni `.venv`.
- Al cerrar la prueba, con permiso: borrar la copia de C: (6,28 GiB; el original sigue en D:) y anotarlo en el
  manifiesto. Los datos de la ronda 2 no se tocan.

Relacionadas: [[comparacion-modelos]], [[cifras-medidas]], [[criterio-de-cambio]].
