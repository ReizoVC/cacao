---
estado: verificado
verificado_commit: 65696bc
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
| 2 | Prueba reversible de Qwen (contrato de la ronda 2) | preparada (945fa17), **siguiente**. Criterio del usuario: ≥ 185/195 (ideal ≥ 190), 0 acciones peligrosas o sin confirmar, VRAM medida; Gemma se repite con el mismo código | Claude (backend), con permiso |
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

- **Pasos 0–2 hechos, revisados y en `main` de la isla (62b615c, fast-forward):**
  - vista previa `dev.html`, fuera del build;
  - guardarropa de 13 accesorios con calendario (octubre: sombrero de bruja);
  - el accesorio se guarda en `localStorage`.
  - Claude repitió las pruebas: invariantes 10/10 (sin Rust), arnés 40/40, campo 18/18, accesorios 116/116 y
    build. `dist/` no tiene el reproductor. Ningún protegido cambió.
  - **Sin verificar:** que `localStorage` persista en WebView2 (se comprueba con la próxima compilación).
  - No se portaron la física elástica de Swift ni los accesorios del saludo.
- **Pasos 3–5 hechos y en `main` de la isla (15bed5e):** ícono SVG, accesorios dentro de la isla, textos largos
  desplazables con los botones fijos, canvas al cambiar la densidad, y el diseño de la línea mínima
  (`docs/diseno-linea-minima.md`, aprobado con condiciones).
- **Hueco encontrado en la revisión y cerrado por Claude (isla 35d25d0):** una respuesta o un aviso tapaban una
  confirmación pendiente. Ahora esperan a que se cierre. Es el **invariante 10** (4 mutaciones detectadas); la
  música pasa a ser el 11. Va en el exe con la próxima compilación.
- **Siguiente orden:** implementar la línea mínima sin tocar protegidos y un aviso de «hay más» en las
  confirmaciones largas.
- **Lote de Rust abierto** (Claude): música v3 y quitar funciones sin usar de `platform/`. Necesita permiso para
  compilar ([[isla-codex]]).
