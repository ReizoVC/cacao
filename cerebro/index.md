# Cerebro de Cacao (para Claude Code)

Lee primero `CLAUDE.md` en la raíz. Después, solo las páginas que necesites. Estado y fecha de cada página: en su
frontmatter. Frescura: `python -I cerebro/frescura.py`.

## Arquitectura
- [[vision-general]]: piezas, flujo de un pedido y dónde se decide cada cosa
- [[agente-y-herramientas]]: catálogo, estructuras del ejecutor y cómo añadir una herramienta
- [[protecciones]]: sin evidencia no hay «hecho», dos alternativas, atajos estructurados, emergencia
- [[permisos-y-bloqueos]]: dónde se decide si se pregunta, niveles, bloqueos, confirmación física, modo sin confirmación
- [[voz]]: entrada, frenos, Whisper, Piper y confirmaciones en voz
- [[palabra-activacion]]: detector «Cacao» y escucha de seguimiento
- [[isla-websocket]]: protocolo con la isla (versión 2), protecciones y bandeja
- [[isla-codex]]: traspaso de la isla a Codex: rama, arnés, invariantes y datos personales
- [[modo-juego]]: detección de juego, descarga y recarga, guardia de la GPU
- [[memoria-y-wiki]]: memoria.db, wiki, consultar_memoria, reflexión, lint y sugerencias
- [[registro-habitos]]: registrador, privacidad y pausa
- [[entrada-fisica]]: Raw Input para la actividad y hooks para las confirmaciones

## Decisiones
- [[wsl-dominio-cuda]]: pila experimental en un solo WSL; no mezclar CUDA de Windows y WSL
- [[gemma-q4-por-ahora]]: Q4 solo en la pila experimental; producción sigue en Q5
- [[mtp]]: sin probar; no activarlo
- [[gemma-26b]]: no probado; no perseguirlo (sin verificar)
- [[wrench-ui-mate]]: descartados como cerebro
- [[qwen-como-cerebro]]: descartado (189/195, 7 acciones distintas)
- [[no-reducir-whisper-ni-contexto]]: 8K de contexto ahorra solo 81 MiB; recortar antes el TTS
- [[swa-full-false]]: −2,5 GiB de VRAM sin perder tareas; no aplicado
- [[qwen3-tts-vllm-omni]]: voz experimental; Piper sigue en producción
- [[motor-llama-cpp]]: 0.3.36 frente a b11429 y por qué migrar no es trivial
- [[use-mmap-false]]: mmap apagado por la RAM
- [[cierre-rapido-mensaje-final]]: diferencias entre producción y el banco de pruebas

## Modelos
- [[configuracion-vigente]]: config.json de producción explicado
- [[cifras-medidas]]: tabla de resultados con su archivo de origen
- [[criterio-de-cambio]]: criterio fijado y propuesta para cambiar de modelo o volver a Q5

## Pruebas
- [[suites]]: suites sin modelo, qué cubren y su baseline por commit
- [[suites-con-modelo]]: scripts que cargan la GPU o tocan el PC real
- [[evaluacion-65-frases]]: pruebas.json, cómo correrla en simulación y sus criterios
- [[comparacion-modelos]]: banco aislado ejecutar.py, rondas y evaluación a ciegas

## Estado
- [[backlog]]: pendientes verificados (hecho, pendiente o desconocido)
- [[riesgos]]: riesgos vigentes y alcance de cerebro/ frente a Cacao
- [[pendientes-presenciales]]: lo que necesita al usuario delante

## Operación
- [[arrancar-detener]]: lanzador, simulación, salir y emergencia
- [[mapa-archivos]]: archivos por rol
- [[mapa-datos]]: datos personales (no leer), datos de prueba y modelos
- [[compilar-isla]]: compilar la isla, respaldo de la v1 y cómo volver atrás (también el protocolo de Cacao)
- [[comandos]]: comandos útiles y trucos del entorno
- [[lecciones]]: fallos reales y su causa
- [[mantenimiento]]: chequeo de frescura, formato y privacidad
- [[log]]: registro cronológico de cambios del cerebro
- [[log-2026-10-10]]: entradas archivadas del 2026-10-10
