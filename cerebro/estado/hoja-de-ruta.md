---
estado: verificado
verificado_commit: 031e0b8
verificado_fecha: 2026-10-11
fuentes: [config.json, comparacion_modelos/ejecutar.py, cerebro/frescura.py]
---
# Hoja de ruta del usuario, cruzada con el repositorio (2026-10-11)

La lista viene del usuario (estado del proyecto del 2026-10-11). Aquí cada punto se cruza con [[backlog]] y Git.
**Diferencia** = la lista y el repositorio no dicen lo mismo.

## Diferencias con la lista del usuario

| Punto de la lista | Lo que dice el repositorio |
|---|---|
| «Cerebro: 29 páginas por revisar; `suites.md` y `lecciones.md` desactualizadas» | **Ya no.** `frescura.py`: 45 páginas, 0 por revisar (fb78182). Las dos páginas se corrigieron en a42d084 |
| «CLAUDE.md más 41 páginas» | 45 páginas |
| «Fase 1: otra sesión la cambió» | Fue la sesión que coordina (commits 7d31aa7, 8e72787, c6a74f3, 14c17cb, eb5a9c4). Suites sin modelo al día. Falta reiniciar Cacao y medir VRAM (backlog #5 y #11c) |
| Falta en la lista: **65 frases × 3** | Hecha el 2026-10-11 con producción: 194/195 (`resumen_65x3_C.json`). Backlog #8 |
| Falta en la lista: isla v2 | Bandeja con clic físico, «Permitir capturas» 10 min, protocolo v2, mouse sin clic en la bandeja (b15a349). Compilada y probada en físico ([[compilar-isla]]) |
| «Prueba de Qwen 9B: preparada» | Coincide: copia en `modelos/comparacion_local/` (6,28 GiB) y `ejecutar.py` la lee (0b90b51). El backlog la tenía como «sin rastro»: corregido |
| «Descartados: MTP, 26B, llama.cpp servidor, WSL» | El backlog los tenía pendientes (#14–16, #18, #19, #22): pasan a descartados |
| Falta en la lista | `verificar.py` (decidir hashes, #10) y apagado automático del modo sin confirmación (#11) |

## Siguiente (orden del usuario)

| # | Punto | Estado | Quién |
|---|---|---|---|
| 1 | Verificar el cerebro y medir VRAM con `swa_full=False` | revertido (397d0a2). Producción sin la clave: 65 × 3 = 194/195 (base 193). Los 35/42 con false no se reproducen (brazo A 42/42): causa abierta ([[swa-full-false]]). En pausa hasta saber si Gemma sigue | Claude (backend) |
| 2 | Prueba reversible de Qwen | Producción: 173 → 182 (cierre rápido arreglado) → 182 con el contrato de la ronda 2, con casos (c) de cierres no pedidos ([[qwen-como-cerebro]]). No pasa el criterio, pero **el usuario decide usarlo una semana (desde el 2026-10-11)**: se descarta si resulta molesto o impreciso. Vuelta atrás: `"modelo_activo": "gemma"` y reiniciar | usuario; Claude (backend) |
| 3 | Cierre rápido con `mensaje_final` | pendiente | usuario decide ([[cierre-rapido-mensaje-final]]) |
| 4 | Hook y skill para que cada chat use el cerebro | sin empezar | — |
| 5 | Reorganizar archivos | después del 2 | — |
| 6 | Spotify: teclas multimedia, Chromium, visión | sin empezar. Enlaza con la música de la isla ([[musica-isla]]) | — |
| 7 | Camino rápido y filtrado de herramientas | sin empezar | — |
| 8 | Qwen3-TTS 0.6B en Windows (RAM) | sin medir; WSL descartado | — |

**Futuro:** adaptadores por app, memoria de experiencia (diseño aprobado), Jev en modo sombra, cerrar pestañas por
nombre, Tailscale, especialista visual, SRS 1.3. Ninguno tiene código.

**Solo el usuario:** las dos evaluaciones a ciegas (backlog #20 y #21) y tareas de seguridad personal que no se
detallan aquí. El usuario pidió no activar nada con permisos amplios hasta cerrar el diagnóstico de seguridad.

## Frontend (isla), a cargo de Codex

Detalle por paso en `log-2026-10-11-b`. En `main` de la isla (15bed5e y 35d25d0):
- vista previa `dev.html` fuera del build, guardarropa con calendario y accesorio en `localStorage` (**sin
  verificar** que persista en WebView2);
- textos largos desplazables y la línea mínima diseñada;
- **invariante 10** (Claude): una respuesta o un aviso ya no tapan una confirmación pendiente.

En curso:
- **Línea mínima** (Codex, e30e4fe y e441b90): no fusionada. Con la línea apagada cambiaba el comportamiento;
  Codex la corrige.
- **Música v3** (Claude, [[musica-isla]]): ramas `claude/musica` (isla) y `claude/musica-v3` (Cacao), sin compilar.
  Se fusionan a la vez.
- **Después:** una sola compilación con permiso y una prueba presencial de todo junto ([[compilar-isla]]).
- **Antes de esa prueba (aprobado por el usuario):** `cargo check` en el worktree `C:sistente-ui-claude`
  (sin `.exe` y sin cerrar Cacao); arreglar lo que salga y borrar su `target` al terminar.
