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

## Ideas del usuario para usar la memoria liberada (2026-10-11), con la opinión de Claude

- **Ampliar el contexto:** no hace falta ahora. El contexto cuesta poca VRAM (16K → 8K solo ahorró 81 MiB,
  [[no-reducir-whisper-ni-contexto]]), pero cada token más es más tiempo de lectura del prompt. Se amplía cuando un
  uso lo pida (memoria de experiencia, conversaciones largas).
- **MTP:** baja prioridad. Suma un modelo borrador (más VRAM). Acelera la generación, pero Cacao genera JSON corto:
  pesa más el primer token. No consta que llama-cpp-python lo exponga ni que funcione con gramática ([[mtp]]).
  Antes rinden más el camino rápido y el filtrado de herramientas. Se prueba en el banco, después de Qwen.
- **Qwen 9B + voz:** es lo que más sentido tiene. Gemma con `swa_full=false` (~9,8 GB) más Whisper (~1,3) más
  Qwen3-TTS (~5,25, perfil lean) no caben en 16 GB, y un modelo más pequeño sí. Pero el bloqueo de la voz es el
  motor: Qwen3-TTS solo fue rápido con vLLM-Omni en WSL (descartado por RAM). En Windows con PyTorch fue lento
  (RTF 3,84, [[qwen3-tts-vllm-omni]]). Hace falta buscar un motor de TTS para Windows.

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
