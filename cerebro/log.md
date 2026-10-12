# Registro del cerebro

Una entrada por tarea, la más reciente al final: fecha, qué cambió y commit.

Entradas anteriores: [[log-2026-10-10]], [[log-2026-10-11-isla]], [[log-2026-10-11-b]], [[log-2026-10-11-c]] y [[log-2026-10-11-d]].

## 2026-10-11: rediseño de la isla, cargo check y voz

- Isla: rediseño de Codex (4ead7c5) en `main`; rama `claude/musica` con el panel de 800 (858d001) y `cargo check` limpio (3bfef0f).
- Página nueva `voz-candidatas`: investigación web de motores de voz en Windows nativo, sin medir.

## 2026-10-11: diseño del camino rápido y del filtrado de herramientas (sin código de producción)

- ef06fb8: `medir_prompt.py`. Prompt de sistema: Gemma 3 802 tokens y Qwen 4 141; las herramientas son el 75–80 %.
- Hallazgo: Qwen no reutiliza la caché de prefijo (0/593 llamadas) y recalcula ≈ 4 300 tokens por llamada
  (1,54 s); Gemma reutiliza ≈ 3 965 (100 %).
- Páginas nuevas (propuestas): `camino-rapido` (14 de las 95 frases), `filtrado-herramientas` (variante C y, antes,
  la caché por estados para Qwen) y `frases-simples`. `simular_filtrado.py`: 53 de 95 con el núcleo solo.

## 2026-10-11: isla compilada con protocolo v3 (música, rediseño y 800 px)

- Isla 3bfef0f compilada (exe `bcdc268e…`); respaldo v2 en `_prive/respaldos`. Cacao: fusión de
  `claude/musica-v3` (2797ba4). Suites verdes; prueba física parcial con el arnés (la música llega). Páginas:
  `compilar-isla`, `musica-isla`.

## 2026-10-11: fase A (caché por estados de Qwen, banco) y fase B (camino rápido)

- 0b3624e: `cache_estado.py` y `probar_cache_estado.py`.
  - 42 casos con salidas idénticas con y sin caché (greedy, hora fija, estado alineado a `n_batch`).
  - Llamada 2,86 → 1,25 s; estado de 118 MB en RAM, sin VRAM extra; restaurar, 26 ms.
- 65 × 3 del banco con caché: 189/195 (igual que sin caché); tarea 6,83 → 3,05 s.
  - 193 de 195 casos idénticos; los 2 distintos (#56 con `ver_pantalla`) se arreglaron en d7e0ba2.
  - 76250a2: prueba sin modelo, 7/7.
  - Falta repetir la 65 × 3 (el usuario está jugando: sin GPU).
- fdf84d1: camino rápido (17 frases, volumen en la pausa del modo juego, mismo `ejecutar()`).
  `probar_camino_rapido.py` 456/456 con 8 mutaciones. Falta la 65 × 3 de `gemma` y `qwen9b`.
- Páginas: `camino-rapido` (implementado), `frases-simples`, `prompt-y-cache` (fase A), `filtrado-herramientas`
  (aparcado), `modo-juego`, `voz`, `vision-general`, `suites`, `mapa-archivos`, `comparacion-modelos`, backlog
  (#28–30) y `evaluacion-65-frases` (pendiente).

## 2026-10-11: tres corridas con GPU (caché corregida, camino rápido en los dos modelos)

- Banco con caché corregida: 189/195. Las dos corridas con caché son idénticas entre sí; #56 s22/s33 difieren de la
  corrida sin caché por los frenos posteriores (0a3ea28, e9a580d), no por la caché.
- 65 × 3 con el camino rápido. El banco no anotaba sus herramientas: corregido y recalificado (62cd4fc). Gemma
  194/195 (#44 s33); Qwen 180/195, sin (c) ejecutados (dos cierres no pedidos, frenados). Las 39 frases del camino
  rápido son correctas. Este arnés no fija la hora del pedido: las salidas de Qwen varían entre corridas.

## 2026-10-11: caché por estados en producción (qwen9b) y hora fija en el banco

- 180d71d: `probar_swa_cache.py` fija la hora del pedido; dos corridas del mismo código, 65/65 idénticas.
- b056954 (permiso del usuario): `cache_estados.py` en el perfil `qwen9b`; `probar_cache_estados.py` 13/13.
- 65 × 3 con y sin caché, hora fija: 181 frente a 182; 192/195 casos idénticos. Los 3 distintos vienen de
  `mouse_sim`, que mira el escritorio real (backlog #31), no de la caché. Ningún (c). Tarea 6,8 → 3,2 s. Activa.
- El camino rápido se queda activo (decisión del coordinador y del usuario).

