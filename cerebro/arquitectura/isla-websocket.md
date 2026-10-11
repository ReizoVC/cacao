---
estado: verificado
verificado_commit: 8a78d51
verificado_fecha: 2026-10-11
fuentes: [ui_isla.py, herramientas_grupo4.py, pedidos.py, agente_minimo.py, voz.py, entrada_fisica.py, config.json, diseno_fase7.md, prueba_presencial_isla.py, medir_isla_juego.py]
---
# Isla y WebSocket

La isla es una interfaz flotante (Tauri 2 y WebView2) en un repositorio aparte, `C:\asistente-ui` (`windows/`).
Cacao lanza el exe de `config.ui.exe`. Diseño: `diseno_fase7.md`. Adapta Coucou: la licencia de los assets está en
[[riesgos]].

El `CLAUDE.md` y el `docs/AGENTS.md` de ese repositorio son del Coucou original (macOS) y **no** describen la isla. Lo
que vale es el `AGENTS.md` de la raíz (desde ca7fb21).

## Contrato: `C:\asistente-ui\docs\protocolo.md` (versión 2)

Escrito desde el código el 2026-10-11 (b7b81a7) y subido a la versión 2 (isla 41656f0, Cacao 8a78d51). Resumen:
- **Conexión:** `ui_isla.ServidorIsla` (el agente es el servidor).
  - Solo `127.0.0.1:8765`.
  - Token por sesión (`token_urlsafe(32)`) en `%LOCALAPPDATA%\Asistente\ui.json`, que se borra al salir.
  - Origin solo `tauri.localhost` o `localhost:1420`; si no, 403.
  - Primer mensaje `hola` en ≤ 5 s; si no llega, no es un objeto o el token no coincide, cierre 4001.
  - Después del token, `version` tiene que ser `ui_isla.PROTOCOLO` (2); si no, cierre 4003.
  - Una sola isla (4002).
  - Un JSON que no es un objeto, o un `rect` con valores no numéricos, se ignora (en la versión 1 cerraba con 1011).
- **Isla → agente:** `hola`, `rect`, `decision`, `modo` (con `fisico`, alterna), `pedido`, `salir` y `ver_terminal`.
- **Agente → isla:** `estado`, `confirmar`, `decision_rechazada`, `cancelar`, `respuesta`, `fin_habla`, `seguimiento`,
  `aviso` y `modos`.
  - Estados que se mandan hoy: `reposo`, `escuchando`, `pensando`, `ejecutando`, `pregunta`, `detenido` y `juego`.
  - La isla sabe mostrar 5 más. Un estado desconocido se muestra como `reposo`.
- **Confirmaciones:** el clic físico de `decision` lo valida **el agente**
  (`entrada_fisica.clic_fisico_reciente`, ≤ 2 s). Los modos, el campo y «Salir de Cacao» los valida la isla
  (`fisico.rs`, ≤ 1,5 s, un uso por clic).
- **Versión:** una isla y un agente de versiones distintas no se conectan: se suben a la vez. Un cambio de protocolo lo
  hace Claude en los dos repositorios.
- **Bandeja de la isla** (`bandeja.rs`, `captura.rs`, isla 5554214): ninguna opción actúa sin clic físico en el
  menú; los modos llegan con `fisico`. «Permitir capturas» solo se enciende con clic físico, se apaga a los 10
  minutos y empieza apagada en cada arranque. **Sin compilar todavía** (falta permiso).

## Protecciones del lado del agente

- El agente no ve el proceso de la isla (`PROCESOS_OCULTOS`).
- `mouse` no hace clic en sus zonas: `zonas_isla`, el `rect` con 14 px de margen o la ventana entera. `teclado` no
  escribe en ella.
- `mouse` tampoco hace clic (ni mueve ni desplaza) sobre la bandeja de Windows (`TrayNotifyWnd`), su desbordamiento
  de íconos ni ninguna ventana del proceso de la isla, incluidos sus menús (`herramientas_grupo4.bandeja_o_isla_en_punto`,
  b15a349). Ante la duda, bloquea.
- Confirmar exige entrada física: [[permisos-y-bloqueos]], [[entrada-fisica]].

## Traspaso a Codex

Rama `codex/isla`, arnés, invariantes y datos personales: [[isla-codex]].

## Arranque

`config.ui.activa` y `lanzar`. El agente abre la isla (`iniciar_isla`) y la ata a un Job para que muera con él. En
modo juego queda compacta y dormida ([[modo-juego]]).

## Pruebas

- En Cacao:
  - `probar_fase7.py`: A en simulación; B con la isla real y C con un clic inyectado (con permiso);
  - `probar_campo_isla.py`;
  - `prueba_presencial_isla.py` (con el usuario).
- En la isla: `probar_invariantes.py`, `probar_arnes.py` y `npm run probar-campo` (18/18). Ver [[suites]].
