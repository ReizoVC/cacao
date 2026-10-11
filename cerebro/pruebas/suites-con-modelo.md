---
estado: verificado
verificado_commit: d4b36dd
verificado_fecha: 2026-10-10
fuentes: [probar_voz.py, probar_memoria.py, probar_emergencia.py, probar_reflexion.py, probar_vision.py, probar_seguridad_vision.py, prueba_real.py, validar_transcripcion.py, guardia_juego.py]
---
# Pruebas que cargan modelo o tocan el PC real

**Antes de cualquiera:**
- la GPU tiene que estar libre (sin juego abierto: `guardia_juego`);
- Cacao no debe estar en marcha, porque compite por la VRAM;
- desde el teléfono, ninguna.

| Script | Qué hace | Real o simulado | Baseline |
|---|---|---|---|
| `evaluar_pruebas.py` | 65 frases × semillas | Simulado con `SIN_REALES=1` y `CONFIRMAR=s` | [[evaluacion-65-frases]] |
| `probar_voz.py` | `voz.py` con WAV y un altavoz falso; Gemma y Whisper en la GPU | Simulado | 11/11 (f7b3509) |
| `probar_memoria.py` | recordar y consultar_memoria en `memoria_prueba.db` | Simulado | sin total en un commit |
| `probar_emergencia.py` | Atajo de emergencia con el agente completo | Simulado (no pulsa teclas) | sin total en un commit |
| `probar_reflexion.py` | Reflexión y lint con el modelo real sobre 7 días simulados | Simulado | 24/24 y 7/7 en el SRS (`resultados_reflexion.json`) |
| `probar_modo_juego.py --medir` | Descarga y recarga reales de Gemma y Whisper | Juego simulado | ver el SRS, RNF-08 |
| `probar_vision.py` | `ver_pantalla`: **captura la pantalla real** | Real, solo lectura | — |
| `probar_seguridad_vision.py` | El agente con `ver_pantalla` real | Real, solo lectura | — |
| `prueba_real.py N` | Pruebas **reales** del agente | Real | Solo con el usuario delante |
| `validar_transcripcion.py` | Transcripción con grabaciones de `voz_pruebas/` | Datos personales | No usar sin permiso |
| `probar_audio_nativo.py`, `probar_whisper.py` | Comparar transcriptores con WAV | Según los WAV | — |

## Reglas

- Las capturas reales pueden mostrar datos personales: no las guardes ni las cites.
- Si la guardia de la GPU corta la prueba, avisa; no pongas `ESPERAR_JUEGO=1` para esquivarla sin permiso.
- No hay baseline registrada para las filas «sin total en un commit»: no inventes una.

Ver [[suites]] y [[comparacion-modelos]].
