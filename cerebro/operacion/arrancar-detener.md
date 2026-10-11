---
estado: verificado
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [iniciar_cacao.py, crear_acceso_directo.ps1, voz.py, agente_minimo.py, registro_habitos.py, emergencia.py, ui_isla.py]
---
# Arrancar y detener Cacao

**Claude Code no arranca Cacao real sin permiso.** Para comprobar el lanzador, usa `--simular`.

## Arrancar

| Forma | Comando | Qué hace |
|---|---|---|
| Normal (sin terminal) | `Cacao.lnk` → `.venv\Scripts\pythonw.exe iniciar_cacao.py` | Lanza `voz.py` con `python.exe` sin ventana. La salida va a `registro_cacao.log` (rota a los 5 MB) y avisa con una notificación si cae |
| Al iniciar sesión | `iniciar_cacao.py --al-inicio` (el acceso de Inicio) | Espera 60 s y, con `ESPERAR_JUEGO=1`, espera a que se cierre un juego |
| Simulación | `.venv\Scripts\python iniciar_cacao.py --simular` | Solo comprueba y dice lo que haría; no carga nada |
| Con terminal (depuración) | `.venv\Scripts\python voz.py` | Modo voz a la vista |
| Modo texto | `.venv\Scripts\python agente_minimo.py` | Sin audio. Carga el modelo al importar |
| Registro de hábitos | `.venv\Scripts\pythonw registro_habitos.py` | Proceso aparte, sin modelo, de una sola instancia |

- `crear_acceso_directo.ps1` crea `Cacao.lnk` (ignorado por Git); `-Inicio` lo añade a la carpeta de Inicio y
  `-Quitar` lo quita. Tocar el Inicio de Windows requiere permiso.
- Solo puede haber un Cacao: si ya hay uno, avisa.
- Con un juego activo, el agente espera antes de cargar ([[modo-juego]]).
- La isla la abre el propio agente (`config.ui.lanzar`) ([[isla-websocket]]).

## Detener

- **«Salir de Cacao»** en la bandeja de la isla: salida limpia, sin aviso de error.
- **Decir o escribir «salir».**
- **Ctrl+Alt+Shift+Q:** no cierra Cacao. Detiene la tarea y deja el agente detenido hasta «reanudar»; también apaga
  el modo sin confirmación.
- **Ctrl+C** en una terminal (si se lanzó con `voz.py`).
- Al salir se borra `%LOCALAPPDATA%\Asistente\ui.json` (el token de la isla) y se cierra la isla.

## Ver qué pasa

«Ver terminal» en la bandeja abre un PowerShell con `Get-Content -Tail 300 -Wait registro_cacao.log`. Cerrarlo no
cierra Cacao.

`registro_cacao.log` puede contener pedidos del usuario: no lo leas ni lo copies sin permiso ([[mapa-datos]]).

## Pila experimental en WSL

No forma parte del arranque de Cacao. Los scripts `run_*_wsl.sh` de `.comparacion-runtime/` levantan llama-server
(puerto 18080) y vLLM-Omni (8091) para medir ([[wsl-dominio-cuda]]).
