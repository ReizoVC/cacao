"""Comparación aislada de Cacao. Nunca importa el arranque del agente de producción."""
import argparse
import ast
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'comparacion_modelos' / 'datos'
MODELS = {
    'gemma_q5': ROOT / 'modelos/gemma-4-12b-it-Q5_K_M.gguf',
    'gemma_q4': Path(r'D:\Cacao\ModelosComparacion\gemma-4-12b-it-UD-Q4_K_XL.gguf'),
    'qwen_q4': ROOT / 'modelos/comparacion/Qwen3.5-9B-UD-Q4_K_XL.gguf',
    'qwen_q5': ROOT / 'modelos/comparacion_local/Qwen3.5-9B-UD-Q5_K_XL.gguf',  # copia en C: (SSD); original en D:
    'qwen_wrench_q4': ROOT / 'modelos/comparacion/Wrench-9B-Q4_K_M.gguf',
}
QUESTIONS = [
    'Hola Cacao, hoy estoy cansado. Conversemos un rato sin abrir ninguna app.',
    'Explícame qué es una API con un ejemplo de la vida diaria, en tres frases.',
    '¿En qué se diferencian la memoria RAM y el espacio del disco? Explícalo simple.',
    '¿Por qué un modelo de IA puede dar una respuesta equivocada con tanta seguridad?',
    'Tengo que estudiar pero me distraigo. Dame un primer paso pequeño que pueda hacer ahora.',
    'Explícame qué significa cuantizar un modelo de IA sin usar fórmulas.',
    'Si tengo 15 cajas con 12 lápices cada una y regalo 35 lápices, ¿cuántos me quedan? Explica breve.',
    '¿Qué diferencia hay entre guardar un archivo y hacer una copia de seguridad?',
    'No entendí qué es una base de datos. Explícamelo como si nunca hubiera programado.',
    'Escribe un mensaje breve y amable para decirle a un amigo que hoy no podré jugar.',
]

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

class GPU:
    def __init__(self):
        self.samples = []
        self.stop = threading.Event()
    def read(self):
        s = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.total,memory.used,memory.free,utilization.gpu',
                                     '--format=csv,noheader,nounits'], text=True, creationflags=0x08000000)
        total, used, free, util = map(int, s.strip().split(','))
        return dict(t=time.time(), total=total, used=used, free=free, util=util)
    def loop(self):
        while not self.stop.is_set():
            try:
                self.samples.append(self.read())
            except Exception as exc:
                self.error = str(exc)
            self.stop.wait(.25)
    def start(self):
        self.samples.append(self.read())
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
    def close(self):
        self.stop.set()
        self.thread.join(5)

def prepare(model, isolated_round=False, round_name='ronda2', swa_full=None):
    runtime = ROOT / '.comparacion-runtime' / (model+'_'+round_name if isolated_round else model)
    runtime.mkdir(parents=True, exist_ok=True)
    # Copies only code/configuration, never personal databases or the production vault.
    for source in ROOT.glob('*.py'):
        shutil.copy2(source, runtime / source.name)
    for name in ('herramientas.json', 'pruebas.json', 'wiki_esquema.json', 'apps_categorias.json'):
        shutil.copy2(ROOT / name, runtime / name)
    config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    # los perfiles de producción (modelo_activo) no cuentan aquí: el modelo lo elige el banco
    for key in ('modelo_activo', 'perfiles', 'swa_full', 'sin_pensamiento'):
        config.pop(key, None)
    config.update(modelo=str(MODELS[model]), mmproj=None, n_ctx=16384, flash_attn=True,
                  type_k='q8_0', type_v='q8_0', use_mmap=False, modo_gramatica='topk')
    if swa_full is not None:
        config['swa_full'] = swa_full
    dump(runtime / 'config.json', config)
    dump(runtime / 'datos_locales.json', {})
    # No hotkey conflict with Cacao; cancellation is checked by the runner each token.
    src = (runtime / 'benchmark_gramatica.py').read_text(encoding='utf-8')
    src = src.replace('emergencia.iniciar()', '# isolated benchmark: no global hotkey')
    (runtime / 'benchmark_gramatica.py').write_text(src, encoding='utf-8')
    if swa_full is not None:
        model_src = (runtime / 'modelo.py').read_text(encoding='utf-8')
        needle = 'use_mmap=config.get("use_mmap", True), verbose=False,'
        replacement = 'use_mmap=config.get("use_mmap", True), swa_full=config.get("swa_full"), verbose=False,'
        if needle not in model_src:
            raise RuntimeError('No pude inyectar swa_full en el runtime aislado.')
        (runtime / 'modelo.py').write_text(model_src.replace(needle, replacement), encoding='utf-8')
    return runtime

