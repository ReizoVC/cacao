---
estado: verificado
verificado_commit: fb78182
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
| Falta en la lista: **65 frases × 3** | Obligatorio tras la Fase 1 (regla JSON y protecciones). Backlog #8 |
| Falta en la lista: isla v2 | Bandeja con clic físico, «Permitir capturas» 10 min, protocolo v2, mouse sin clic en la bandeja (b15a349). Compilada y probada en físico ([[compilar-isla]]) |
| «Prueba de Qwen 9B: preparada» | Coincide: copia en `modelos/comparacion_local/` (6,28 GiB) y `ejecutar.py` la lee (0b90b51). El backlog la tenía como «sin rastro»: corregido |
| «Descartados: MTP, 26B, llama.cpp servidor, WSL» | El backlog los tenía pendientes (#14–16, #18, #19, #22): pasan a descartados |
| Falta en la lista | `verificar.py` (decidir hashes, #10) y apagado automático del modo sin confirmación (#11) |

## Siguiente (orden del usuario)

| # | Punto | Estado | Quién |
|---|---|---|---|
| 1 | Verificar el cerebro y medir VRAM con `swa_full=False` | cerebro hecho; VRAM pendiente (GPU, reiniciar Cacao) | sesión de pruebas, con permiso |
| 2 | Prueba reversible de Qwen (contrato de la ronda 2) | preparada, sin lanzar | sesión de pruebas, con permiso |
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

- Rama `codex/isla` = `main` de la isla (cf09696). Codex no ha hecho commits todavía.
- **Orden enviada (2026-10-11), sin reporte aún:**
  - paso 0: vista previa con `dev.html`, que reproduce mensajes;
  - paso 1: guardarropa y calendario, portados de las fuentes Swift y JS locales;
  - paso 2: el accesorio en `localStorage`.
- **Después:** ancho y estilo (la geometría va al lote de Rust) y la línea mínima.
- **Lote de Rust abierto** (Claude): música v3 y quitar funciones sin usar de `platform/`. Necesita permiso para
  compilar ([[isla-codex]]).
