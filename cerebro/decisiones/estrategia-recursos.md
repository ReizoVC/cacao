---
estado: verificado
verificado_commit: 3575862
verificado_fecha: 2026-10-11
fuentes: [obstaculos.py]
---
# Estrategia: herramientas antes que modelo, con el mínimo de recursos (usuario, 2026-10-11)

Mientras no se actualice el equipo (16 GB de RAM y una sola GPU), el usuario prioriza:
1. **Ahorrar memoria.** Por eso se prueba Qwen 9B: si basta, deja sitio a la voz personalizada (Qwen3-TTS).
   Ante dos opciones parecidas, gana la que ocupa menos (por ejemplo, `swa_full=false` vaciando la memoria entre
   tareas, si su coste en tiempo es aceptable: [[swa-full-false]]).
2. **El modelo solo decide; el código hace.** Herramientas más capaces: adaptadores por app, camino rápido, filtrado
   de herramientas por pedido. Un prompt más corto es menos contexto, menos memoria y menos errores.
3. **Memoria de experiencia** en el cerebro de Cacao (Obsidian): ver abajo.

## Memoria de experiencia (idea del usuario; propuesta de diseño, sin código)

Cada vez que un resultado no es el deseado, Cacao anota qué hizo, qué resultado dio y en qué app. Con eso, ante un
problema parecido sabe qué hacer y qué no. Y un «error» que produjo otro efecto puede ser la solución de un
problema futuro.

**Propuesta de Claude:**
- Se separan dos registros:
  - **qué consigue cada acción:** acción en la app → efecto observado, sea éxito o fallo;
  - **qué se buscaba:** intención → éxito o fallo.

  Así un fallo para un objetivo queda como receta para otro.
- **Lo escribe el código, nunca el modelo:** con la verificación de efectos, y sin guardar nada si en la tarea entró
  texto de fuera (web, archivos), como ya hace `obstaculos.py`, que es el germen.
- **El dato y su vista:** el dato estructurado va en SQLite, que el código consulta rápido. El cerebro de Obsidian
  recibe una vista en Markdown que el usuario puede leer y corregir. La reflexión programada condensa experiencias
  en lecciones.
- **Antes de planificar:** el código busca por app e intención y mete solo unas pocas líneas en el prompt, con un
  tope de tokens.

El usuario dijo que había un diseño aprobado: no está en el repositorio. Pedirlo antes de escribir el diseño final.
