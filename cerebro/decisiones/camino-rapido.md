---
estado: sin verificar
verificado_commit: ef06fb8
verificado_fecha: 2026-10-11
fuentes: [agente_minimo.py, protecciones_ejecucion.py, pruebas.json, comparacion_modelos/pruebas_nuevas_30.json, comparacion_modelos/probar_swa_cache.py]
---
# Camino rápido: pedidos simples sin el modelo

**Estado: propuesto (2026-10-11), sin código.** Sigue [[estrategia-recursos]]: el modelo decide; el código hace.

## Qué pedidos entran (lista blanca, fase 1)

Solo pedidos de **una herramienta**, con argumentos que salen del texto sin interpretar:

| Patrón (frase entera, sin tildes) | Herramienta y argumentos | Frases del banco |
|---|---|---|
| «sube / baja el volumen [un poco]» | `volumen` subir / bajar 10 | #1, #2 |
| «pon el volumen al N» (N con dígitos, 0–100), «… al máximo» | `volumen` fijar N / 100 | #3, #7 |
| «silencia el sonido / el volumen / el equipo» | `volumen` silenciar | #4 |
| «quita el silencio», «(vuelve a) activa(r) el audio / el sonido» | `volumen` activar | #5, #103 |
| «¿a cuánto está el volumen?» | `volumen` consultar | #6 |
| «abre / inicia (la aplicación de) X», X un nombre concreto | `abrir_app` X | #8–12, #104 |

**14 de las 95 frases** (#1–12, #103 y #104). Dos ampliaciones posibles, para decidir:
- `registro_habitos` pausar / reanudar con su frase literal (#65, #130): **16**;
- números en palabras («al cuarenta y cinco por ciento», #101): **17**.

No entran (siempre al modelo): varios pasos, paráfrasis, nombres genéricos («el navegador»), teclado, mouse,
cerrar, mover, conversación, ventanas, archivos y web. Detalle en [[frases-simples]].

## Cómo se reconoce

- `camino_rapido.py`: expresiones que **cubren la frase entera** (`fullmatch`), sin tildes, mayúsculas, «Cacao,»
  inicial, «por favor» ni puntuación final. Una palabra de más no coincide. **Ante la duda, al modelo.**
- Solo mira el pedido del usuario (isla o voz), al empezar la tarea. Nunca texto externo (resultados, archivos, web,
  pantalla).

## Cómo pasa por las mismas protecciones

- Se engancha al principio de `atender()`, después de comprobar `emergencia.detenido()` y antes de llamar al modelo.
- Ejecuta con **el mismo `ejecutar()`**: permisos, planificadores, modo sin confirmación, confirmación física (por
  ejemplo, abrir una consola), frenos de [[frenos-cierre]] y `emergencia.comprobar()`.
- **Modo juego:** se comporta igual que hoy. Con el modelo descargado, el pedido sigue el camino actual; si se
  permite el camino rápido en pausa (solo el volumen, sin GPU), lo decide el usuario.
- Al historial va como si el modelo la hubiera elegido (acción con `"pensamiento": "camino rápido"`, resultado y
  `finalizar`): el contexto queda coherente y la caché de Gemma no cambia.

## Qué responde

- Un texto fijo con el resultado **verificado** (`resultado_verificado`). Por ejemplo, «Listo, puse el volumen al
  {volumen_actual}%», «Abrí {app_abierta}» o «El volumen está al {volumen_actual}%».
- Si el resultado no está verificado (error, app ambigua o rechazo), la tarea **pasa al modelo** con lo ocurrido ya
  en el historial. Un rechazo del usuario o un bloqueo termina como hoy.

**Registro:** una línea `[camino rápido] <herramienta>` en `registro_cacao.log`, sin el texto del pedido.

## Riesgos

- **Falso positivo** (un pedido complejo tomado por simple): frase entera, lista blanca corta y frases trampa en la
  suite («sube el volumen y abre spotify», «no abras spotify», «¿abro spotify?», «abre spotify en el portátil»).
- **Transcripción errónea** («al 13» por «al 30»): el mismo riesgo que con el modelo; el volumen es reversible.
- **Texto externo:** no entra por este camino.

## Ganancia esperada

Con el modelo, esas frases tardan de media **1,82 s con Gemma** (1,1 llamadas) y **6,09 s con Qwen** (2,36 llamadas).
Datos de `datos/swa_cache/gemma65x3cierre_C.json` y `qwen65x3contrato_A.json`, frases #1–12 y #65. Con el camino
rápido, ese tiempo pasa a ser casi cero; queda el de la herramienta. Además, Qwen falló 3 de esos 39 casos
(enfocó en vez de abrir), y aquí no fallaría. No cambia la memoria: el modelo sigue cargado.

## Cómo se probaría

- **Sin modelo:** `probar_camino_rapido.py` (las 14 dan la acción esperada; las trampas y las otras 81 van al
  modelo; rechazo, consola con confirmación y atajo de emergencia).
- **Con modelo:** 65 × 3 con `gemma` y con `qwen9b`. Criterio:
  - ninguna frase baja respecto de su última 65 × 3;
  - las 14 se completan en las tres semillas;
  - ninguna frase de fuera de la lista entra por el camino rápido (el registro lo dice);
  - 0 casos (c).

**Archivos:** `camino_rapido.py` (nuevo), `atender()`, una clave `camino_rapido` por perfil y
`probar_camino_rapido.py`. **No cambia el prompt ni el esquema**, pero sí el comportamiento: 65 × 3 de los dos.
