---
estado: verificado
verificado_commit: d95855d
verificado_fecha: 2026-10-11
fuentes: [entrada.py, diagnostico_atajos3.py, modelo.py, muestreo_gramatica.py, comparacion_modelos/integracion.py, guia_instalacion_agente.md, resultados_comparacion_modelos.md, protecciones_ejecucion.py, guardia_juego.py, agente_minimo.py]
---
# Lecciones aprendidas (fallos reales y su causa)

| Fallo | Causa | Arreglo o regla |
|---|---|---|
| Nunca había «inactivo» aunque nadie usara el PC | `GetLastInputInfo` se reiniciaba sin ninguna entrada (2026-10-06) | Raw Input con dispositivo (`entrada.py`) |
| Ctrl+S no abría «Guardar como» en el Bloc de notas | En español, Guardar es **Ctrl+G** y Guardar como, Ctrl+Mayús+S | Obstáculos aprendidos; `diagnostico_atajos3.py` |
| «CUDA error» sin detalle | llama-cpp-python 0.3.36 ocultaba los registros de llama.cpp | `modelo.py` los muestra y los guarda en `errores_llama.log` |
| RAM agotada con el modelo cargado | `use_mmap: true` mantenía el GGUF en RAM (~8,6 GB) | `use_mmap: false` ([[use-mmap-false]]) |
| Generación a ~8 tok/s con gramática | llama-cpp-python aplica la gramática antes de top_k, sobre ~262 000 tokens | `LlamaRapida` «topk» (SRS RNF-01: 38,0 tok/s) |
| `JSONDecodeError` con un salto de línea en el pensamiento | La regla `char` de la gramática permite U+0000–U+001F | Regla estricta en `modelo.py` (7d31aa7) y en `integracion.py`; `probar_gramatica_json.py` |
| `UnicodeEncodeError` al imprimir | Consola cp1252 | UTF-8 en el lanzador y en `voz.py` y el modo texto (`salida_utf8`, 8e72787); en pruebas, reconfigurar stdout |
| Pedidos de varias acciones a medias | `mensaje_final` cerraba la tarea tras la primera acción, sin validar | Contrato sin cierre rápido en las pruebas; en producción, `mensaje_final` validado y apagado en Qwen ([[cierre-rapido-mensaje-final]]) |
| El endpoint de Gemma en Windows dejó de responder | CUDA en Windows y en WSL a la vez | Un solo dominio CUDA ([[wsl-dominio-cuda]]) |
| Whisper escribe «Gracias por ver el video» en silencio | Alucinación típica | Frenos en `voz.filtrar` |
| Las pruebas cargaron unos 12 GB de VRAM mientras alguien jugaba | No se comprobaba si había un juego abierto | `guardia_juego` en `crear_llm` y en Whisper; avisar y no esquivar |
| Respuestas correctas rechazadas por la protección | Expresiones regulares demasiado amplias («escrita», «sonido… está», «no he podido») | Análisis de la cláusula en lugar de ampliar listas (c6a74f3, [[protecciones]]) |
| Una prueba «sin modelo» cargó Gemma | Importar `agente_minimo` creaba el modelo (también `probar_fase7.py` A y `probar_modo_juego.py` vía `voz`) | Carga perezosa con `cargar_modelo()` (14c17cb, `probar_carga_modelo.py`) |
| `cerebro/modelos/` no entraba en Git | La regla raíz `modelos/` ignora cualquier carpeta con ese nombre | `!modelos/` en `cerebro/.gitignore` |
| La isla no compilaba (`LNK1104 msvcrt.lib`) | VS 18 Insiders | Compilar desde VS 2022 (`vcvars64.bat`) (guía) |
| El modo voz descartaba todo | Micrófono silenciado o tomado en exclusiva por otra app | Revisar el mute (guía) |

## Reglas que salen de esto

- Mide antes de afirmar. Una cifra sin su archivo de origen no se pone.
- Que algo quepa en memoria no prueba que sea estable: hay que medir los picos simultáneos.
- Cambiar el prompt o el esquema cambia el modelo en la práctica: hay que volver a pasar las 65 frases.
