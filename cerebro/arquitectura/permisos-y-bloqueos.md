---
estado: verificado
verificado_commit: 9230d4d
verificado_fecha: 2026-10-12
fuentes: [herramientas.json, agente_minimo.py, voz.py, modo_directo.py, ui_isla.py, entrada_fisica.py, herramientas_grupo1.py, herramientas_powershell.py, confirmacion_voz.py]
---
# Permisos, bloqueos y confirmaciones

## ¿Dónde se decide si una acción pide confirmación?

En `agente_minimo.ejecutar(nombre, args)`, en este orden. Las acciones del camino rápido (`paso_rapido`,
[[camino-rapido]]) pasan por el mismo `ejecutar()`: solo sustituyen la elección del modelo.

1. `camino_conocido()` aplica los [[protecciones|obstáculos]] aprendidos.
2. `PLANIFICADORES[nombre]` valida sin efectos (PowerShell, teclado). Si falla, devuelve el error sin preguntar.
3. Tarea contaminada + herramienta de `GUARDAN_SOBRE_REIZO` → pregunta «¿Lo pidió el usuario?».
4. `decision_modo()` consulta el modo sin confirmación (`modo_directo.Politica.decidir`).
5. `permiso == "confirmar"` y no va directa → `confirmar()`.

**En modo voz**, `voz.ejecutar_voz()` envuelve `ejecutar()`: toda herramienta fuera de `SOLO_LECTURA` también
pide confirmación, aunque su permiso sea «libre» (abrir, volumen…).

## Niveles (`herramientas.json`)

- `libre`: se ejecuta sin preguntar (en voz, solo las de lectura).
- `confirmar`: cerrar_app, mouse, teclado, mover_archivo, deshacer_movimiento, ejecutar_powershell,
  autocompletar_login.
- `prohibido`: no existe como herramienta (`acciones_prohibidas`: borrar, registro, configuración, instalar,
  apagar).

## Bloqueos

- **Apps:** `limites.apps_sensibles` tiene listas `bloqueadas` y `confirmar` por ejecutable o AppID
  (`nivel_app()`).
- **Archivos:** `listar_carpeta`, `leer_archivo` y `mover_archivo` solo trabajan dentro de `carpetas_permitidas`
  (Escritorio, Documentos, Descargas, Imágenes, Música y Vídeos del perfil). Los `patrones_sensibles` ocultan o
  rechazan nombres en toda la ruta.
- **PowerShell:** `planificar_powershell` exige comando y motivo, y rechaza `powershell_patrones_bloqueados`.
  Siempre pregunta, también en el modo sin confirmación. Los patrones no son un sandbox: la barrera real es la
  confirmación.
- **Isla:** el agente no ve el proceso `asistente-ui.exe`; `teclado` no escribe en la isla y `mouse` no hace clic
  en ella, en sus menús, en la bandeja de Windows ni en su desbordamiento de íconos ([[isla-websocket]]).

## Confirmación física

`confirmar()` usa `ui_isla.Confirmar`:
- **Enter/Esc:** solo teclas sin `LLKHF_INJECTED`.
- **Botones de la isla:** solo si el último clic fue físico.
- **Voz:** «confirmo la instrucción» en una grabación aparte (`confirmacion_voz.py`), con voz real y sin otro audio
  sonando.

Sin respuesta en 30 s = no. En segundo plano y sin isla conectada = no.

## Modo sin confirmación (`modo_directo.py`)

- Empieza apagado. Solo lo cambia un clic físico en la isla o en la bandeja (`cambiar_modo`, con
  `fisico=True`); la emergencia lo apaga.
- `Politica.decidir()` deja ir directas:
  - volumen, deshacer_movimiento y mouse;
  - buscar_web, abrir_app, enfocar_ventana y cerrar_app (normal), con condiciones si antes se miró la pantalla;
  - mover_archivo, con límites (`_mover`);
  - teclado, salvo un texto que no sale del pedido después de leer contenido externo.
- Siempre preguntan: `SIEMPRE_CONFIRMAR` (incluye PowerShell) y cerrar a la fuerza. Si en la tarea entró contenido
  externo, todo vuelve a preguntarse, excepto mouse y teclado.
- No hay apagado automático por tiempo ([[backlog]]).

Ver [[entrada-fisica]] e [[isla-websocket]].
