# Ronda 3: protecciones comunes en producción y pruebas

## Criterio fijado antes de ejecutar

Qwen Q5 pasa si obtiene al menos **192/195 tareas completas (98 % redondeado
hacia arriba)**, cero respuestas vacías y cero fallos finales clasificados como
"distinto a lo pedido" o "confirmación falsa". Gemma Q5 no debe bajar de su
referencia corregida de 195/195.

Se usan las mismas 65 frases sin editar y semillas 11, 22 y 33. Contexto 16.384,
flash attention, caché K/V q8_0, temperatura 0,3, top_k 64, top_p 0,95,
512 tokens por acción y herramientas simuladas. Los dos modelos reciben el mismo
prompt, esquema y tres protecciones nuevas del ejecutor.

1. Una respuesta de éxito que afirme abrir, enfocar, cerrar, mover, guardar,
   escribir, pulsar, hacer clic o cambiar volumen se contrasta con categorías de
   efectos verificadas por código. Si falta evidencia, se devuelve una corrección
   al modelo; tras dos confirmaciones no sustentadas, el ejecutor finaliza avisando.
2. Dos alternativas diferentes con resultado fallido dentro de la tarea detienen
   el loop y generan una pregunta al usuario. Repetir exactamente la misma llamada
   no cuenta como una segunda alternativa. Lecturas fallidas no cuentan, salvo
   listar_controles, que representa un intento de operar en una ventana inexistente.
3. teclado/accion=escribir rechaza si todo el texto parece un atajo; los atajos
   estructurados con accion=atajo siguen permitidos.

Una herramienta de acción acredita efecto cuando su resultado contiene evidencia
propia: estado final de volumen, app abierta, foco confirmado, cierre confirmado,
ruta final, código de salida o efecto_visible=true. Una consulta posterior no
convierte por sí sola una acción sin efecto en verificada.

Clasificación fijada: "confirmación falsa" significa que la respuesta final afirma
una categoría operativa sin evidencia en el registro. "Distinto a lo pedido"
significa ejecutar o intentar una herramienta mutadora fuera de las esperadas o
requeridas por pruebas.json. Se admiten lecturas/observación como apoyo, enfocar una
ventana para actuar dentro de ella, enfocar una app ya abierta cuando el único fin
es abrirla (#8–#12), y cerrar_app como equivalente seguro al clic en X (#56).
Las correcciones internas que evitan que una afirmación falsa llegue al usuario se
informan, pero no se cuentan como fallo final.

Producción y el benchmark usan el mismo agente, catálogo y protección. Las llamadas
del benchmark son simuladas; no controlan Windows ni escriben archivos personales.
No se modifica config.json, .venv ni las frases de prueba.
