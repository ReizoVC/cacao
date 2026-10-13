---
estado: sin verificar
verificado_commit: f83dd1a
verificado_fecha: 2026-10-13
fuentes: [agente_minimo.py, contrato_ronda2.py, comparacion_modelos/medir_prompt.py, comparacion_modelos/simular_filtrado.py, comparacion_modelos/probar_swa_cache.py]
---
# Filtrado de herramientas por pedido

**Estado: aparcado por decisión del usuario (2026-10-11)** hasta ver la caché por estados de Qwen. Primeros datos
([[cache-estados]]): con la caché, Qwen lee el prompt en ≈ 0,03 s por llamada en vez de 1,54 s, así que
el filtrado le ahorraría poco tiempo. Sigue [[estrategia-recursos]].

## Datos

En [[prompt-y-cache]]. Resumen: las herramientas son el 75–80 % del prompt (≈ 3 000 de 3 800–4 100 tokens). Gemma
reutiliza ≈ 3 965 tokens por llamada. **Qwen no reutiliza nada** y recalcula ≈ 4 300 tokens en cada llamada, a
1,54 s (≈ 0,35 ms/token). Perder el prefijo le cuesta a Gemma ≈ 1,3 s por llamada.

## Elección del subconjunto

- **Núcleo fijo, siempre presente:** finalizar, volumen, abrir_app, listar_apps, listar_ventanas, enfocar_ventana y
  consultar_memoria. Son 1 594 tokens de prompt en Gemma y 1 873 en Qwen.
- **Grupos por palabras clave del pedido** (solo del usuario):
  - interfaz (mouse, teclado, ver_pantalla, listar_controles, cerrar_app): ≈ 1 100;
  - archivos: ≈ 440;
  - memoria y hábitos: ≈ 500;
  - web: 86;
  - PowerShell: ≈ 105.
- **Ante la duda, todos** (como hoy).

Simulación sobre las 95 frases (`simular_filtrado.py`):
- 53 quedan solo con el núcleo, y ninguna se queda sin su herramienta;
- media: 1 925 tokens en Gemma y 2 213 en Qwen (hoy, 3 802 y 4 141).

Las palabras clave se ajustaron sobre esas mismas frases (#62 «sugieras» falló al principio), así que en el uso real
fallarán más. Por eso el respaldo es obligatorio.

**Si falta una herramienta:**
- el esquema mantiene **el enum completo** (no cambia);
- si el modelo elige una herramienta de un grupo ausente, el ejecutor **no la ejecuta**: añade su grupo y repite el
  paso con la descripción ya presente;
- un `finalizar` con `exito: false` en la primera llamada también repite el pedido con todas.

## Variantes y la caché

| Variante | Qwen (sin caché hoy) | Gemma (reutiliza ≈ 3 965) |
|---|---|---|
| A. Subconjunto libre dentro del sistema | −1 900 tokens por llamada ≈ −0,67 s; ≈ −2 s por tarea (3 llamadas) | Al cambiar el conjunto entre tareas recalcula desde la primera herramienta distinta, más el historial: hasta +1,2 s en la primera llamada. Pierde |
| B. 3–4 conjuntos fijos completos | Igual que A, algo menos de ahorro | Reutiliza si se repite el conjunto; al cambiar, como A |
| **C. Prefijo fijo (reglas + núcleo) y grupos en orden fijo al final del sistema** | Igual que A | Siempre reutiliza ≈ 1 600; al cambiar de grupos recalcula el bloque (0–2 200) y el historial: 0 s si no hay grupos o se repiten, como mucho ≈ +1,2 s |
| D. Sistema fijo y grupos en el mensaje del pedido | Igual que A | Conserva toda la caché; añade el bloque en cada tarea (≈ +0,55 s con interfaz). El historial crece con descripciones: hay que compactarlo |

## Recomendación

1. **Primero, sin filtrar: devolverle a Qwen la caché del prompt de sistema.** Guardar el estado tras el prompt de
   sistema (`save_state`/`load_state` de llama-cpp-python) y restaurarlo en cada llamada. Si funciona con su memoria
   híbrida, ahorra ≈ 4 000 tokens por llamada (≈ 1,4 s, ≈ 4 s por tarea), más que el filtrado, y **sin cambiar el
   prompt**. Hecho: activo en `qwen9b` ([[cache-estados]]).
2. **Después, la variante C** con grupos fijos: es la única que no empeora a Gemma en el caso típico y le da a Qwen
   casi todo el ahorro de A. La D conserva mejor la caché de Gemma, pero pone descripciones de herramientas en el
   mensaje del usuario, un cambio de formato más arriesgado para los dos modelos.

**Memoria:** no cambia la VRAM (`n_ctx` fijo); ahorra tiempo y deja más contexto para el historial.

## Prueba y archivos

- **Cambia el prompt** (no el esquema), así que exige la 65 × 3 con `gemma` y con `qwen9b`. Criterio:
  - ≥ el último resultado de cada modelo (Gemma 195, Qwen 182);
  - 0 casos (c);
  - 0 frases sin su herramienta en el registro (respaldos contados aparte);
  - la latencia media por tarea baja en Qwen y no sube más de 0,3 s en Gemma.
- **Sin modelo:** las 95 frases y frases trampa para los grupos.
- **Archivos:** `agente_minimo.py` (prompt por partes, grupos y respaldo), `contrato_ronda2.py`,
  `benchmark_gramatica.py` y una clave `filtrado` por perfil. El paso 1: `modelo.py` o `pedir_accion`, medido con
  `probar_swa_cache.py`.