def isolated_tools(b):
    import jsonschema
    ns = b.ns
    ns['PLANIFICADORES'] = {}
    ns['anotar_intento'] = lambda *a: None
    ns['camino_conocido'] = lambda name, args: (args, None)
    ns['CAMINO_RAPIDO'] = False  # el banco mide al modelo: sin el camino rápido de producción
    original_date = ns['con_fecha']
    from datetime import datetime
    ns['con_fecha'] = lambda text: original_date(text, datetime(2026, 10, 7, 15, 0))
    # Pin the prompt's wiki index so timestamp and candidate order cannot change it.
    b.wiki.indice_texto = lambda: 'Wiki de prueba: sin memorias personales. Perfil, hábitos, apps y rutinas vacíos.'
    ns['obstaculos'].para_prompt = lambda: []
    initial_windows = copy.deepcopy(b.VENTANAS_SIM)
    effects = []
    def focus(id_ventana):
        if id_ventana not in b._ID_SIM:
            return {'ok': False, 'error': 'Ventana inexistente'}
        for w in b.VENTANAS_SIM:
            w['enfocada'] = w['id_ventana'] == id_ventana
        return {'ok': True}
    def close(proceso=None, pid=None, forzar=False, id_ventana=None):
        matches = [w for w in b.VENTANAS_SIM if (id_ventana == w['id_ventana'] or pid == w['pid'] or
                   (proceso and (proceso.casefold() in w['proceso'].casefold() or proceso.casefold() in w['titulo'].casefold())))]
        if len(matches) != 1:
            return {'ok': False, 'error': 'Selecciona una sola ventana de la lista'}
        return {'ok': True, 'cerrada': True, 'requirio_forzar': forzar, 'proceso': matches[0]['proceso']}
    def mouse(accion, x=None, y=None, cantidad=None, control=None, id_ventana=None):
        if accion == 'desplazar':
            return {'ok': isinstance(cantidad, int) and -10 <= cantidad <= 10}
        if control:
            wid = id_ventana or next(w['id_ventana'] for w in b.VENTANAS_SIM if w['enfocada'])
            controls, err = b._controles_sim(wid)
            if err or not any(c['nombre'].casefold() == control.casefold() for c in controls):
                return {'ok': False, 'error': 'Control no encontrado'}
        elif x is None or y is None:
            return {'ok': False, 'error': 'Faltan coordenadas o control'}
        return {'ok': True, 'efecto_visible': True, 'app': 'fixture.exe',
                'despues': b.estado_despues_sim(), 'nota': 'Efecto visible simulado.'}
    def keyboard(accion, texto=None, teclas=None):
        if accion == 'escribir':
            # Usa el mismo planificador que producción; así un atajo pasado como texto se rechaza.
            _plan,error=b.g4.planificar_teclado(accion,texto,teclas)
            return error or {'ok': True, 'efecto_visible': True, 'app': 'fixture.exe',
                             'despues': b.estado_despues_sim(), 'nota': 'Efecto visible simulado.'}
        return {'ok': bool(teclas), 'efecto_visible': bool(teclas), 'app': 'fixture.exe',
                'despues': b.estado_despues_sim(), 'nota': 'Efecto visible simulado.'}
    ns['IMPLEMENTACIONES'].update(enfocar_ventana=focus, cerrar_app=close, mouse=mouse, teclado=keyboard,
        sugerencias=lambda accion, **kw: {'ok': True, 'accion': accion, 'sugerencias': []},
        consultar_memoria=lambda **kw: [], recordar=lambda **kw: {'ok': True, 'id': 1},
        deshacer_movimiento=lambda: {'ok': False, 'error': 'No hay movimientos previos'})
    # Fail closed: every callable is a simulation or an in-memory catalog operation.
    allowed = {'listar_apps', 'abrir_app', 'volumen', 'listar_ventanas', 'enfocar_ventana', 'listar_carpeta',
               'leer_archivo', 'buscar_web', 'recordar', 'consultar_memoria', 'ver_pantalla', 'cerrar_app',
               'mover_archivo', 'mouse', 'teclado', 'listar_controles', 'ejecutar_powershell',
               'sugerencias', 'registro_habitos', 'deshacer_movimiento'}
    assert set(ns['IMPLEMENTACIONES']) <= allowed
    execute = ns['ejecutar']
    def measured(name, args):
        try:
            jsonschema.validate(args, ns['HERRAMIENTAS'][name]['parametros'])
            result = execute(name, args)
        except Exception as exc:
            result = {'ok': False, 'error': str(exc)}
        effects.append({'herramienta': name, 'argumentos': copy.deepcopy(args), 'resultado': copy.deepcopy(result)})
        return result
    ns['ejecutar'] = measured
    def reset():
        b.VENTANAS_SIM[:] = copy.deepcopy(initial_windows)
        b._ID_SIM.clear()
        b._ID_SIM.update({w['id_ventana']: w for w in b.VENTANAS_SIM})
        effects.clear()
    return effects, reset

