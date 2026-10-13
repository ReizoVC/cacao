---
estado: verificado
verificado_commit: a04c212
verificado_fecha: 2026-10-12
fuentes: [cache_estados.py, modelo.py, agente_minimo.py, config.json, probar_cache_estados.py, comparacion_modelos/cache_estado.py, comparacion_modelos/probar_cache_estado.py, comparacion_modelos/probar_swa_cache.py, comparacion_modelos/comparar_corridas.py]
---
# Caché por estados del prompt de sistema (Qwen 9B)

Qwen no reutiliza el prefijo de la caché KV y recalculaba ≈ 4 300 tokens por llamada ([[prompt-y-cache]]). Se guarda
el estado tras el prompt de sistema y se restaura en cada llamada. **Activa en el perfil `qwen9b`** desde b056954.

## Fase A: caché por estados para Qwen (banco, 2026-10-11; producción no lo usa)

`comparacion_modelos/cache_estado.py` guarda el estado de llama.cpp tras el prompt de sistema, alineado a `n_batch`:
4 096 de los 4 194–4 265 tokens comunes. Lo restaura antes de cada llamada; tras restaurar, `kv_cache_seq_rm` sí
funciona (94/94 y 499/499).

- **Corrección** (`probar_cache_estado.py`, `datos/cache_estado/comparacion_qwen9b.json`): 42 casos de la secuencia
  larga, semilla 11, greedy y con la hora del pedido fija. **Salidas idénticas** con y sin caché.
  - Sin alinear a `n_batch` o sin fijar la hora salían diferencias: en el primer caso, por cómo se trocea el prompt
    en bloques; en el segundo, porque cada pedido lleva la hora.
- **Tiempos** (mismos 42 casos): llamada 2,86 → 1,25 s; tarea 6,34 → 2,77 s.
- **Memoria:** el estado ocupa 118 MB de RAM y no añade VRAM (7 654 / 7 575 MiB cargado). Crearlo cuesta 1,8 s, una
  vez; restaurarlo, 26 ms de media (44 ms como máximo).
- **65 × 3 del banco** (`ejecutar.py qwen_q5 --round2 --cache-estado`, `datos/qwen9b_cache_2026-10-11`):
  - 62 / 65 / 62 = **189/195**, igual que sin caché;
  - primera acción 2,44 → 0,94 s (mediana); tarea 6,83 → 3,05 s; lectura del prompt 1,54 → 0,03 s por llamada;
  - 193 de 195 casos, idénticos a la corrida sin caché. Los 2 distintos (#56 s22 y s33) pasaban por
    `ver_pantalla`: la caché restauraba encima de la imagen ya evaluada.
  - Repetida con la caché corregida (`datos/qwen9b_cache2_2026-10-11`): 189/195. Las dos corridas con caché son
    idénticas entre sí. Los mismos 2 casos difieren de la corrida sin caché, pero **no por la caché**: esa corrida
    (10:23) es anterior a los frenos de `forzar` (0a3ea28, 10:49) y de `listar_controles` (e9a580d, 10:51).
    - #56 s33: `listar_controles` con id 1 daba error y ahora da la ventana del primer plano;
    - #56 s22: `forzar: true` ya no se ejecuta.
    - La corrección de d7e0ba2 (no restaurar si el estado ya tiene el prompt entero) no llegó a actuar: el banco no
      usa visión (`mmproj` vacío), pero protege la ruta de visión de producción.
  - Para una comparación estricta, con el mismo código, falta una 65 × 3 sin caché con el código de hoy.
- Gemma no se probó: ya reutiliza el prefijo.

## En producción (b056954): `cache_estados` en el perfil qwen9b

`cache_estados.py`, creada por `modelo.crear_llm` (una por modelo: se invalida al descargarlo o recargarlo en el
modo juego). `pedir_accion` le indica el prompt de sistema vigente. No restaura si el estado ya tiene el prompt
entero (visión). Gemma no la usa. Pruebas sin modelo: `probar_cache_estados.py` 13/13.

65 × 3 de producción con Qwen, hora fija (180d71d), `datos/swa_cache/qwen65x3{con,sin}Cache_A.json`:

| | Sin caché | Con caché |
|---|---:|---:|
| Completas (11 / 22 / 33) | 61 / 62 / 59 = 182 | 61 / 61 / 59 = 181 |
| Segundos por tarea (11 / 22 / 33) | 6,49 / 7,04 / 6,83 | 3,09 / 3,15 / 3,29 |
| VRAM cargado / pico | 7 649 / 7 878 MiB | 7 669 / 7 804 MiB |

- **Reproducibilidad:** la semilla 11 sin caché, repetida, da 65/65 casos idénticos (`qwen65x3sinCacheRep_A`).
- **Con frente a sin caché** (`comparar_corridas.py`): **192/195 casos idénticos**. Los 3 distintos (#49 s22,
  #58 s33 y #59 s22) se separan después de un `mouse`. `mouse_sim` usa `g4.planificar_mouse`, que mira la ventana
  **real** bajo el punto (`prohibida_en_punto`) y depende del escritorio de cada momento. No es la caché
  (backlog #31).
- **Ningún (c):** los dos intentos de cerrar sin pedirlo (#58 s22 y s33) los paró el freno.
- **Veredicto:** cumple el criterio del coordinador; `cache_estados` queda activa en `qwen9b`.

