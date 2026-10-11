---
estado: verificado
verificado_commit: d95855d
verificado_fecha: 2026-10-11
fuentes: [comparacion_modelos/resumen_gemma_q5_llama_b11429.json, comparacion_modelos/motor_llama_cpp_b11429.json, modelo.py, muestreo_gramatica.py, vision.py, transcripcion.py, requirements.txt]
---
# Motor: llama-cpp-python 0.3.36 frente a llama.cpp b11429 (servidor)

**Estado:**
- **Producción:** sigue con llama-cpp-python 0.3.36, fijado en `requirements.txt`.
- **Pruebas:** llama.cpp b11429 se usa en `.comparacion-runtime/` y en WSL.
- **Migración:** pendiente.

## Resultado medido (Gemma Q5, 65 frases × 3)

| | 0.3.36 | b11429 | Origen |
|---|---:|---:|---|
| Completas | 195 | 195 | `resumen_gemma_q5_llama_b11429.json` |
| Acciones distintas | 2 | 4 | ídem |
| Mediana de la primera acción | 3,50 s | 3,91 s | ídem |
| tok/s | 35,0 | 41,1 | ídem |
| Pico de VRAM | 12 756 | 9 542 MiB | ídem |

## Por qué la migración no es trivial

Producción depende de partes internas de 0.3.36:
- **`muestreo_gramatica.LlamaRapida`** sobrescribe `Llama._init_sampler`. Es el arreglo de velocidad de la gramática
  «topk».
- **`vision.ManejadorVision`** sustituye `_mtmd_cpp` para fijar los tokens por imagen.
- **`transcripcion.py`** clona el contexto (audio nativo) usando atributos internos.
- **`modelo.py`**:
  - captura los registros de llama.cpp en `errores_llama.log`;
  - cambia `llama_grammar.PRIMITIVE_RULES["char"]` (7d31aa7). Con llama-server, la regla JSON hay que
    comprobarla en el lado del servidor.

Con llama-server todo eso pasa a ser HTTP: gramática y esquema por petición, visión con `--mmproj` (b11429 limitó
los tokens de imagen a 512 por `n_ubatch`) y control de interrupciones.

## Decisión

Migrar solo con un plan reversible, después de la pila WSL ([[wsl-dominio-cuda]]) y volviendo a pasar las 65
frases.

## No hacer

- No actualizar llama-cpp-python «de paso»: rompe `LlamaRapida` (SRS R-06).
- Si hay que volver atrás con el muestreo, `modo_gramatica: null` en `config.json`.
