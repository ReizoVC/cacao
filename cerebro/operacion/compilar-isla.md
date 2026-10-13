---
estado: verificado
verificado_commit: f83dd1a
verificado_fecha: 2026-10-13
fuentes: [ui_isla.py, herramientas_grupo4.py, config.json]
---
# Compilar la isla, respaldo y vuelta atrás

La isla vive en `C:\asistente-ui` (otro repositorio). Cacao lanza `windows\target\release\asistente-ui.exe`
(`config.ui.exe`). Contrato y protecciones: [[isla-websocket]]; traspaso a Codex: [[isla-codex]].

## Compilar (con permiso del usuario)

1. Cacao e isla cerrados: ni `voz.py`, `agente_minimo.py` o `iniciar_cacao.py`, ni `asistente-ui.exe`, y el puerto
   8765 libre. El registrador de hábitos (`registro_habitos.py`) puede seguir: no usa la isla ni el exe.
2. Pruebas de Rust sueltas (`foco`, `bandeja`, `captura` y la forma de `island`), con rustc y VS 2022:
   `python windows\arnes\probar_invariantes.py` las corre.
3. Build desde una consola con VS 2022 (`vcvars64.bat`; VS 18 Insiders falla con `msvcrt.lib`):
   ```
   cd C:\asistente-ui\windows
   set CARGO_NET_OFFLINE=true
   set CARGO_BUILD_JOBS=2
   npx tauri build --no-bundle
   ```
   El perfil release usa `lto = true` y `codegen-units = 1`: el enlace gasta memoria. Con las dependencias ya
   compiladas, solo se recompila la isla.

## Última compilación (2026-10-13, isla 9a648a3, solo interfaz)

- Arreglo: «Contraer a línea» (⌃) gana al mouse dentro (9a648a3). Build en 121 s; exe `df52e543…`,
  `island-B4mC0mQY.js`; respaldo del anterior en `_prive/respaldos/asistente-ui-b30e901.exe`. Arnés 45/45, campo
  18/18.
- **Prueba física completa** (`mock_agente.py --escenario recorrido --paso 3`, usuario delante): ⌃ lleva a la
  línea; bordes de color vistos; reconexión conserva la línea; respuesta hablada con barras en la línea; la
  tarjeta de confirmación se vio sin tapar y la decisión llegó por el botón (`si: true`, clic físico).
  Antes (b30e901): bandeja («Pausar» con teclado no actúa) y armario tras reiniciar, bien.

## Compilación anterior (2026-10-13, isla b30e901, solo interfaz)

- Línea fina con 5 barras (voz solo en la línea), bordes de color por modo (ámbar sin confirmación, verde
  escucha; línea y engranaje de la pequeña), «Sin confirmación» 4 s al encender, curvas de notch, seguimiento y
  `State.cacaoHabla` (912abce). Sin cambios de Rust ni de protocolo.
- Build en 140 s, mismos 8 avisos. Exe 6 201 344 bytes, SHA-256 `e814cc16…`, `island-CwkiApfP.js`. Respaldo del
  anterior: `_prive/respaldos/asistente-ui-v3-3bfef0f.exe` (`bcdc268e…`).
- Arnés 45/45, campo 18/18 tras compilar. **Prueba física:** colores del engranaje vistos con claridad; bandeja
  («Pausar» con teclado no actúa, con clic sí) y armario tras reiniciar, bien según el usuario.
  **Fallo:** «Contraer a línea» (⌃) en la pequeña no hace nada con el mouse dentro (`compactaManual` de
  bf1e9f1); pedido a Codex. Sin probar en físico: tarjeta de confirmación y barras con voz (las órdenes se
  escribieron en el campo de la isla; la próxima vez, `--escenario recorrido`).

## Compilación anterior (2026-10-11, isla 3bfef0f, protocolo v3)

- Contenido: música (invariante 11), rediseño de tres niveles de Codex, línea mínima, guardarropa, invariante 10 y
  panel de 800 px. Cacao, a la vez: fusión de `claude/musica-v3` (2797ba4).
- Antes: invariantes 12/12. `npx tauri build --no-bundle`: código 0 en 150 s, mismos 8 avisos de `platform/`.
- Exe 6 200 320 bytes, SHA-256 `bcdc268e2da140bb7c902c624ad850019ca95d45323c3729f191555f61abed49`; embebe
  `island-DfaOcGKd.js` con protocolo 3.
- Después: arnés 45/45, campo 18/18; Cacao `probar_fase7.py A` 37/37, segundo plano 23/23, campo de la isla
  29/29, grupo 4 OK.
- **Prueba física con el arnés (usuario delante):** conexión v3; tamaños de los tres niveles vistos bien; la
  música llegó al agente (`reproduciendo` / `nada suena`) con un reproductor real. Sin probar: tarjeta de
  confirmación desde el arnés, armario tras reiniciar y «Pausar» con teclado. Hallazgos para Codex: la
  desplegada pierde la curvatura de notch, la línea se pide más fina (con barras que se mueven al hablar) y el
  icono de seguimiento no se entiende.

Compilaciones anteriores (v2 y su prueba física) y vuelta a la isla v1: [[compilar-isla-historial]].

## Respaldo de la isla v2

- `C:\asistente-ui\_prive\respaldos\asistente-ui-v2-a690655.exe`, SHA-256 `e16e478c…` (el exe de a690655).
- Volver a v2: copiarlo sobre `target\release\asistente-ui.exe` **y** revertir en Cacao la fusión 2797ba4
  (`git revert -m 1 2797ba4`); si no, Cacao v3 e isla v2 se rechazan con 4003.
