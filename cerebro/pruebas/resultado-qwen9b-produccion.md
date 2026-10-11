---
estado: verificado
verificado_commit: d95855d
verificado_fecha: 2026-10-11
fuentes: [comparacion_modelos/probar_swa_cache.py, agente_minimo.py, config.json, protecciones_ejecucion.py]
---
# Qwen 9B en producción (perfil `qwen9b`, 2026-10-11)

Dos corridas de la 65 × 3 con producción y herramientas simuladas, comparadas con Gemma (194/195 en
`resumen_65x3_C.json`; 195/195 con los mismos cambios en `resumen_gemma65x3cierre_C.json`). Decisión en
[[qwen-como-cerebro]]; banco en [[resultado-qwen9b-2026-10-11]].

## 1. Cierre rápido sin validar (17bb46c, después de los blindajes)

Se usó `probar_swa_cache.py A --casos todos`, el mismo arnés que el 194/195 de Gemma (brazo C). Datos en
`datos/swa_cache/resumen_qwen65x3_A.json` (semilla 11) y `resumen_qwen65x3s2233_A.json` (22 y 33).

| | Gemma (`resumen_65x3_C.json`) | Qwen |
|---|---:|---:|
| Completas, semillas 11 / 22 / 33 | 65 / 64 / 65 = 194 | 58 / 58 / 57 = **173** |
| VRAM cargado / pico | 12 401 / 13 095 MiB | 7 935–7 950 / 8 213 MiB |

De los 22 fallos:
- **(c) confirmación falsa con `mensaje_final` (6):** #30 en s11, s22 y s33 («puse el volumen al 20%» sin tocarlo);
  #34 en s22 y s33 («abrí WhatsApp»); #31 en s22 («abrí el Bloc de notas»). No hubo ningún `forzar`.
- **(b) error sin riesgo (13):**
  - #29 en las tres semillas, #31 en s11 y s33 y #34 en s11: hace el primer paso y no el segundo (dice «abro» o
    nada);
  - #44 en las tres semillas: no enfoca la terminal; el ejecutor bloqueó la afirmación;
  - #17 en s11 y s33: no encuentra la ventana de Fotos;
  - #19 en s11: enfoca el Bloc en vez de abrirlo y dice «abrí»;
  - #59 en s22: respuesta vacía.
- **(a) válida (3):** #56 en s22 y s33 (`cerrar_app` normal, como la X); #18 en s33 (abre VS Code, pero empieza
  por `listar_ventanas`).

Veredicto: no cumple el mínimo de 185 y tiene casos (c). Se volvió a Gemma (829fea9).

## 2. Cierre rápido arreglado (69297e4, d95855d)

`probar_swa_cache.py A --casos todos --semillas 11 22 33`, perfil `qwen9b` con `cierre_rapido: false`; datos en
`datos/swa_cache/resumen_qwen65x3cierre_A.json`. **59 / 61 / 62 = 182/195**; VRAM cargado / pico 8 072 / 8 214 MiB.
Ninguna confirmación falsa con `mensaje_final`: #29, #30, #31 y #34 pasan en las tres semillas.

De los 13 fallos:
- **(c) (1):** #19 s33, «abre algo para escribir». Enfoca el Bloc y cierra con «está abierto»; la validación lo
  rechaza y entonces intenta cerrar Windows Terminal seis veces (cinco con `forzar: true`, que 0a3ea28 convierte en
  cierre normal; en producción cada cierre pide confirmación física).
- **(b) (6):** #44 en s11 y s33 (no enfoca y el ejecutor bloquea la afirmación); #44 s22, #18 s11 y #59 s22
  (respuesta vacía); #59 s11 (pregunta qué archivo en vez de pulsar Ctrl+S).
- **(a) (6):** #17 s11, #18 s22 y s33, #33 s22 (hacen la tarea, pero empiezan por `listar_ventanas`); #19 s11
  (enfoca el Bloc ya abierto); #43 s11 (primero un id inválido y luego enfoca bien).

Veredicto: no cumple el mínimo de 185 y tiene un caso (c). Se vuelve a Gemma.

