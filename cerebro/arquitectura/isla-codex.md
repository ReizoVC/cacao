---
estado: verificado
verificado_commit: 8a78d51
verificado_fecha: 2026-10-11
fuentes: [ui_isla.py, herramientas_grupo4.py]
---
# Traspaso de la isla a Codex (2026-10-11)

Lo verificado está en el repositorio de la isla, `C:\asistente-ui`, con sus commits. Aquí solo se citan los
archivos de Cacao que forman el contrato. El protocolo y las protecciones están en [[isla-websocket]].

Rama **`codex/isla`** del repositorio de la isla (sale de ca7fb21). Codex solo trabaja allí. El protocolo, los
archivos protegidos y los invariantes los cambia Claude.
- **Arnés** `windows/arnes/mock_agente.py`: reproduce `ServidorIsla` y `Confirmar` sin Cacao.
  - Escenarios: recorrido, estados y confirmaciones.
  - `--decisiones fisicas|inyectadas|alternar`.
  - Usa el puerto 8765 y no arranca si está ocupado.
  - `probar_arnes.py`: 40/40. Las sondas de la versión 2 dan lo mismo que el `ServidorIsla` real.
- **Invariantes** `windows/arnes/probar_invariantes.py`: 10/10. Son 9 invariantes (foco, entrada física, token y
  versión, solo localhost, exclusión de capturas, paso de clics, salir con clic físico, sin red y bandeja) más las
  marcas PROTEGIDO.
  - Corre `foco.rs`, `bandeja.rs`, `captura.rs` y la forma de `island.rs` con rustc suelto (VS 2022), sin compilar la
    app.
  - Se probó con roturas en una copia: 4 la primera vez y 7 con la bandeja; todas se detectan.
- La rama `codex/isla` avanzó hasta a690655 (fast-forward desde `main`).
- **Datos personales:** ninguno en el árbol ni en el historial. Queda el nombre de pila en
  `identifier`/`Cargo.toml` y el nombre y el correo del autor en los metadatos de 14 commits.

## Lote de Rust y adjuntos de Codex (2026-10-11)

- **Lote de Rust:** `docs/lote-rust.md` (protegido). Codex pide los cambios de Rust por filas; Claude los implementa
  y se compila una vez por lote. El lote abierto incluye la música ([[musica-isla]]).
- **`.codex-remote-attachments/`:** 5 JPG (28–55 KB) del 2026-10-11, de 01:17:30 a 01:17:34. Su carpeta se llama
  como la sesión de Codex `01a12989-0ecc-7a81-…`, que empezó a las 00:56:50. Se comprobó solo por los nombres y
  las fechas, sin abrir los archivos. Va en `.gitignore` (2ab8039) y no está en el historial.

## Flujo de trabajo con Codex (desde el 2026-10-11)

- Claude planifica y escribe las órdenes para Codex. El usuario las pasa y trae los reportes de Codex.
- **Fuente para portar el guardarropa de Mochi:** no hay `outfits.ts` ni `wardrobe.ts` en el fork. Está en
  local, en `NotchBuddy/Sources/CoucouKit/MochiWardrobe.swift` (selección y fechas), `MochiOutfitDrawing.swift`
  (dibujo), `tests/MochiWardrobeTests.swift` y `design/outfits/mochi-outfits.js` (dibujo de referencia en Canvas
  2D). Codex tiene permiso para leerlos, sin editarlos.
- **Vista previa en el navegador:** `dev.html` y `src/dev/`, fuera del build, reproducen mensajes con
  `cacao.recibir` (el gancho de `main.ts` en `npm run dev`). No se conectan al arnés: el navegador no tiene
  `leer_conexion` y su Origin se rechazaría. El WebSocket de verdad se prueba con el exe y el arnés, por lotes.
- **Preferencias de aspecto** (el accesorio): primero en `localStorage` del webview, sin Rust. Solo si no basta,
  se pide una fila en el lote de Rust (`settings.rs`).
