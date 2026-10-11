---
estado: verificado
verificado_commit: 2797ba4
verificado_fecha: 2026-10-11
fuentes: [confirmacion_voz.py, ui_isla.py, probar_fase7.py]
---
# Música en la isla (protocolo v3): compilada y en main

El diseño está en `C:\asistente-ui\docs\diseno-musica.md`. Compilada el 2026-10-11 (isla 3bfef0f, Cacao 2797ba4) y
probada con un reproductor real: llegaron `reproduciendo` y `nada suena` al arnés ([[compilar-isla]]).

## Qué hace

- La isla lee `Windows.Media.Control` y **solo** mira `PlaybackStatus` de cada sesión. Al agente solo le llega
  `{"tipo": "musica", "reproduciendo": bool}`: al conectar y en cada cambio, con antirrebote de 1 s y como mucho un
  mensaje por segundo.
- **Nunca** cruzan el título, el artista, la carátula, la app ni la posición, ni se usa ningún `Try…Async` de
  control. Serían texto de un tercero, una vía de inyección. Es el **invariante 11** de la isla.
- **En Cacao es solo informativo:** `ServidorIsla.musica` (`True`, `False` o `None`; vuelve a `None` al
  desconectarse). Nunca relaja un freno: la confirmación por voz sigue con `confirmacion_voz.otro_audio_sonando`.
  Una prueba comprueba que `confirmacion_voz.py` no usa el dato.
- Con la isla cerrada no hay sondeo: solo despiertan los eventos de Windows. Si el API no está, no se manda nada.

## Dónde está

En `main` de los dos repositorios: isla 3bfef0f (antes en `claude/musica`) y Cacao 2797ba4 (fusión de
`claude/musica-v3`). Pruebas tras compilar: [[compilar-isla]].

## Falta

- Nada en Cacao usa todavía el booleano (es solo informativo; no se ve en la isla). Cualquier uso nuevo se diseña
  aparte y nunca relaja un freno.
- Funcionó sin declarar la capacidad `globalMediaControl` (exe Win32 sin empaquetar).
