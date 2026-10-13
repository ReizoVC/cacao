---
estado: verificado
verificado_commit: 97cea59
verificado_fecha: 2026-10-13
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
| 1 | `swa_full=False` | cerrado: revertido en Gemma (397d0a2), solo en el perfil `qwen9b`, donde no cambia la VRAM ([[swa-full-false]], [[memoria-liberable]]) | — |
| 2 | Prueba reversible de Qwen | Producción: 173 → 182 (cierre rápido arreglado) → 182 con el contrato de la ronda 2, con casos (c) de cierres no pedidos ([[qwen-como-cerebro]]). No pasa el criterio, pero **el usuario decide usarlo una semana (desde el 2026-10-11)**: se descarta si resulta molesto o impreciso. **Activo desde 5e9eee0**, con el freno nuevo de `cerrar_app` (98c763e). Al final, cifras con `resumir_semana_qwen.py --con-permiso`. Vuelta atrás: `"modelo_activo": "gemma"` y reiniciar | usuario; Claude (backend) |
| 3 | Cierre rápido con `mensaje_final` | hecho: validado en los dos modelos y apagado en Qwen (69297e4, d95855d) | [[cierre-rapido-mensaje-final]] |
| 4 | Hook y skill para que cada chat use el cerebro | sin empezar | — |
| 5 | Reorganizar archivos | después del 2 | — |
| 6 | Spotify: teclas multimedia, Chromium, visión | sin empezar. Enlaza con la música de la isla ([[musica-isla]]) | — |
| 7 | Camino rápido y caché por estados de Qwen | **hechos y activos** (fdf84d1, b056954); filtrado aparcado | [[camino-rapido]], [[cache-estados]] |
| 8 | Voz Qwen3-TTS 0.6B (llama.cpp nativo, A1_equilibrada) | **activa en producción** con Piper de respaldo (c0945a6, a04c212); **el usuario la aprueba** (2026-10-13). Falta decidir el saludo (empezar antes con pausa o más tarde sin ella) | [[voz-qwen3]] |

**Memoria de experiencia: hecha** (97cea59; [[memoria-experiencia]]): 65 × 3 Gemma 195, Qwen 187. Falta la prueba
presencial. **Siguiente: Spotify (#6).**

**Futuro:** adaptadores por app, Jev en modo sombra, cerrar pestañas por
nombre, Tailscale, especialista visual, SRS 1.3. Ninguno tiene código.

**Solo el usuario:** las dos evaluaciones a ciegas (backlog #20 y #21) y tareas de seguridad personal que no se
detallan aquí. El usuario pidió no activar nada con permisos amplios hasta cerrar el diagnóstico de seguridad.

## Frontend (isla), a cargo de Codex

**Compilado el 2026-10-11** (isla 3bfef0f, Cacao 2797ba4; [[compilar-isla]]): rediseño de tres niveles (Figma,
página 02), panel de 800 px, música v3 ([[musica-isla]]), invariante 10, guardarropa y línea mínima. Prueba física
parcial: falta la confirmación, el armario tras reiniciar (persistencia en WebView2) y «Pausar» con teclado.

**Siguiente (Codex):** línea fina con 5 barras que se mueven cuando Cacao habla (`State.cacaoHabla`, isla 912abce),
curvas de notch e icono de seguimiento (b38feb3, en `main`). Falta su corrección de la respuesta hablada con la isla
abierta. Luego se compila (solo interfaz) y se completa la prueba física.
