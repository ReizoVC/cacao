# Fase 7: isla de interfaz (diseño, pendiente de aprobación)

Fecha: 2026-10-05. Estado: **solo diseño, no hay código**. Base: Coucou (github.com/Louis-CFM/coucou), clonado en
`C:\asistente-ui`, **sin remoto**: se quitó `origin`, así que un `git push` falla. No se ejecutó `npm install` ni se
compiló nada.

## 1. Comprobaciones (sin instalar nada)

| Requisito de Coucou para Windows | En este PC | Estado |
|---|---|---|
| Rust (rustup) | rustc/cargo **1.97.1**, rustup 1.29.0, toolchain `stable-x86_64-pc-windows-msvc` | OK |
| Node 20+ | **v22.12.0** (npm 10.9.0, pnpm 12.6.0) | OK |
| MSVC Build Tools ("Desarrollo para el escritorio con C++") | Instalado en la Fase 1 (llama-cpp-python se compiló con él) | OK |
| WebView2 | Runtime **154.0.4258.53** (registro) | OK |
| Windows 10/11 | **10.0.26300.9550** (Windows 11, rama Insider) | OK. `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)`, que se usa en §6, exige 10.0.19041 o posterior |

## 2. Qué es Coucou en Windows

- **Tauri 2:** backend en Rust (`windows/src-tauri`) y front-end en TypeScript sin framework (`windows/src`).
- **Mochi:** se dibuja en Canvas 2D (`src/mochi/engine.ts`).
- **La isla** es una ventana transparente de 720×320, siempre encima y fuera de la barra de tareas, que se recoge en
  el borde superior. Ya es `WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW` (`platform/windows.rs`).
- **Hoy:** `coucou-hook.exe` (crate `hook/`) recibe los hooks de Claude Code y los pasa por una tubería con nombre
  (`pipe.rs`) a la isla como eventos `hook`. Un `PermissionRequest` deja la conexión abierta hasta que la isla
  responde `allow`/`deny` (`approval_decision`). **Ese mismo esquema es el que se reutiliza** para nuestras
  confirmaciones.
- **Licencia:**
  - El código es MIT.
  - El nombre "Coucou"/"Mochi", el personaje, los iconos y los sonidos están reservados (`LICENSE-ASSETS.md`): se
    permite compilarlo "para uno mismo".
  - Es uso personal y local, sin publicar nada. Si algún día se comparte, hay que cambiar nombre, personaje y
    sonidos.

## 3. Qué se quita

| Parte | Archivos | Motivo |
|---|---|---|
| Hooks de Claude Code | `src-tauri/src/hooks.rs`, crate `hook/` (`coucou-hook.exe`), `src/island/hooks.ts`, sección de hooks de Ajustes, `bundle.resources`, `predev`/`prebuild` de `package.json` | Escribía en `%USERPROFILE%\.claude\settings.json`; nuestro agente no es Claude Code |
| Tubería con nombre | `pipe.rs` | Se reemplaza por el WebSocket local (§4) |
| API de Anthropic y chat | `claude.rs`, `src/views/chat.ts`, la sección "Claude" de Ajustes | Sin red. El chat necesitaba foco de teclado (§6) |
| Integraciones | `integrations.rs`, `src/island/integrations.ts`, `src/views/integrations.ts`, `src/mochi/minibots.ts` | Stripe, n8n, GitHub, Vercel, Resend, Notion y Cal.com hacen peticiones a internet |
| Claves | `secrets.rs`, dependencia `keyring` | Ya no hay claves que guardar |
| Red saliente | dependencia `reqwest`; CSP `connect-src` solo `ipc:` y `ws://127.0.0.1:<puerto>` | La isla no puede hablar con internet ni aunque quiera |
| Soltar archivos | `files.rs`, `src/upload/*`, `src/views/upload.ts`, `dragDropEnabled: false` | Saltaría las carpetas permitidas de `leer_archivo`. Si se quiere, en otra fase y por esas reglas |
| Ir al terminal / VS Code | `open_in_vscode` | No aplica |

**Se queda:**
- Mochi y sus animaciones, la máquina de estados de la isla (`fsm.ts`) y la tarjeta de aprobación;
- el icono de bandeja (Pausar, Salir), el ticker (para mostrar el paso actual) y el posicionamiento;
- el arranque con Windows, opcional.

**Nombre local:** `productName` "Asistente" e identificador propio, para no confundirlo con Coucou instalado.

## 4. Conexión isla ↔ agente: WebSocket local

**Quién es servidor:** el agente (Python), con `websockets`. Es un `pip install` sin permisos de administrador, que
se hará al programar. La isla (JavaScript del webview) se conecta como cliente. Así no se toca el transporte en Rust,
y si el agente se cierra, la isla solo espera y reintenta.

