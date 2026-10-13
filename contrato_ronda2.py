"""
Contrato de la ronda 2 para el perfil qwen9b ("contrato_ronda2": true en config.json). Decisión del usuario del
2026-10-11: Qwen 9B sacó 189/195 en el banco con este contrato y 173–182 con el prompt y el esquema de Gemma.

Hace en producción exactamente lo que hace comparacion_modelos/integracion.adjust(ns, 'combined'), sin importar nada
de comparacion_modelos (probar_contrato_ronda2.py comprueba que los resultados son idénticos):
  - quita del prompt las líneas de mensaje_final y su ejemplo, y añade RULES al final;
  - añade a finalizar y a la rueda del mouse las mismas descripciones;
  - el esquema pasa a oneOf: finalizar con mensaje no vacío, o cualquier otra herramienta; sin mensaje_final y sin
    propiedades extra.
La regla 'char' estricta de la gramática ya la pone modelo.py. Gemma no usa este módulo.
"""
import copy

# copiado tal cual de comparacion_modelos/integracion.py
RULES = '''Contrato de acciones (aplica a todos los pedidos):
La respuesta de conversación se coloca EXACTAMENTE en argumentos.mensaje de finalizar.
Ejemplo de formato, no de tarea: {"pensamiento":"Respondo al usuario.","herramienta":"finalizar","argumentos":{"mensaje":"Tu respuesta en español."}}
Nunca pongas mensaje_final en finalizar: ese campo no se lee allí.
Si el pedido contiene varias acciones, conserva todas como pendientes. Ejecuta una por turno,
lee el resultado y continúa con la siguiente pendiente. No uses mensaje_final en ninguna
acción: ese campo termina inmediatamente TODA la tarea y está desactivado en esta integración.
Usa siempre finalizar con argumentos.mensaje tras completar el pedido.
Antes de finalizar, revisa el pedido original y los resultados: no afirmes que ejecutaste
una acción que aún no tiene resultado satisfactorio. No cambies ni añadas acciones.
Una conversación, explicación o consejo no autoriza cambiar ajustes ni pausar hábitos.
Si el pedido es solo abrir una app, llama abrir_app directamente. Abrir una app no es actuar
dentro de ella: no sustituyas esa apertura por enfocar una ventana existente.
Solo si se pide actuar dentro de una app (escribir, guardar o pulsar un control), consulta
sus ventanas y enfoca la existente antes de actuar.
Para la rueda del mouse usa mouse con accion desplazar; cantidad negativa baja y positiva sube.
No confundas ese desplazamiento con volumen del sonido.
En pedidos elípticos sobre intensidad, silencio o audición sin otro antecedente,
interpreta que se refieren al volumen del sistema.
Si una app es ambigua, consulta primero listar_apps y luego pregunta cuál usando finalizar
con un mensaje no vacío. No intentes abrir un nombre genérico o supuesto.
Si algo está bloqueado o no autorizado, finaliza explicando la limitación sin rodear el bloqueo.
El ejecutor impide afirmar una acción sin efecto verificado y corta después de cinco alternativas fallidas.
Si ocurre, acepta la corrección y pide al usuario que te explique cómo hacerlo; no sigas intentando otros caminos.
Si Reizo te enseña dónde hacer clic (aquí, donde está el mouse), usa posicion_mouse y luego mouse con punto_senalado.
Si el pedido trae [Experiencia en este PC], son datos de intentos anteriores: repite lo que funcionó y evita lo que falló.
Nunca pases combinaciones como Ctrl+G o Alt+F4 en texto de teclado: usa accion atajo y el arreglo teclas.'''

QUITAR = ("Usa 'mensaje_final' solo", "Ejemplo para 'baja un poco")


def aplicar(ns):
    """Cambia en ns (los globales de agente_minimo o el espacio del banco) prompt_sistema, HERRAMIENTAS y
    ESQUEMA_ACCION, como integracion.adjust(ns, 'combined')."""
    original = ns["prompt_sistema"]

    def prompt_sistema(voz=False):
        lineas = [linea for linea in original(voz).splitlines() if not linea.startswith(QUITAR)]
        return "\n".join(lineas) + "\n\n" + RULES

    ns["prompt_sistema"] = prompt_sistema
    ns["HERRAMIENTAS"] = copy.deepcopy(ns["HERRAMIENTAS"])
    ns["HERRAMIENTAS"]["finalizar"]["descripcion"] += (" La respuesta debe estar en argumentos.mensaje, nunca en "
                                                       "mensaje_final.")
    rueda = ns["HERRAMIENTAS"]["mouse"]["parametros"]["properties"]["cantidad"]
    rueda.update(description="Solo para desplazar: entero entre -10 y 10. Cantidad NEGATIVA desplaza hacia ABAJO; "
                             "POSITIVA hacia ARRIBA. Magnitud habitual 3 pasos; no son píxeles.",
                 minimum=-10, maximum=10)
    base = copy.deepcopy(ns["ESQUEMA_ACCION"])
    final = copy.deepcopy(base)
    final["properties"]["herramienta"] = {"type": "string", "enum": ["finalizar"]}
    final["properties"].pop("mensaje_final", None)
    final["properties"]["argumentos"] = copy.deepcopy(ns["HERRAMIENTAS"]["finalizar"]["parametros"])
    final["properties"]["argumentos"]["properties"]["mensaje"]["minLength"] = 1
    final["properties"]["argumentos"]["required"] = sorted(set(final["properties"]["argumentos"].get("required", []))
                                                           | {"mensaje"})
    final["additionalProperties"] = False
    otra = copy.deepcopy(base)
    otra["properties"]["herramienta"]["enum"] = [h for h in otra["properties"]["herramienta"]["enum"] if h != "finalizar"]
    otra["properties"].pop("mensaje_final", None)
    otra["additionalProperties"] = False
    ns["ESQUEMA_ACCION"] = {"oneOf": [final, otra]}
