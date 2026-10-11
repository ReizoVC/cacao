---
estado: verificado
verificado_commit: dd51ba6
verificado_fecha: 2026-10-11
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

## Última compilación (2026-10-11, isla a690655)

- `npx tauri build --no-bundle`: código 0, en 144 s.
  - Memoria disponible mínima: 2,03 GiB, partiendo de 3,0 GiB.
  - El registrador de hábitos siguió vivo, con los mismos PID antes y después.
  - 8 avisos de funciones sin usar en `platform/`, todos del Coucou original.
- El exe se generó el 2026-10-11 a las 01:22:58. Mide 6 173 696 bytes.
  SHA-256 `e16e478c15cfcd5af448ee9b248ed5ada2cfb6fd3efafcdffd1459a067809274`.
- **Protocolo v2:** el exe embebe `island-Blq9F1OR.js`, que manda `hola` con `version: kt` y `kt=2`. El respaldo v1
  embebe `island-CYYKj4zF.js`. Los recursos van comprimidos, así que se comprueba por el hash del nombre del bundle.
- Pruebas después de compilar:
  - Rust sueltas: 23/23;
  - `probar_invariantes.py`: 10/10;
  - `probar_arnes.py`: 40/40;
  - `npm run probar-campo`: 18/18.
- **Prueba física con el arnés (2026-10-11, con el usuario delante):**
  - **A, clic:** las 8 opciones del menú actuaron, todas con `fisico=true`; los modos llegaron con
    `origen: bandeja`.
  - **B, teclado:** Abrir, Ajustes, Ver terminal, Permitir capturas, Salir y los dos modos dieron
    `fisico=false` y no hicieron nada (los modos, con aviso). «Pausar» no se probó.
  - **C, un clic inyectado** (script, 01:47:03): `bandeja: captura (fisico=false)` y nada más.
  - **D, Ajustes:** el interruptor encendió las capturas con un clic físico (01:36:10).
  - **E:** se encendió a las 01:48:37 y se apagó sola a las 01:58:37 («pasaron 10 minutos»).
  - **F:** se encendió (01:59:07), «Salir» dos veces y se relanzó la isla. Arrancó con
    `captura permitida=false` (07:26:22) aunque los ajustes guardados decían `true`. El usuario vio la casilla
    desmarcada en el menú, y su primer clic (07:37:36) la encendió. Cierre limpio con «Salir» dos veces
    (07:38:55 y 07:38:58).

## Respaldo de la isla v1

- `C:\asistente-ui\_prive\respaldos\asistente-ui-v1-82efb6b.exe` (`_prive/` lo ignora Git).
- Es el exe compilado el 2026-10-07 a las 01:34 (dos minutos antes del commit 82efb6b). Mide 6 171 136 bytes.
- SHA-256 `e02480e9747c4342b0fa7524ba52ad4742fafb31a670077da64c48c2aa339f34`.
- Habla el **protocolo v1** y su bandeja **no** exige clic físico.

## Volver a la isla v1

Copiar el respaldo sobre `target\release\asistente-ui.exe` no basta. **También hay que revertir en Cacao el
protocolo v2**:
- **8a78d51** (`ui_isla.PROTOCOLO = 2` y sus pruebas). Sin revertirlo, Cacao cierra la isla v1 con 4003.
- **b15a349** (el `mouse` no hace clic en la bandeja ni en los menús de la isla). El usuario pidió revertirlo junto
  con 8a78d51. No afecta a la compatibilidad: quitarlo solo reabre el hueco de la bandeja.

Con Cacao cerrado: `git revert 8a78d51 b15a349` en `C:\asistente`, y volver a pasar `probar_fase7.py A`,
`probar_grupo4.py`, `probar_segundo_plano.py` y `probar_campo_isla.py`. Anotar la vuelta atrás en [[log]] y
[[riesgos]].