**Seguridad:** un `ws://` en localhost lo puede abrir **cualquier página web** del navegador, así que:
1. el servidor escucha **solo en 127.0.0.1**, puerto de `config.json` (`ui.puerto`, 8765 por defecto);
2. **token por sesión:** el agente genera 32 bytes al arrancar y los guarda en `%LOCALAPPDATA%\Asistente\ui_token`.
   Un comando Tauri `leer_token` se lo da al JS, y el primer mensaje debe traerlo; si no, se cierra la conexión;
3. **Origin:** solo se acepta el del webview de Tauri (`http://tauri.localhost`) y, en desarrollo,
   `http://localhost:1420`;
4. **una sola isla** conectada a la vez; una segunda conexión se rechaza;
5. las decisiones solo valen para el `id` pendiente y una sola vez (sin repeticiones).

**Mensajes (JSON):**

| Dirección | Mensaje | Campos |
|---|---|---|
| isla → agente | `hola` | `token`, `version` |
| agente → isla | `estado` | `estado` (ver §5), `detalle` (texto corto para el ticker: herramienta y paso) |
| agente → isla | `confirmar` | `id`, `herramienta`, `resumen`, `motivo`, `comando` (PowerShell), `vence_s` |
| isla → agente | `decision` | `id`, `si` (true/false) |
| agente → isla | `cancelar` | `id` (respondida por teclado, vencida o emergencia) |
| agente → isla | `respuesta` | `texto`, `exito` (y `sugerencia`, si la hay), `habla` (se lee en voz alta: la isla espera a `fin_habla` para empezar a esconderse) |
| agente → isla | `fin_habla` | — (Cacao terminó de hablar; desde ahí la respuesta se queda 4 a 10 s según su largo) |
| agente → isla | `seguimiento` | `activo`, `segundos` (escucha de seguimiento: indicador con cuenta atrás) |
| agente → isla | `aviso` | `texto` (modo juego, revisión de la wiki) |
| isla → agente | `rect` | `x`, `y`, `ancho`, `alto` de la isla en pantalla (§6) |

**Arranque:**
- el agente lanza `asistente-ui.exe` si no está abierto y lo cierra al salir;
- la isla reintenta conectar cada 2 s; sin agente muestra Mochi dormido;
- el modo texto y el de voz siguen funcionando **sin isla**.

## 5. Estados del agente → expresiones de Mochi

Mochi ya trae `BotStateName` (`idle`, `working`, `thinking`, `searching`, `approval`, `question`, `error`,
`finished`, `ratelimit`, `sleeping`, `dizzy`) y emotes (`happy`, `proud`, `love`, `wink`, `surprised`, `yawn`,
`annoyed`).

| Agente | Estado de Mochi | Emote / detalle |
|---|---|---|
| Esperando pedido | `idle` | — |
| Grabando (Ctrl+Espacio pulsado) | `searching` | ticker "Te escucho…" |
| Transcribiendo / pensando (`pedir_accion`) | `thinking` | ticker con el pensamiento (≤ 120 caracteres) |
| Ejecutando una herramienta | `working` | ticker "volumen", "listar_ventanas"… |
| Esperando confirmación | `approval` | tarjeta con botones (§6) |
| `preguntar_usuario` | `question` | la pregunta en el ticker |
| Respuesta con éxito | `finished` | `happy`; `proud` en tareas de varios pasos |
| Bloqueado por seguridad o error | `error` | — |
| Atajo de emergencia (detenido) | `dizzy` | ticker "Detenido: escribe 'reanudar'" |
| Hablando (Piper) | `working` | `happy` al terminar |
| Reflexión o lint en curso | `sleeping` | ticker "Ordenando mis notas…" |
| Modo juego | `sleeping` | `yawn`; ticker "En pausa: juego abierto" |
| Sugerencia del momento | `idle` | `wink` y el texto |

La isla se abre sola con `approval`, `question`, `error` y la respuesta final, como hace Coucou con sus alertas. El
resto se ve al pasar el mouse por el borde superior.

## 6. Confirmaciones con botones y protecciones

**Botones en lugar de s/n y Enter/Esc:**
- `ejecutar()` (y `pedir_confirmacion` en voz) envía `confirmar` y espera `decision` como mucho
  `confirmar_timeout_s` (30 s). Sin respuesta cuenta como **no**, como hoy.
- La tarjeta reutiliza la vista `approval` de Coucou: **Permitir / Denegar**, con el motivo y el comando de
  PowerShell completos.
- **Sin isla conectada**, sigue el método actual (consola o Enter/Esc).
- **En modo voz, ambos a la vez:** gana lo primero que llegue, botón o tecla, y al otro se le envía `cancelar`.
- Se quitan "Allow always" y similares: cada acción se confirma.

**Que el agente no pueda aprobarse a sí mismo:** mientras espera una confirmación, el agente está bloqueado en
`ejecutar()`, así que no puede usar `mouse` a la vez. Además:
- `planificar_mouse` rechaza clics dentro del último `rect` de la isla y controles de su proceso
  (`asistente-ui.exe`), como un bloqueo;
- `cerrar_app` y `enfocar_ventana` rechazan el proceso de la isla.

