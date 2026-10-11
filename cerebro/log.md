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
