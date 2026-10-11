---
estado: verificado
verificado_commit: d4b36dd
verificado_fecha: 2026-10-10
fuentes: [ui_isla.py, pedidos.py, agente_minimo.py, config.json, diseno_fase7.md]
---
# Isla y WebSocket

La isla es una interfaz flotante (Tauri y WebView2) en un repositorio aparte, `C:\asistente-ui`, con su propio
`CLAUDE.md`. El ejecutable que se lanza está en `config.ui.exe`. Diseño: `diseno_fase7.md` (adapta Coucou; ver la
licencia de assets en [[riesgos]]).

## Conexión (`ui_isla.py`, el agente es el servidor)

- Solo `127.0.0.1:8765`.
- Token por sesión de 32 bytes. Se escribe al arrancar en `%LOCALAPPDATA%\Asistente\ui.json`, se borra al salir
  y, si no coincide, se cierra con el código 4001.
- Origin: solo el webview de Tauri (`tauri.localhost`) y `localhost:1420` en desarrollo. Cualquier otro recibe 403.
- Una sola isla a la vez (4002).

## Mensajes

- **Agente → isla:**
  - estados (pensando, ejecutando, pregunta, juego, reposo…);
  - modos (`enviar_modos`);
  - confirmaciones;
  - avisos.
- **Isla → agente:**
  - respuestas a confirmaciones (válidas solo con un clic físico, comprobado con un hook de mouse);
  - `pedido` del campo de texto (`pedidos.py`), que entra igual que la consola;
  - cambios de modo (`cambiar_modo`, solo si `fisico`);
  - `salir` y `ver_terminal` desde la bandeja.

## Protecciones

- El agente no ve el proceso de la isla (`PROCESOS_OCULTOS`).
- `mouse` no hace clic en sus zonas (`herramientas_grupo4.zonas_isla`) y `teclado` no escribe en ella.
- El campo de texto solo se abre con un clic físico.
- Confirmar exige entrada física: [[permisos-y-bloqueos]], [[entrada-fisica]].

## Arranque

`config.ui.activa` y `lanzar`. El agente abre la isla (`iniciar_isla`) y la cierra al salir. En modo juego la isla
queda compacta y dormida ([[modo-juego]]).

## Pruebas

- `probar_fase7.py`: A en simulación, B con la isla real y C con un clic inyectado.
- `probar_campo_isla.py`.
- En el repositorio de la isla: `npm run probar-campo` (ver [[suites]]).
