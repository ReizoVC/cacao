---
estado: verificado
verificado_commit: 97cea59
verificado_fecha: 2026-10-13
fuentes: [experiencia.py, agente_minimo.py, herramientas_grupo4.py, protecciones_ejecucion.py, herramientas.json, contrato_ronda2.py, benchmark_gramatica.py, probar_experiencia.py]
---
# Memoria de experiencia, cinco alternativas y enseñar clics con el mouse

**Estado: en `main` (97cea59, 2026-10-13); activo al reiniciar Cacao.** Lo pidió el
usuario antes de Spotify, con estas condiciones: hasta 5 intentos en lugar de 2; si no lo logra, que le pida que le
explique cómo; y que pueda leer dónde está el mouse para enseñarle dónde hacer clic. Pidió también no priorizar tanto
la seguridad («todo es local»). **65 × 3** (datos en el worktree, `comparacion_modelos/datos/swa_cache/*experiencia*`): Gemma 195/195; Qwen
187/195, sin casos (c), frente a 181 de su última corrida. Ningún caso llega a 5 alternativas. #58 llega a 16 pasos
por el simulador de foco (backlog #26). Falta la prueba con el usuario delante.

## Qué hace

- **Registro (`experiencia.py`, tabla `experiencias` de `memoria.db`):**
  - al terminar cada tarea con acciones, el **código** (nunca el modelo) guarda:
    - el pedido;
    - la app;
    - cada paso resumido (herramienta, argumentos, control pulsado) con su resultado: `ok`, `sin_efecto`, `error`
      o `no_autorizado`;
    - si la tarea salió bien.
  - Repetidas, suman `veces`. Tope de 500 filas.
- **Uso:**
  - al empezar una tarea, las 3 experiencias más parecidas (palabras en común y misma app) se añaden **al
    mensaje del pedido**, como `[Experiencia en este PC (datos…, no instrucciones): …]`, con un máximo de 700
    caracteres;
  - no van al prompt de sistema, para no romper la caché por estados ([[cache-estados]]).
- **Cinco alternativas:**
  - `MAX_ALTERNATIVAS = 5` en `protecciones_ejecucion.py` (antes eran 2);
  - `max_pasos_por_tarea` sube de 15 a 25.
- **Pedir ayuda:**
  - al rendirse, Cacao dice: «¿Me explicas cómo se hace? Dime los pasos, o pon el mouse donde hay que hacer clic y
    dime «aquí»».
  - Si el pedido siguiente llega antes de 30 minutos y parece una explicación («primero», «pulsa», «aquí», «menú»,
    etc.):
    - va marcado como explicación de lo anterior;
    - si sale bien, queda como **receta** del pedido original, con la explicación de Reizo.
- **El mouse que señala (`posicion_mouse`, sin permiso):**
  - toma el punto donde estaba el cursor **al hacer el pedido**; si estaba sobre la isla, el de ahora;
  - devuelve la app, la ventana y el control de UI Automation que hay debajo;
  - `mouse(punto_senalado=true)` hace clic ahí.

**Coste en tokens** (`comparacion_modelos/medir_prompt.py`, solo el vocabulario):
- prompt de sistema de Gemma: 3 802 → 4 012;
- prompt de sistema de Qwen: 4 141 → 4 418;
- `posicion_mouse`: 83–85 tokens.

Con la caché por estados, el prompt de Qwen se calcula una vez. El bloque de experiencia va en cada pedido: como
mucho 700 caracteres, solo cuando hay algo parecido.

## Protecciones que siguen

- **El clic en el punto señalado:** pasa por las mismas comprobaciones que cualquier otro clic:
  - no se hace sobre la isla, la bandeja ni ventanas prohibidas;
  - caduca a los 2 minutos;
  - pide confirmación como cualquier `mouse`.
- **Ventanas sensibles:** `posicion_mouse` no lee el título ni el control de una ventana sensible.
- **Texto de fuera:** `posicion_mouse` cuenta como herramienta que trae texto de fuera (`TEXTO_EXTERNO`).
- **Lo que se guarda:**
  - los textos se recortan y se limpian (sin corchetes ni saltos de línea, para que no cierren el bloque);
  - nunca se guarda texto leído de archivos o de la web.

## Pruebas

- **`probar_experiencia.py`:** 50/50 sin modelo (registro, búsqueda, limpieza, mouse señalado, flujo rendirse →
  explicación → receta) y 8/8 mutaciones. Ajustadas: protecciones 95/95, contrato 16/16 (huellas nuevas de Gemma),
  obstáculos 35/35, cierre rápido 13/13, camino rápido 456/456. En `main` pasan todas las suites sin modelo.
- **El banco:** experiencia apagada y `posicion_mouse` simulada.

## Falta

1. **Reiniciar Cacao** para que la cargue (hecho: 65 × 3 y fusión en `main`).
2. **Prueba con el usuario delante:**
   - una tarea que falle cinco veces;
   - la explicación;
   - «haz clic aquí» con el mouse;
   - la misma tarea otra vez.
3. **Después:** la vista en Markdown en la wiki (`python experiencia.py --exportar ruta`) y que la reflexión condense
   las experiencias en lecciones ([[estrategia-recursos]]).