**No tomar el foco:**
- `WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW` **siempre**: se quita `focus_window`/`set_activating`, que solo usaba el chat;
- los botones funcionan con un clic sin activar la ventana (así funcionan hoy las tarjetas de Coucou);
- nunca `SetForegroundWindow`;
- campo de texto (añadido el 2026-10-06): es la única parte que activa la isla, y solo tras un clic físico en él;
  Enter y Esc devuelven el foco a la ventana de antes; con un clic fuera se queda en la ventana del clic
  (`src-tauri/src/foco.rs`, `src/island/campo.ts`).

**No aparecer en `ver_pantalla` ni en `listar_ventanas`:**
1. `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` al crear la ventana (`platform/windows.rs`, feature
   `Win32_UI_WindowsAndMessaging`, ya incluida). Hay que **comprobar en real** que `mss` (GDI) no la captura.
2. **Refuerzo en `vision.capturar`:** las ventanas del proceso de la isla se tapan en negro, con el mismo mecanismo de
   `tapar_sensibles`. No se avisa "ventana tapada", para que el modelo ni sepa que existe.
3. `listar_ventanas` ya la excluye por `WS_EX_TOOLWINDOW` (`_es_ventana_de_usuario`). Se añade la exclusión explícita
   por nombre de proceso, por si algún día cambia el estilo.
4. `listar_controles` rechaza el `id_ventana` de la isla.

## 7. Plan (cuando lo apruebes)

1. Quitar lo del §3 y comprobar que compila (`npm install`, `npm run tauri dev`: sin administrador; descarga paquetes
   de npm y crates).
2. Comando `leer_token`, cliente WebSocket en `src/core/bridge.ts`, mapeo de estados (§5) y tarjeta de confirmación.
3. Rust: `WDA_EXCLUDEFROMCAPTURE` y NOACTIVATE fijo; sin `reqwest`; CSP cerrada.
4. Python: `ui_isla.py` (servidor, token, Origin), `ejecutar()` y `voz.py` con botones, guardas en
   mouse/cerrar/enfocar/listar_controles/capturar.
5. Pruebas sin la isla: cliente WebSocket falso (token malo, Origin malo, segunda isla, decisión repetida, tiempo
   vencido, decisión a un id viejo).
6. Contigo frente al PC:
   - que no robe el foco;
   - que no salga en `ver_pantalla` ni en `listar_ventanas`;
   - los botones;
   - el modo voz con botones y Enter/Esc.

## 8. Decisiones (aprobadas el 2026-10-05)

| # | Decisión | Estado |
|---|---|---|
| 1 | El agente es el servidor WebSocket (token por sesión, Origin, solo 127.0.0.1) | Aprobada. **Cómo recibe la isla el token:** el agente lo genera al arrancar (32 bytes aleatorios) y lo escribe con el puerto en `%LOCALAPPDATA%\Asistente\ui.json`, en tu carpeta de usuario. La isla lo lee con el comando de Tauri `leer_conexion` y el webview lo manda en su primer mensaje. El archivo se borra al salir del agente |
| 2 | Se quitan hooks, chat, API de Anthropic, integraciones, claves, soltar archivos y red saliente | Aprobada y hecha (sin `reqwest`, `keyring` ni `tokio`) |
| 3 | Campo de texto en la isla | Pospuesta el 2026-10-05; **hecho el 2026-10-06**: foco solo con clic físico en el campo; Enter y Esc lo devuelven a la ventana de antes y un clic fuera lo deja en la ventana del clic; el texto entra como un pedido normal (`{"tipo": "pedido"}`); teclado no escribe en la isla. Probado en simulación; la prueba visual, pendiente |
| 4 | Mapa de estados del §5 | Aprobada y hecha (`src/island/agente.ts`) |
| 5 | Confirmación con botones y "no" a los 30 s | Aprobada con requisitos de seguridad, hechos: (a) **solo entrada física**: hooks de bajo nivel; Enter/Esc con `LLKHF_INJECTED` y botones tras un clic con `LLMHF_INJECTED` se rechazan (`entrada_fisica.py`); (b) la herramienta mouse no puede hacer clic dentro de la isla; (c) los botones no quitan el foco (`WS_EX_NOACTIVATE`, que ahora se vuelve a aplicar cada vez que Tauri cambia la transparencia de clics) |
| 6 | Invisible para el agente | Aprobada y hecha. **Se puede desactivar para grabar la isla:** bandeja → "Permitir capturas (para grabar la isla)" o el interruptor en Ajustes de la isla. Aun así, el agente la tapa en negro en sus capturas |
| 7 | Nombre local "Asistente", repositorio sin remoto | Aprobada y hecha |

**Cómo compilar la isla:** `C:\asistente-ui\windows`, `npm install` y luego `npx tauri build --no-bundle` desde un entorno
de VS 2022 Community (`vcvars64.bat`). VS 18 Insiders no trae las librerías de C++ y el enlazado falla
(`msvcrt.lib`). El ejecutable queda en `target\release\asistente-ui.exe` y `config.json` → `ui.exe` apunta ahí.
