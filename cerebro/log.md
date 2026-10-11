# Registro del cerebro

Una entrada por tarea, la más reciente al final: fecha, qué cambió y commit.

Entradas anteriores: [[log-2026-10-10]].

## 2026-10-11: traspaso de la isla a Codex (C:\asistente-ui: b7b81a7, f48e837, d8576e0 y ca7fb21)

- **En el repositorio de la isla:**
  - `docs/protocolo.md` (versión 1, escrito desde el código);
  - el arnés `windows/arnes/mock_agente.py` y `probar_arnes.py` (35/35, con las mismas respuestas que el
    `ServidorIsla` real);
  - `probar_invariantes.py` (8 invariantes más las marcas: 9/9; detecta las 4 roturas provocadas);
  - la marca PROTEGIDO en 12 archivos (solo un comentario);
  - `AGENTS.md`;
  - la rama `codex/isla`.
- **Sin compilar la app, sin abrir la isla, sin GPU y sin tocar Cacao.** `foco.rs` y la forma de `island.rs` se
  probaron con rustc suelto (VS 2022).
- **Página corregida:** `isla-websocket`. Decía que la isla tenía «su propio CLAUDE.md», pero ese archivo es del
  Coucou original. Además se añadieron el protocolo y el traspaso.
- **Riesgo nuevo:** la bandeja permite cambiar «Permitir capturas» sin clic físico. Se documentó y no se arregló.
- **Datos personales en la isla:** ninguno en archivos. Quedan el nombre de pila y el correo del autor en los
  metadatos de los commits.

## 2026-10-11: bandeja de la isla cerrada y protocolo v2 (Cacao b15a349 y 8a78d51; isla 5554214, 41656f0 y a690655)

- **Agente:** `mouse` no hace clic en la bandeja de Windows, en su desbordamiento de íconos ni en los menús de la
  isla. `probar_grupo4` tiene 14 pruebas nuevas, que fallan con 3 roturas en una copia. `ui_isla` pasa a la
  versión 2: comprueba la versión (4003) e ignora los JSON que no son objetos. `probar_fase7` A: 32/32.
- **Isla:**
  - `bandeja.rs` y `captura.rs`: ninguna opción del menú actúa sin clic físico, y «Permitir capturas» dura 10
    minutos y no sobrevive a un reinicio;
  - `agente.ts` y `docs/protocolo.md` en la versión 2; el arnés da 40/40;
  - invariantes 10/10, que detectan las 7 roturas provocadas;
  - `codex/isla` avanzó hasta a690655.
- **Sin compilar la app** (falta el permiso). Hasta recompilar, Cacao rechaza la isla vieja con 4003 (backlog #11d).

## 2026-10-11: isla compilada con la bandeja y el protocolo v2 (isla a690655; cerebro: compilar-isla)

- **Antes:** sin procesos de Cacao ni de la isla, salvo el registrador de hábitos (el usuario lo dejó seguir) y
  con el puerto 8765 libre.
- **Respaldo de la v1:** en `_prive\respaldos` del repositorio de la isla. Volver a la v1 exige revertir también
  8a78d51 (y b15a349, a petición del usuario) en Cacao.
- **Pruebas antes de compilar:** Rust sueltas 23/23.
- **Build:** código 0 en 144 s. Memoria disponible mínima de 2,03 GiB; el registrador siguió intacto.
- **Resultado:** el exe del 2026-10-11 01:22:58 embebe el bundle con `version` 2 (`kt=2`).
- **Pruebas después de compilar:** invariantes 10/10, arnés 40/40, campo 18/18.
- **Sin abrir la isla.** Los pasos de la prueba física están en `pendientes-presenciales` #7.
- **Visto en la isla:** una carpeta sin seguimiento, `.codex-remote-attachments/`, que no es de Claude. No se tocó.

## 2026-10-11: prueba física de la bandeja, adjuntos de Codex y diseño de la música

- **Prueba física con el arnés (sin Cacao ni GPU):** A–F correctos (detalle en `compilar-isla`).
  - **F confirmado por el usuario:** al reabrir la isla, «Permitir capturas» salió desmarcada en el menú.
  - Un único clic inyectado, desde un script, contra el arnés: no hizo nada.
  - «Permitir capturas» se apagó sola a los 10 minutos justos y no sobrevivió a un reinicio.
  - Solo se leyeron las líneas `bandeja:` y `captura` del registro de la isla, con permiso del usuario.
- **`.codex-remote-attachments/`:** 5 JPG de la sesión de Codex `01a12989-…` (2026-10-11, 01:17), sin abrirlos.
  Va en `.gitignore` (isla 2ab8039) y no está en el historial.
- **Diseño de la música (protocolo v3, sin implementar):** isla cf09696. Las páginas nuevas son `musica-isla` y,
  en la isla, `docs/lote-rust.md` (protegido).

## 2026-10-11: Claude coordina a Codex

- Claude planifica y da las órdenes a Codex (`isla-codex`, sección «Flujo de trabajo»).
- Primera orden: vista previa por reproducción de mensajes (sin WebSocket ni archivos protegidos) y portar el
  guardarropa desde las fuentes Swift y JS locales del Coucou original.
