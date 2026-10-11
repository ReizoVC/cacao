---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [entrada.py, entrada_fisica.py, ui_isla.py, emergencia.py, diagnostico_actividad.py]
---
# Entrada física

Hay dos usos distintos: medir la actividad y aceptar confirmaciones.

## Actividad (`entrada.py`, Fase 6)

- **Teclado y mouse:** se miden con Raw Input (`RIDEV_INPUTSINK` en una ventana oculta), no con
  `GetLastInputInfo`. En este PC, `GetLastInputInfo` se reiniciaba sin ninguna entrada (ver [[lecciones]]).
- **Entrada inyectada:** `SendInput` (las herramientas mouse y teclado del agente, macros, control remoto) llega sin
  dispositivo y no cuenta.
- **Mouse:** cuentan los botones, la rueda y el movimiento por encima de un mínimo (la deriva del sensor no).
- **Mandos:** XInput y Raw Input HID, con zona muerta (un stick que deriva o el giroscopio no cuentan).
- **Usuarios:** el registro de hábitos (`inactivo`), la vigilancia de la reflexión y el modo juego.
- **Plan B:** si Raw Input falla, se vuelve a `GetLastInputInfo` y se avisa (`raw_teclado_ok`).

## Confirmaciones (`entrada_fisica.py`, Fase 7)

- Hooks de bajo nivel solo mientras se espera una respuesta.
- **Teclado:** Enter = sí y Esc = no, solo sin `LLKHF_INJECTED` (ni `LOWER_IL_INJECTED`). Mientras se espera, Enter
  y Esc no llegan a ninguna app.
- **Mouse:** un «Permitir» o «Denegar» de la isla vale solo si el último clic dentro de la isla fue físico y
  reciente.
- **Resultado:** el agente nunca puede aprobar sus propias acciones con mouse o teclado.
- `procesar_tecla` y `procesar_clic` tienen la lógica sin Win32, y las pruebas la usan.

## Lo mismo vale para

- los cambios de modo desde la isla o la bandeja ([[permisos-y-bloqueos]]);
- el campo de texto de la isla ([[isla-websocket]]);
- la tecla Espacio de la confirmación por voz.

## Pruebas

`probar_actividad_fisica.py` y `probar_fase7.py` (A en simulación; C con un clic inyectado en la isla real)
([[suites]]). Falta probar con un mando real: [[pendientes-presenciales]].
