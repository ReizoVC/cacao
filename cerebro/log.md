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

## 2026-10-11: arranque de la Fase 1, VRAM y 65 × 3 detenida (3ad35c7, 76baceb, ac148e6, ce74786)

- **Arranque sin micrófono ni herramientas reales** (`medir_arranque.py`): importar no usa la GPU, `cargar_modelo()`
  carga una vez y el pedido simulado se resuelve. VRAM 787 → 9 819 MiB (pico 9 845); privada 11 105 MB.
  Origen: `resultados_arranque_fase1.json` (ignorado por Git).
- **65 × 3 detenida** en semilla 11, caso 42: 35/42 frente a 42/42 de la base. Hipótesis: `swa_full=false` con
  reutilización del prefijo KV entre tareas. No se revirtió nada. Detalle en `backlog` #5 y #8.
- `entrenar_cacao.py` lee de `D:\Cacao\entrenamiento\` (permiso del usuario). Lista de comprobación de Qwen 9B:
  `lista-qwen9b-ronda2`.

## 2026-10-11: producción restaurada sin swa_full (397d0a2, a6e0cd6)

- Orden del coordinador y permiso del usuario: `config.json` sin la clave `swa_full` (valor por defecto) y una nota
  del motivo. Cacao no estaba en marcha. `probar_carga_modelo.py` ajustada a la nueva configuración: 13/13.

## 2026-10-11: prueba A/B/C de swa_full (dd51ba6): la hipótesis no se confirma

- `probar_swa_cache.py`, los 7 casos fallidos de la semilla 11 en orden: A (false, sin vaciar) 7/7, B (false,
  vaciando) 7/7 y C (por defecto) 7/7. A no reprodujo los fallos: se paró ahí y la 65 × 3 no se lanzó.
- Tabla en `swa-full-false`. Sin entrada en `lecciones.md`: la causa no está confirmada.
- 21 páginas reselladas tras el cambio de `config.json` (una sola clave); `hoja-de-ruta` no se tocó.

## 2026-10-11: estrategia del usuario

- Página nueva `estrategia-recursos`: ahorrar memoria primero, el modelo decide y el código hace, y propuesta de
  memoria de experiencia (sin código).

## 2026-10-11: pasos 3–5 de Codex e invariante 10 de la isla

- Isla 1085c15, 7b4b0a8, 1fbcf2c y 15bed5e revisados; pruebas repetidas y fast-forward de `main`.
- En la revisión: `alert()` dejaba que una respuesta o un aviso taparan la confirmación pendiente. Arreglado en
  `agente.ts` (aplazados hasta cerrar la tarjeta) con el invariante 10 (isla 35d25d0). Detalle en `hoja-de-ruta`.

## 2026-10-11: Qwen 9B preparada sin sobrescribir (945fa17), sin lanzar

- `ejecutar.py --salida DIR` (por defecto igual) y `resumir_qwen9b.py` (un único `resumen_qwen9b_<fecha>.json`).
  Prueba en seco: SHA256 de 368 archivos iguales antes y después.
- `lista-qwen9b-ronda2`: criterio **propuesto** por el coordinador (≥ 193/195, 0 acciones peligrosas o sin confirmar,
  VRAM menor que Gemma, latencia ≤ +20 %), pendiente de confirmar por el usuario.
- Visto al leer: `--swa-full` de `ejecutar.py` está roto desde eb5a9c4 (`comandos`, `comparacion-modelos`).

## 2026-10-11: 65 × 3 con producción restaurada (sin swa_full)

- `probar_swa_cache.py C --casos todos` (dbb0e42): 1.ª herramienta 195/195, completas 194/195 (base 193/195).
  Semilla 11 sin fallos en #26–42. Detalle en `evaluacion-65-frases`.

## 2026-10-11: brazo A sobre #1–42 (swa_full=false, sin vaciar): 42/42

- Los fallos de la primera corrida no se reproducen ni con la secuencia larga; ningún umbral de tokens coincide
  (tabla en `swa-full-false`). Causa abierta; sin arreglos ni entrada en `lecciones.md`.
