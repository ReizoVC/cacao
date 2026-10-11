---
estado: verificado
verificado_commit: a42d084
verificado_fecha: 2026-10-11
fuentes: [ui_isla.py, pedidos.py, agente_minimo.py, voz.py, entrada_fisica.py, config.json, diseno_fase7.md, prueba_presencial_isla.py, medir_isla_juego.py]
---
# Isla y WebSocket

La isla es una interfaz flotante (Tauri 2 y WebView2) en un repositorio aparte, `C:\asistente-ui` (`windows/`).
Cacao lanza el exe de `config.ui.exe`. Diseño: `diseno_fase7.md`. Adapta Coucou: la licencia de los assets está en
[[riesgos]].

El `CLAUDE.md` y el `docs/AGENTS.md` de ese repositorio son del Coucou original (macOS) y **no** describen la isla. Lo
que vale es el `AGENTS.md` de la raíz (desde ca7fb21).

## Contrato: `C:\asistente-ui\docs\protocolo.md` (versión 1)

Escrito desde el código el 2026-10-11 (b7b81a7). Resumen:
- **Conexión:** `ui_isla.ServidorIsla` (el agente es el servidor).
  - Solo `127.0.0.1:8765`.
  - Token por sesión (`token_urlsafe(32)`) en `%LOCALAPPDATA%\Asistente\ui.json`, que se borra al salir.
  - Origin solo `tauri.localhost` o `localhost:1420`; si no, 403.
  - Primer mensaje `hola` en ≤ 5 s; si no llega o el token no coincide, cierre 4001.
  - Una sola isla (4002).
  - Un JSON que no es un objeto, o un `rect` con valores no numéricos, cierra con 1011.
- **Isla → agente:** `hola`, `rect`, `decision`, `modo` (con `fisico`, alterna), `pedido`, `salir` y `ver_terminal`.
- **Agente → isla:** `estado`, `confirmar`, `decision_rechazada`, `cancelar`, `respuesta`, `fin_habla`, `seguimiento`,
  `aviso` y `modos`.
  - Estados que se mandan hoy: `reposo`, `escuchando`, `pensando`, `ejecutando`, `pregunta`, `detenido` y `juego`.
  - La isla sabe mostrar 5 más. Un estado desconocido se muestra como `reposo`.
- **Confirmaciones:** el clic físico de `decision` lo valida **el agente**
  (`entrada_fisica.clic_fisico_reciente`, ≤ 2 s). Los modos, el campo y «Salir de Cacao» los valida la isla
  (`fisico.rs`, ≤ 1,5 s, un uso por clic).
- **Versión:** la isla manda `version: 1` y el agente no la comprueba. Un cambio de protocolo lo hace Claude en los dos
  repositorios.

## Protecciones del lado del agente

- El agente no ve el proceso de la isla (`PROCESOS_OCULTOS`).
- `mouse` no hace clic en sus zonas: `zonas_isla`, el `rect` con 14 px de margen o la ventana entera. `teclado` no
  escribe en ella.
- Confirmar exige entrada física: [[permisos-y-bloqueos]], [[entrada-fisica]].

## Traspaso a Codex (2026-10-11)

Rama **`codex/isla`** del repositorio de la isla (sale de ca7fb21). Codex solo trabaja allí. El protocolo, los
archivos protegidos y los invariantes los cambia Claude.
- **Arnés** `windows/arnes/mock_agente.py`: reproduce `ServidorIsla` y `Confirmar` sin Cacao.
  - Escenarios: recorrido, estados y confirmaciones.
  - `--decisiones fisicas|inyectadas|alternar`.
  - Usa el puerto 8765 y no arranca si está ocupado.
  - `probar_arnes.py`: 35/35. El handshake y los errores coinciden con el `ServidorIsla` real (sondas del
    2026-10-11).
- **Invariantes** `windows/arnes/probar_invariantes.py`: 9/9. Son 8 invariantes (foco, entrada física, token y
  Origin, solo localhost, exclusión de capturas, paso de clics, salir con clic físico, sin red) más las marcas
  PROTEGIDO.
  - Corre `foco.rs` y la forma de `island.rs` con rustc suelto (VS 2022), sin compilar la app.
  - Se probó estropeando cuatro invariantes en una copia: los cuatro fallan.
- **Hueco conocido, sin arreglar:** en la bandeja, «Permitir capturas», «Pausar», «Abrir» y «Ajustes» no exigen clic
  físico, y `zonas_isla` no cubre el menú de la bandeja ([[riesgos]]).
- **Datos personales:** ninguno en el árbol ni en el historial. Queda el nombre de pila en
  `identifier`/`Cargo.toml` y el nombre y el correo del autor en los metadatos de 14 commits.

## Arranque

`config.ui.activa` y `lanzar`. El agente abre la isla (`iniciar_isla`) y la ata a un Job para que muera con él. En
modo juego queda compacta y dormida ([[modo-juego]]).

## Pruebas

- En Cacao:
  - `probar_fase7.py`: A en simulación; B con la isla real y C con un clic inyectado (con permiso);
  - `probar_campo_isla.py`;
  - `prueba_presencial_isla.py` (con el usuario).
- En la isla: `probar_invariantes.py`, `probar_arnes.py` y `npm run probar-campo` (18/18). Ver [[suites]].
