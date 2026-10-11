---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [comparacion_modelos/motor_llama_cpp_b11429.json, resultados_comparacion_modelos.md]
---
# MTP (predicción multi-token / decodificación especulativa)

**Estado:** sin probar. No hay ninguna cifra medida.

## Contexto

llama.cpp b11429 expone las opciones de MTP. Podría acelerar la generación, pero añade otro modelo (el borrador) y
consume VRAM.

## Lo que hay

`motor_llama_cpp_b11429.json` registra:
- `"mtp_disponible_en_cli": true`;
- `"mtp_probado": false`.

`resultados_comparacion_modelos.md` explica que no se probó porque el modelo borrador no estaba instalado.

## Decisión

Evaluarlo solo después de estabilizar la pila Gemma Q4 + visión + TTS + Whisper ([[wsl-dominio-cuda]]). Hay que
comparar, con el mismo texto, primero sin voz y luego con el conjunto completo:
- primer token;
- tok/s;
- pico de VRAM;
- estabilidad;
- tasa de aceptación.

Fuente de este plan: `REPORTE_TRABAJO_CACAO.md` §16 (otra herramienta, **sin verificar**).

## No hacer

- No activar MTP en producción porque el ejecutable reconozca las banderas.
- No contar con su ahorro: no reduce el modelo base y suma el borrador. El margen en WSL ya es de unos 1,5 GiB.
