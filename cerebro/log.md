# Registro del cerebro

Una entrada por tarea, la más reciente al final: fecha, qué cambió y commit.

Entradas anteriores: [[log-2026-10-10]] y [[log-2026-10-11-isla]].

## 2026-10-11: Claude coordina a Codex

- Claude planifica y da las órdenes a Codex (`isla-codex`, sección «Flujo de trabajo»).
- Primera orden: vista previa por reproducción de mensajes (sin WebSocket ni archivos protegidos) y portar el
  guardarropa desde las fuentes Swift y JS locales del Coucou original.

## 2026-10-11: hoja de ruta del usuario cruzada con el backlog

- Página nueva `hoja-de-ruta`: diferencias con la lista del usuario, el «Siguiente» y el estado de Codex.
- `backlog`: WSL, llama.cpp servidor, MTP y 26B pasan a descartados; la prueba de Qwen 9B está preparada (0b90b51).
- `pendientes-presenciales`: añadidos Whisper pequeño, el «sí» solo y el mando; nota de la captura del 2026-10-11.

## 2026-10-11: pasos 0–2 de Codex revisados y en main de la isla

- Isla 9379465, d47d406 y 62b615c: vista previa local, guardarropa con calendario y accesorio en `localStorage`.
- Revisado el diff (sin red, sin protegidos, sin innerHTML con datos) y repetidas las pruebas. Fast-forward de
  `main` de la isla a 62b615c, sin push. Detalle en `hoja-de-ruta`.
