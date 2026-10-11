---
estado: sin verificar
verificado_commit: a9797ed
verificado_fecha: 2026-10-11
fuentes: [confirmacion_voz.py, ui_isla.py, probar_fase7.py]
---
# Música en la isla (protocolo v3): implementada en ramas, sin compilar

El diseño está en `C:\asistente-ui\docs\diseno-musica.md`. Está **sin verificar** porque la isla no se ha compilado
y el API no se ha probado en este PC.

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

## Dónde está (2026-10-11)

| Repositorio | Rama | Commits | Pruebas |
|---|---|---|---|
| Isla | `claude/musica` (worktree `C:\asistente-ui-claude`) | 1daebe0, 712a893, a90ddc9 | invariantes 12/12 con Rust, arnés 45/45, campo 18/18, build; 9 mutaciones del invariante 11 detectadas |
| Cacao | `claude/musica-v3` (worktree `C:\asistente-claude`) | a9797ed | `probar_fase7.py` A 37/37; 3 mutaciones detectadas; segundo plano 23/23 y campo 29/29 |

**No se fusionan en `main` por separado.** Una isla v2 con un Cacao v3, o al revés, se rechazan con 4003. Se fusionan
las dos ramas a la vez, al compilar la isla ([[compilar-isla]]).

## Falta

- Compilar la isla (con permiso y con Cacao cerrado). El `cargo check` de la rama pasó el 2026-10-11 sin errores
  (isla 3bfef0f, con el rediseño y el panel de 800 px ya integrados); su `target` se borró.
- Prueba física con el arnés y un reproductor real: diseño §6.
- Comprobar que el API funciona sin declarar la capacidad `globalMediaControl` (la isla es un Win32 sin empaquetar).
