---
estado: sin verificar
verificado_commit: 6a01ca1
verificado_fecha: 2026-10-11
fuentes: [confirmacion_voz.py, ui_isla.py]
---
# Música en la isla (protocolo v3): diseño, sin implementar

El diseño completo está en `C:\asistente-ui\docs\diseno-musica.md` (isla cf09696). Está **sin verificar** porque el
API no se ha probado en este PC.

## La decisión propuesta

- La isla lee `Windows.Media.Control` y **solo** mira `PlaybackStatus`. A la isla y al agente solo les llega el
  booleano `reproduciendo`.
- **Nunca** cruzan el título, el artista, la carátula, la app (`SourceAppUserModelId`) ni la posición. Tampoco se usa
  ningún `Try…Async` de control. Son texto de un tercero y serían una vía de inyección.
- **Protocolo v3:** mensaje isla → agente `{"tipo": "musica", "reproduciendo": bool}`, al conectar y en cada cambio
  (antirrebote de 1 s, un mensaje por segundo como mucho). Un valor que no sea booleano se ignora.
- **En Cacao es solo informativo:** nunca relaja un freno. La confirmación por voz sigue usando
  `confirmacion_voz.otro_audio_sonando`, que mira los medidores de pico de cada sesión de audio, sin capturar audio.

## Comprobado en la documentación (2026-10-11)

- Windows 10 1809 o posterior.
- Capacidad `globalMediaControl`, que es de **uso general**, no restringida.
- Microsoft dice que las capacidades se aplican «sobre todo» a apps empaquetadas o en AppContainer. La isla es un
  Win32 sin empaquetar, así que **se infiere** que no hace falta declarar nada. Se confirma en el prototipo.
- No hay credenciales ni captura de audio: el API lee lo que publica cada reproductor.

## Dónde va

En el **lote de Rust** (`C:\asistente-ui\docs\lote-rust.md`, protegido): los cambios de Rust se juntan y se compilan
una sola vez. Codex pide los suyos por filas y no edita los archivos protegidos ([[isla-codex]]). Archivos que toca:
- en la isla: `Cargo.toml` (features `Media_Control` y `Foundation`), un `musica.rs` nuevo, `platform/windows.rs`,
  `lib.rs`, `agente.ts`, `main.ts`, `docs/protocolo.md` y el arnés;
- en Cacao: `ui_isla.py` y `probar_fase7.py`.

Habrá un invariante 10 nuevo (solo `PlaybackStatus` y un booleano) y una prueba física con un reproductor real
([[compilar-isla]]).
