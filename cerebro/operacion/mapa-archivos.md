---
estado: verificado
verificado_commit: c297bcb
verificado_fecha: 2026-10-11
fuentes: [agente_minimo.py, voz.py, iniciar_cacao.py, .gitignore]
---
# Mapa de archivos por rol

Los nombres son relativos a la raíz del repositorio. Actualiza esta página al mover, crear o renombrar archivos.

## Núcleo

| Rol | Archivos |
|---|---|
| Arranque | `iniciar_cacao.py`, `crear_acceso_directo.ps1`, `avisos_windows.py` |
| Proceso principal (voz) | `voz.py`, `microfono.py`, `transcripcion.py`, `confirmacion_voz.py`, `seguimiento.py`, `palabra_activacion.py` |
| Agente | `agente_minimo.py`, `modelo.py`, `muestreo_gramatica.py`, `protecciones_ejecucion.py`, `obstaculos.py`, `emergencia.py`, `pedidos.py`, `camino_rapido.py`, `contrato_ronda2.py`, `cache_estados.py` |
| Herramientas | `herramientas.json` (catálogo y límites), `herramientas_grupo1.py`, `herramientas_grupo4.py`, `herramientas_powershell.py`, `vision.py`, `autocompletar_login.py` |
| Modos | `modo_directo.py`, `modo_juego.py`, `guardia_juego.py`, `deteccion.py` |
| Isla y entrada | `ui_isla.py`, `entrada_fisica.py`, `entrada.py`; repositorio aparte `C:\asistente-ui` (`AGENTS.md`, `docs/protocolo.md`, `windows/arnes/`) |
| Memoria y Fase 6 | `memoria.py`, `wiki.py`, `wiki_esquema.json`, `reflexion.py`, `lint.py`, `sugerencias.py`, `habitos.py`, `registro_habitos.py` |
| Configuración | `config.json`, `requirements.txt` |

## Pruebas y medición

| Rol | Archivos |
|---|---|
| Suites sin modelo | `probar_*.py` ([[suites]]); desde la Fase 1 también `probar_carga_modelo.py`, `probar_salida_utf8.py` y `probar_gramatica_json.py`; `probar_cierre_rapido.py` (69297e4), `probar_contrato_ronda2.py` (f21e746) , `probar_camino_rapido.py` (fdf84d1) y `probar_cache_estados.py` (b056954) |
| Evaluación con modelo | `evaluar_pruebas.py`, `benchmark_gramatica.py`, `pruebas.json` ([[evaluacion-65-frases]]) |
| Pruebas reales o presenciales | `prueba_real.py`, `prueba_presencial_isla.py` |
| Mediciones | `medir_*.py`, `validar_transcripcion.py`, `simular_habitos.py`; `comparacion_modelos/medir_memoria.py` (VRAM por opción, [[memoria-liberable]]) |
| Palabra «Cacao» | `entrenar_cacao.py`, `grabar_cacao.py`, `grabar_fondo_cacao.py`, `evaluar_*_cacao*.py` |
| Diagnósticos puntuales | `diagnostico_actividad.py`, `diagnostico_atajos*.py` |
| Comparación de modelos | `comparacion_modelos/`, con `verificar.py` (hashes congelados) y sus `probar_*.py` (unittest) ([[comparacion-modelos]]) |

## Documentos

| Rol | Archivos |
|---|---|
| Para Claude Code | `CLAUDE.md`, `cerebro/` |
| Requisitos y guía | `SRS.md`, `guia_instalacion_agente.md`, `diseno_fase6.md`, `diseno_fase7.md` |
| Informes | `resultados_comparacion_modelos.md`, `resultados_swa_y_recursos.md`, `clasificacion_fallos_qwen.md`, `INFORME_VALIDACION_SWA_GENERALIZACION.md` (cabf3ed, **sin verificar**) |
| Informes de otras herramientas (**sin verificar**) | `REPORTE_TRABAJO_CACAO.md`, `EvaluacionIA.md` |
| Evaluaciones a ciegas | `resultados_ciegas*.md`, `respuestas_*_ciegas.md`; claves en `clave_*.md` |

## Ignorados por Git (no los trae una clonación)

- `.venv/`, `.venv-pruebas/` y `modelos/` (los GGUF, Piper y el detector «Cacao»). `.venv-pruebas` tiene el mismo
  llama_cpp que `.venv` y además `jsonschema` (lo usa `comparacion_modelos/probar_integracion.py`).
- `.comparacion-runtime/`: motores, perfiles de TTS y scripts de WSL. `qwen3-tts-cpp/` y `qwen3-tts-kreutzm/`: bancos de Qwen3-TTS
  en Windows nativo (fuente, scripts, modelos GGUF y WAV de salida). Resúmenes en
  `comparacion_modelos/resumen_qwen3_tts_windows.json` y `resumen_qwen3_tts_llama_cpp.json`.
- `comparacion_modelos/datos/`: datos crudos.
- `resultados_*.json`, `resultados_*.md` y `*.log` (salvo los añadidos a mano con `-f`).

Datos personales: [[mapa-datos]].
