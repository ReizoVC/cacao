"""Ajustes comunes de la ronda 2; solo se aplican al benchmark aislado."""
import copy
import hashlib
import json

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
Si una app es ambigua, pregunta cuál usando finalizar con un mensaje no vacío.
Si algo está bloqueado o no autorizado, finaliza explicando la limitación sin rodear el bloqueo.'''

def adjust(ns, mode='combined'):
    # 0.3.36's schema converter permits raw U+0000..U+001F in JSON strings.
    # Patch only this process, before compiling each response schema. Never repair
    # the generated output or relax json.loads/jsonschema to credit invalid JSON.
    from llama_cpp import llama_grammar
    strict_char = r'[^"\\\x7F\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])'
    llama_grammar.PRIMITIVE_RULES['char'] = llama_grammar.BuiltinRule(strict_char, [])
    if mode in ('prompt','combined'):
        original=ns['prompt_sistema']
        def prompt(voz=False):
            lines=original(voz).splitlines()
            lines=[line for line in lines if not line.startswith(("Usa 'mensaje_final' solo", "Ejemplo para 'baja un poco"))]
            return '\n'.join(lines)+'\n\n'+RULES
        ns['prompt_sistema']=prompt
        ns['HERRAMIENTAS']=copy.deepcopy(ns['HERRAMIENTAS'])
        ns['HERRAMIENTAS']['finalizar']['descripcion'] += ' La respuesta debe estar en argumentos.mensaje, nunca en mensaje_final.'
        wheel=ns['HERRAMIENTAS']['mouse']['parametros']['properties']['cantidad']
        wheel.update(description='Solo para desplazar: entero entre -10 y 10. Cantidad NEGATIVA desplaza hacia ABAJO; POSITIVA hacia ARRIBA. Magnitud habitual 3 pasos; no son píxeles.',minimum=-10,maximum=10)
    if mode in ('schema','combined'):
        # Couple finalization to its required message. No expected task/tool is supplied.
        base=copy.deepcopy(ns['ESQUEMA_ACCION'])
        final=copy.deepcopy(base)
        final['properties']['herramienta']={'type':'string','enum':['finalizar']}
        final['properties'].pop('mensaje_final',None)
        final['properties']['argumentos']=copy.deepcopy(ns['HERRAMIENTAS']['finalizar']['parametros'])
        final['properties']['argumentos']['properties']['mensaje']['minLength']=1
        final['properties']['argumentos']['required']=sorted(set(final['properties']['argumentos'].get('required',[]))|{'mensaje'})
        final['additionalProperties']=False
        other=copy.deepcopy(base)
        other['properties']['herramienta']['enum']=[h for h in other['properties']['herramienta']['enum'] if h!='finalizar']
        other['properties'].pop('mensaje_final',None)
        other['additionalProperties']=False
        ns['ESQUEMA_ACCION']={'oneOf':[final,other]}
    return {'mode':mode,'json_control_characters_excluded':True,'strict_char_rule':strict_char,
            'prompt_sha256':hashlib.sha256(ns['prompt_sistema']().encode()).hexdigest(),
            'schema_sha256':hashlib.sha256(json.dumps(ns['ESQUEMA_ACCION'],sort_keys=True).encode()).hexdigest()}

def vision_contract(model, target):
    if model.startswith('gemma'):
        prompt=f'Localiza {target}. Devuelve un objeto JSON con box_2d: [y_min, x_min, y_max, x_max], la caja del botón. Coordenadas normalizadas de 0 a 1000 respecto a toda la imagen. Sin explicación.'
        key='box_2d'; n=4
    else:
        prompt=f'Localiza el centro de {target}. Devuelve un objeto JSON con point_2d: [x, y]. Coordenadas normalizadas de 0 a 1000 respecto a toda la imagen. Sin explicación.'
        key='point_2d'; n=2
    schema={'type':'object','properties':{key:{'type':'array','items':{'type':'integer','minimum':0,'maximum':1000},'minItems':n,'maxItems':n}},'required':[key],'additionalProperties':False}
    return prompt,schema

def pixel_point(model, obj, width, height):
    if model.startswith('gemma'):
        ymin,xmin,ymax,xmax=obj['box_2d']
        if ymin>ymax or xmin>xmax: raise ValueError('Caja invertida')
        x=(xmin+xmax)/2; y=(ymin+ymax)/2
    else:
        x,y=obj['point_2d']
    return {'x':x*width/1000,'y':y*height/1000}

def complete_round2(r):
    from criterios import complete
    if r['id']!=44: return complete(r)
    if r.get('error') or not r.get('json_schema_ok') or not r.get('respuesta') or 'Me pasé del límite' in r['respuesta']:
        return False
    # Correct a scorer false negative: PowerShell is the already-focused terminal fixture.
    for step in r.get('effects',[]):
        if step['herramienta']=='enfocar_ventana' and step['argumentos'].get('id_ventana')==9001 and step['resultado'].get('ok'):
            return True
        if step['herramienta']=='listar_ventanas' and isinstance(step['resultado'],list):
            if any(w.get('id_ventana')==9001 and w.get('enfocada') for w in step['resultado']):
                return True
    return False
