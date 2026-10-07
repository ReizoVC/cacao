"""Comprobaciones de argumentos y efectos simulados, además del marcador histórico.

No mide el éxito sobre Windows real. Casos ambiguos conservan el criterio del set.
"""
import unicodedata
import json
from pathlib import Path
CASES = {p['id']:p for p in json.loads((Path(__file__).resolve().parents[1]/'pruebas.json').read_text(encoding='utf-8'))['pruebas']}

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD',str(s).lower()) if not unicodedata.combining(c))

def complete(r):
    if r.get('error') or not r.get('json_schema_ok') or not r.get('respuesta') or 'Me pasé del límite' in r['respuesta']:
        return False
    steps=r.get('effects',[])
    def successful(name):
        return [s for s in steps if s['herramienta']==name and
                not (isinstance(s['resultado'],dict) and s['resultado'].get('ok') is False)]
    def opened(name):
        return any(norm(s['resultado'].get('app_abierta',''))==norm(name) for s in successful('abrir_app'))
    def action(name, **fields):
        return any(all(s['argumentos'].get(k)==v for k,v in fields.items()) for s in successful(name))
    def volume(value=None,mute=None):
        ss=successful('volumen')
        return bool(ss) and (value is None or ss[-1]['resultado'].get('volumen_actual')==value) and (mute is None or ss[-1]['resultado'].get('silenciado')==mute)
    def path_action(name,key,fragment):
        return any(norm(fragment) in norm(s['argumentos'].get(key,'')).replace('/','\\') for s in successful(name))
    i=r['id']
    if i in (16,17,18,19,20):
        # Ambiguous requests may legitimately finish by asking which app to use.
        # A recovered lookup error is not itself an incomplete task.
        return any(s['herramienta'] in ('abrir_app','listar_apps','consultar_memoria','listar_ventanas') for s in steps) or r['herramientas']==['finalizar']
    if i in (1,2,3,7): return volume({1:40,2:60,3:30,7:100}[i])
    if i in (4,5): return volume(mute=i==4)
    if i==6: return action('volumen',accion='consultar')
    if i in (8,9,10,11,12): return opened({8:'Spotify',9:'Calculadora',10:'Bloc de notas',11:'Google Chrome',12:'Discord'}[i])
    if i in (13,15): return any(s['resultado'].get('volumen_actual',100)<50 for s in successful('volumen'))
    if i==29: return volume(60) and opened('Spotify')
    if i==30: return volume(20) and opened('Calculadora')
    if i==31: return volume(mute=True) and opened('Bloc de notas')
    if i==33: return opened('Steam')
    if i==34: return volume(40) and opened('WhatsApp')
    if i==40: return '180' in r['respuesta']
    if i==43: return action('enfocar_ventana',id_ventana=9002)
    if i==44: return bool(successful('listar_ventanas')) and (action('enfocar_ventana',id_ventana=9001) or 'terminal' in norm(r['respuesta']))
    if i==47: return action('listar_carpeta',patron='*.md')
    if i==48: return path_action('leer_archivo','ruta','inventarios\\help.md')
    if i==50: return not successful('leer_archivo')
    if i in (51,52):
        ss=successful('cerrar_app')
        return any(norm(s['resultado'].get('proceso',''))=='notepad.exe' and bool(s['argumentos'].get('forzar'))==(i==52) for s in ss)
    if i==53: return path_action('mover_archivo','origen','spark.txt') and any('document' in norm(s['argumentos'].get('destino','')) for s in successful('mover_archivo'))
    if i==54: return path_action('mover_archivo','origen','spark.txt') and path_action('mover_archivo','destino','spark_notas.txt')
    if i==55: return not successful('mover_archivo')
    if i==56: return action('mouse',accion='clic',control='Cerrar')
    if i==57: return any(s['argumentos'].get('accion')=='desplazar' and s['argumentos'].get('cantidad',0)<0 for s in successful('mouse'))
    if i==58: return action('enfocar_ventana',id_ventana=9002) and any(norm(s['argumentos'].get('texto','')).strip()=='hola mundo' for s in successful('teclado'))
    if i==59: return any(s['argumentos'].get('accion')=='atajo' and set(map(norm,s['argumentos'].get('teclas',[]))) in ({'ctrl','s'},{'ctrl','g'},{'control','s'},{'control','g'}) for s in successful('teclado'))
    if i==60: return any('enter' in list(map(norm,s['argumentos'].get('teclas',[]))) for s in successful('teclado'))
    if i in (62,63,64): return action('sugerencias',accion={62:'bloquear',63:'listar',64:'desbloquear'}[i])
    if i==65: return action('registro_habitos',accion='pausar')
    expected=CASES[i]['esperado']
    expected=[expected] if isinstance(expected,str) else expected
    evidence=any(successful(h) for h in expected if h!='finalizar') or ('finalizar' in expected and 'finalizar' in r['herramientas'])
    return evidence and all(successful(h) for h in CASES[i].get('requiere',[]))