def main():
    global OUT
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('model', choices=MODELS)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--vision-only', action='store_true')
    parser.add_argument('--vision-normalized', action='store_true')
    parser.add_argument('--round2', action='store_true')
    parser.add_argument('--round3', action='store_true')
    parser.add_argument('--diagnostic', choices=('baseline','prompt','schema','combined'))
    parser.add_argument('--server-url', help='llama-server local ya iniciado; no modifica .venv')
    parser.add_argument('--engine-tag', default='llama_cpp_b11429')
    parser.add_argument('--swa-full', choices=('true','false'))
    parser.add_argument('--test-set', type=Path, help='JSON alternativo de pruebas; siempre se ejecuta en simulación')
    parser.add_argument('--cache-estado', action='store_true',
                        help='fase A: restaura el estado tras el prompt de sistema antes de cada llamada (cache_estado.py)')
    parser.add_argument('--salida', type=Path, help='carpeta nueva para los datos crudos (por defecto, la de la ronda); '
                        'no puede tener ya un JSON de este modelo, para no sobrescribir rondas anteriores')
    args = parser.parse_args()
    if args.vision_normalized:
        args.vision_only = True
    if args.round2 or args.round3 or args.diagnostic:
        OUT = OUT / ('ronda3' if args.round3 else 'ronda2')
    if args.server_url:
        OUT = ROOT / 'comparacion_modelos' / 'datos' / args.engine_tag / ('ronda3' if args.round3 else 'base')
    if args.salida:
        OUT = args.salida.resolve()
        if any(OUT.glob(f'{args.model}*.json')):
            raise SystemExit(f'{OUT} ya tiene datos de {args.model}: elige otra carpeta con --salida.')
    OUT.mkdir(parents=True, exist_ok=True)
    swa_full = None if args.swa_full is None else args.swa_full == 'true'
    ronda = ('ronda3' if args.round3 else 'ronda2') + (f'_{OUT.name}' if args.salida else '')  # --salida: runtime propio
    runtime = prepare(args.model, args.round2 or args.round3 or bool(args.diagnostic), ronda, swa_full=swa_full)
    os.environ.update(SIN_REALES='1', CONFIRMAR='s', PYTHONDONTWRITEBYTECODE='1')
    sys.path.insert(0, str(runtime))
    from guardia_juego import exigir_gpu_libre, juego_abierto
    exigir_gpu_libre('comparación', esperar=True)
    import psutil
    cacao = [p.pid for p in psutil.process_iter(['name', 'cmdline']) if
             (p.info['name'] or '').lower() in ('python.exe', 'pythonw.exe') and
             any(Path(a).name.lower() == 'voz.py' for a in (p.info['cmdline'] or []))]
    if cacao:
        raise RuntimeError(f'Cacao sigue abierto: {cacao}. No se cierra automáticamente.')
    gpu = GPU()
    gpu.start()
    if not args.server_url and gpu.samples[0]['free'] < 12000:
        raise RuntimeError('GPU ocupada; no se carga el modelo.')
    start = time.perf_counter()
    if args.server_url:
        from llama_server_cliente import ClienteLlamaServer
        from llama_server_backend import LlamaServerBackend
        cliente = ClienteLlamaServer(args.server_url)
        modelos_servidor = cliente.modelos()
        servidor_id = modelos_servidor['data'][0]['id']
        backend = LlamaServerBackend(args.server_url, servidor_id)
        backend.metadata['general.architecture'] = modelos_servidor['data'][0].get('meta', {}).get('architecture', 'server')
        import modelo as modelo_runtime
        modelo_runtime.crear_llm = lambda *_a, **_k: backend
    import benchmark_gramatica as b
    import llama_cpp
    import jsonschema
    loaded = gpu.read()
    effects, reset = isolated_tools(b)
    integration=None
    if args.round2 or args.round3 or args.diagnostic:
        from integracion import adjust
        integration=adjust(b.ns,args.diagnostic or 'combined')
        def valid_json(text):
            try:
                jsonschema.validate(json.loads(text),b.ns['ESQUEMA_ACCION'])
                return True
            except (ValueError,jsonschema.ValidationError):
                return False
        b.json_valido=valid_json
    # Native template for each model; Qwen non-thinking for the structured Cacao protocol.
    if args.model.startswith('qwen') and not args.server_url:
        from llama_cpp.llama_chat_format import Jinja2ChatFormatter
        template = '{% set enable_thinking = false %}' + b.llm.metadata['tokenizer.chat_template']
        formatter = Jinja2ChatFormatter(template=template,
            eos_token=b.llm.detokenize([b.llm.token_eos()], special=True).decode(),
            bos_token=b.llm.detokenize([b.llm.token_bos()], special=True).decode(),
            stop_token_ids=[b.llm.token_eos()])
        b.llm.chat_handler = formatter.to_chat_handler()
        rendered=formatter(messages=[{'role':'user','content':'Hola'}]).prompt
        assert rendered.endswith('<|im_start|>assistant\n<think>\n\n</think>\n\n'),'Pensamiento no desactivado'
        template_probe={'generation_suffix':rendered[-60:], 'template_sha256':hashlib.sha256(template.encode()).hexdigest()}
    report = {'model': args.model, 'model_path': str(MODELS[args.model]),
              'version': backend.version if args.server_url else llama_cpp.__version__,
              'backend': 'llama-server' if args.server_url else 'llama-cpp-python',
              'loaded_s': time.perf_counter()-start, 'gpu_baseline': gpu.samples[0], 'gpu_loaded': loaded,
              'config': json.loads((runtime/'config.json').read_text(encoding='utf-8')),
              'prompt_sha256': hashlib.sha256(b.ns['prompt_sistema']().encode()).hexdigest(),
              'architecture': b.llm.metadata.get('general.architecture'), 'cases': [], 'conversation': []}
    cache = None
    if args.cache_estado:  # después de la plantilla de Qwen y del contrato: el prefijo es el del prompt final
        from cache_estado import CacheEstado
        cache = CacheEstado(b.llm, lambda: b.ns['prompt_sistema']())
    report['swa_full'] = swa_full
    report['integration']=integration
    report['template_probe']=(template_probe if args.model.startswith('qwen') and not args.server_url else
                              {'server_native_template': True} if args.server_url else {'native_handler':True})
    raw_call = b.llm.create_chat_completion
    outputs = []
    first = []
    call_start = [0]
    def call(**kw):
        r = raw_call(**kw)
        if not first:
            first.append(time.perf_counter() - call_start[0])
        outputs.append(copy.deepcopy(r))
        return r
    b.llm.create_chat_completion = call
    old_interrupt = b.llm.interrumpir
    last_guard = [time.monotonic()]
    def interrupt():
        if time.perf_counter()-call_start[0] > 120 and call_start[0]:
            raise TimeoutError('120 segundos por tarea')
        if (ROOT/'comparacion_modelos'/'DETENER').exists():
            raise KeyboardInterrupt('Detención solicitada')
        if time.monotonic()-last_guard[0] > 10:
            last_guard[0] = time.monotonic()
            if juego_abierto():
                raise KeyboardInterrupt('Juego detectado: se libera GPU; reanudar después')
        old_interrupt()
    b.llm.interrumpir = interrupt
    def run(text, seed):
        reset()
        outputs.clear()
        first.clear()
        b.llm.reset()
        b.llm._ctx.kv_cache_clear()
        call_start[0] = time.perf_counter()
        r = b.correr('topk', seed, text)
        r['wall_s'] = time.perf_counter()-call_start[0]
        r['first_action_s'] = first[0] if first else None
        r['effects'] = copy.deepcopy(effects)
        r['outputs'] = copy.deepcopy(outputs)
        protection=b.ns['_tarea'].get('proteccion',{})
        r['proteccion']={'verificadas':sorted(protection.get('verificadas',())),
                         'fallos':sorted(protection.get('fallos',())),
                         'correcciones':protection.get('correcciones',0)}
        valid = bool(outputs)
        for out in outputs:
            try:
                jsonschema.validate(json.loads(out['choices'][0]['message']['content']), b.ns['ESQUEMA_ACCION'])
                valid &= out['choices'][0]['finish_reason'] != 'length'
            except Exception:
                valid = False
        r['json_schema_ok'] = valid
        return r
    call_start[0] = time.perf_counter()
    warm = run('hola', 1)
    if warm['error'] or not warm['json_schema_ok']:
        dump(OUT/f'{args.model}_smoke_error.json', warm)
        raise RuntimeError(f'Prueba de humo falló: {warm.get("error")}')
    # Exercise the fallback path after top_k with a deliberately unnatural enum.
    b.llm.set_seed(11)
    b.llm.modo_gramatica = 'topk'
    call_start[0] = time.perf_counter()
    schema = {'type':'object', 'properties':{'color':{'type':'string','enum':['zzqx','wvuy']}, 'n':{'type':'integer'}}, 'required':['color','n']}
    fallback = raw_call(messages=[{'role':'user','content':'Responde con un color y un número.'}],
        response_format={'type':'json_object','schema':schema}, temperature=.3, top_k=1, max_tokens=80)
    jsonschema.validate(json.loads(fallback['choices'][0]['message']['content']), schema)
    report['grammar_probe'] = {'response': fallback,
        'fallbacks': None if args.server_url else b.llm.ultimo_muestreador.respaldos,
        'server_schema_constrained': bool(args.server_url)}
    if args.diagnostic:
        from criterios import complete
        selected=[(14,22),(21,22),(29,11),(30,11),(35,22),(38,11),(40,11),(44,11),(56,22),(57,22),(58,11),(59,33)]
        cases={p['id']:p for p in json.loads((ROOT/'pruebas.json').read_text(encoding='utf-8'))['pruebas']}
        for i,seed in selected:
            r=run(cases[i]['frase'],seed)
            r['id']=i
            r['task_checked']=complete(r)
            report['cases'].append(r)
            print('DIAGNOSTICO',args.diagnostic,i,r['task_checked'],flush=True)
        report['complete']=True
        gpu.close()
        dump(OUT/f'{args.model}_diagnostic_{args.diagnostic}.json',report)
        b.llm.close()
        return
    if args.vision_only:
        from vision import ManejadorVision
        projector = ROOT / ('modelos/comparacion/mmproj-F16.gguf' if args.model.startswith('qwen') else 'modelos/mmproj/mmproj-F16.gguf')
        handler = ManejadorVision(projector, presupuesto=1120)
        if args.model.startswith('qwen'):
            get_template = handler._get_chat_template
            handler._get_chat_template = lambda model: '{% set enable_thinking = false %}' + get_template(model)
        report['vision'] = []
        for task in json.loads((ROOT/'comparacion_modelos/vision.json').read_text(encoding='utf-8')):
            data = (ROOT/'comparacion_modelos/capturas'/task['imagen']).read_bytes()
            from PIL import Image
            import io
            width, height = Image.open(io.BytesIO(data)).size
            b.llm.set_seed(11)
            call_start[0] = time.perf_counter()
            prompt = (f'Esta imagen mide {width} por {height} píxeles. Localiza {task["objetivo"]}. ' +
                ('Devuelve SOLO un JSON con x e y del centro del botón, normalizadas entre 0 y 1000. '
                 'La esquina superior izquierda es (0,0) y la inferior derecha es (1000,1000). '
                 'No devuelvas coordenadas en píxeles.' if args.vision_normalized else
                 'Devuelve SOLO un JSON con x e y del centro del botón, en píxeles de la imagen original. '
                 'Origen (0,0) arriba a la izquierda. No uses coordenadas normalizadas.'))
            vision_schema={'type':'object','properties':{'x':{'type':'integer'},'y':{'type':'integer'}},'required':['x','y']}
            if args.round2:
                from integracion import vision_contract,pixel_point
                prompt,vision_schema=vision_contract(args.model,task['objetivo'])
            result = {'id':task['id'],'task':task,'width':width,'height':height}
            try:
                r = handler(llama=b.llm, messages=[{'role':'user','content':[
                    {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(data).decode()}},
                    {'type':'text','text':prompt}]}], temperature=.3, top_k=64, top_p=.95, max_tokens=128,
                    response_format={'type':'json_object','schema':vision_schema})
                xy = json.loads(r['choices'][0]['message']['content'])
                if args.round2:
                    jsonschema.validate(xy,vision_schema)
                    xy=pixel_point(args.model,xy,width,height)
                elif args.vision_normalized:
                    xy = {'x': xy['x']*width/1000, 'y': xy['y']*height/1000}
                x0,y0,x1,y1 = task['rect']
                result.update(response=r,pixel_point=xy,normalized=args.vision_normalized,
                              hit=x0 <= xy['x'] <= x1 and y0 <= xy['y'] <= y1)
            except Exception as exc:
                result.update(error=str(exc),hit=False)
            result['seconds'] = time.perf_counter()-call_start[0]
            report['vision'].append(result)
            print('VISION',args.model,task['id'],result['hit'],flush=True)
        handler.cerrar()
    elif args.smoke:
        report['warmup'] = warm
    else:
        tree = ast.parse((ROOT/'evaluar_pruebas.py').read_text(encoding='utf-8'))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='primer_paso_ok' or
                 isinstance(n, ast.Assign) and any(getattr(t,'id',None)=='VERIFICACION' for t in n.targets)]
        scoring = {}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'scoring','exec'),scoring)
        test_path = args.test_set.resolve() if args.test_set else ROOT/'pruebas.json'
        test_data = json.loads(test_path.read_text(encoding='utf-8'))
        cases = test_data['pruebas']
        seeds = test_data.get('semillas', [11,22,33])
        report['test_set'] = str(test_path)
        report['test_set_sha256'] = hashlib.sha256(test_path.read_bytes()).hexdigest()
        live_suffix = ('_swa_false' if swa_full is False else '') + ('_nuevas30' if args.test_set else '')
        live_path = OUT / f'{args.model}{live_suffix}.json'
        for seed in seeds:
            for p in cases:
                r = run(p['frase'], seed)
                expected = p['esperado'] if isinstance(p['esperado'],list) else [p['esperado']]
                used = r['herramientas']
                r.update(id=p['id'], tipo=p['tipo'], first_strict=bool(used) and used[0] in expected,
                    first_legacy=scoring['primer_paso_ok'](expected,used))
                r['task_legacy'] = r['first_legacy'] and all(h in used for h in p.get('requiere',[])) and r['error'] is None
                failures = [e for e in effects if isinstance(e['resultado'],dict) and e['resultado'].get('ok') is False]
                # Safety refusals are legitimate for these two prohibited-file cases.
                completed = bool(r['respuesta']) and 'Me pasé del límite' not in r['respuesta']
                r['task_checked'] = r['task_legacy'] and r['json_schema_ok'] and completed and (not failures or p['id'] in (50,55))
                report['cases'].append(r)
                dump(live_path, report)
                print(f"{args.model} {len(report['cases'])}/{len(cases)*len(seeds)} #{p['id']} seed={seed} first={r['first_strict']} task={r['task_checked']} {r['wall_s']:.2f}s",flush=True)
        for i, question in enumerate(QUESTIONS,1):
            r = run(question, 2026)
            report['conversation'].append({'id':i,'question':question, **r})
            dump(live_path, report)
    gpu.close()
    report['gpu_samples'] = gpu.samples
    report['gpu_peak_mib'] = max(s['used'] for s in gpu.samples)
    report['gpu_min_free_mib'] = min(s['free'] for s in gpu.samples)
    expected_cases = (len(cases) * len(seeds)) if not args.vision_only and not args.smoke and not args.diagnostic else None
    report['complete'] = (len(report.get('vision',[])) == 5 if args.vision_only else
                          not args.smoke and len(report['cases']) == expected_cases and len(report['conversation']) == 10)
    suffix = ("_vision_normalized" if args.vision_normalized else "_vision" if args.vision_only else
              "_smoke" if args.smoke else "_swa_false" if swa_full is False else "")
    if args.test_set:
        suffix += '_nuevas30'
    report['cache_estado'] = cache.resumen() if cache else None
    dump(OUT/f'{args.model}{suffix}.json', report)
    print('FIN',args.model,flush=True)
    b.llm.close()

if __name__ == '__main__':
    main()
