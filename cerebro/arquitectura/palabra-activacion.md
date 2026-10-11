---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [palabra_activacion.py, seguimiento.py, entrenar_cacao.py, config.json, SRS.md]
---
# Palabra de activación «Cacao» y escucha de seguimiento

## Palabra «Cacao» (`palabra_activacion.py`)

- **Detección local, en la CPU:** características de openWakeWord (melspectrograma y embeddings) y encima un
  clasificador pequeño entrenado con voces sintéticas de Piper (`entrenar_cacao.py` → `modelos/cacao/`).
- **Funcionamiento:** cada 80 ms calcula una probabilidad; detecta si pasa el umbral en `paciencia` tramas seguidas.
  Una segunda etapa con Whisper filtra las activaciones falsas.
- **Privacidad:** búfer circular en memoria; no se guarda ni se transcribe nada hasta detectar la palabra. Mientras
  Cacao habla, se ignora.
- **Configuración:** `voz.palabra_activacion.activa` y `activa_al_iniciar`. Se enciende y se apaga con un clic físico
  en la isla o en la bandeja.
- **Al detectar:** la isla muestra «escuchando», graba con un búfer previo hasta un silencio y aplica los frenos de
  [[voz]].

## Escucha de seguimiento (`seguimiento.py`)

- Tras una respuesta hablada, escucha `voz.seguimiento.segundos` = 8 s sin necesitar la palabra.
- No se abre si otra app está sonando, y se cierra si empieza a sonar.
- Ignora los primeros 0,4 s (la cola de la voz de Cacao).
- Lo que se oye es un pedido normal, con los mismos frenos y las mismas confirmaciones.

## Cifras (SRS §4.3, sin volver a medir)

RNF-23/24 en `SRS.md`, con origen en `resultados_cacao_instalado.json` y `resultados_oye_cacao.json`:
- detección de 37/54 sola y 77/108 de corrido con la orden, con umbral 0,9;
- 0 activaciones falsas en 7,9 min de conversación.

Las activaciones falsas después de la segunda etapa **no se midieron** (RNF-25).

## Pruebas

`probar_palabra_activacion.py`, `probar_seguimiento.py` y `probar_confirmacion_voz.py`, sin micrófono
([[suites]]). Las pruebas con voz real están en [[pendientes-presenciales]].
