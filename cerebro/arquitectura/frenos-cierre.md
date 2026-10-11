---
estado: verificado
verificado_commit: 98c763e
verificado_fecha: 2026-10-11
fuentes: [protecciones_ejecucion.py, agente_minimo.py, herramientas_grupo4.py, probar_protecciones_ejecucion.py, probar_modo_directo.py, probar_grupo4.py, pruebas.json]
---
# Frenos de cerrar_app y listar_controles

Nacieron de las pruebas de Qwen 9B ([[qwen-como-cerebro]]) y protegen a los dos modelos. Son parte de las
protecciones del ejecutor ([[protecciones]]).

## 1. Cierre forzado solo si se pide (0a3ea28)

`quitar_forzar_no_pedido()`, al principio de `ejecutar()`: si el modelo manda `cerrar_app` con `forzar: true` y el
pedido de la tarea no lo pide (`pide_forzar`: «forzar», «a la fuerza», «no responde», «colgado», «congelado»,
«trabado», «bloqueado», «mata el proceso»…, sin tildes ni mayúsculas), se hace un cierre normal. El registro muestra
`[forzar]` y el resultado lleva `nota_forzar` para el modelo. La confirmación física del cierre forzado no cambia.
Origen: Qwen 9B, #56 s22 ([[resultado-qwen9b-2026-10-11]]). Límite: una respuesta «sí» a «¿lo fuerzo?» en una tarea
nueva no basta; hay que decir la palabra.

## 2. listar_controles sin ventana válida (e9a580d)

Con `id_ventana` ausente, 0 o de una ventana que ya no existe, `listar_controles` usa la ventana al frente
(`ventana_para_listar`) y lo dice en `nota`. Las ventanas sensibles y la isla siguen bloqueadas. `mouse` no cambia.

## 3. cerrar_app solo si el pedido pide cerrar (98c763e)

`cierre_no_pedido()`, al principio de `ejecutar()` y antes de `forzar`: si el pedido no expresa intención de cerrar
(`pide_cerrar`, sin tildes: «cierra», «cerrar», «ciérrame», «sal de», «salir de», «quita», «termina», «mata», «apaga
la app»…), no se cierra ni se pregunta. El modelo recibe «El usuario no pidió cerrar ninguna app; no cierres nada.
Si no puedes hacer lo pedido, explícalo y pregunta.» (`ok: false`, sin `bloqueado`, para que pueda explicarlo) y el
registro muestra `[cerrar]`. Las 4 frases de las 65 + 30 que esperan `cerrar_app` (#51, #52, #119, #120) pasan; «quita
el silencio» (#5) también pasa el freno, aunque no cierra nada.

