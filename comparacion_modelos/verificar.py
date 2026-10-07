"""Verifica integridad y entregables sin cargar modelos ni ejecutar herramientas."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

assert sha(ROOT/'config.json').upper()=='FB10D3EC38A7AE49CE3C51CFECA6740D7CEFE19AA5D1EDE08EEE078FE74C884E'
subprocess.run([sys.executable,'-B',str(HERE/'probar_criterios.py')],check=True)
for path in HERE.glob('*.py'): ast.parse(path.read_text(encoding='utf-8'),str(path))
metrics=json.loads((HERE/'metricas.json').read_text(encoding='utf-8'))
assert len(metrics)==780
for model in ('gemma_q5','gemma_q4','qwen_q4','qwen_q5'):
    rows=[r for r in metrics if r['model']==model]
    assert {(r['id'],r['seed']) for r in rows}=={(i,s) for i in range(1,66) for s in (11,22,33)}
    raw=json.loads((HERE/'datos'/f'{model}.json').read_text(encoding='utf-8'))
    assert raw['version']=='0.3.36' and raw['complete']
    assert raw['config']['n_ctx']==16384 and raw['config']['flash_attn'] is True
    assert raw['config']['type_k']==raw['config']['type_v']=='q8_0'
    assert raw['grammar_probe']['fallbacks']>0
blind=(ROOT/'respuestas_comparacion_ciegas.md').read_text(encoding='utf-8')
assert blind.count('## Pregunta ')==10
for letter in 'ABCD': assert blind.count(f'### Respuesta {letter}\n')==10
assert not any(name in blind for name in ('Gemma','Qwen','Q5_K','UD-Q4'))
report=(ROOT/'resultados_comparacion_modelos.md').read_text(encoding='utf-8')
assert 'PENDIENTE' not in report
vision=json.loads((HERE/'evidencia_vision.json').read_text(encoding='utf-8'))
assert len(vision)==40
engine=[]
production=ROOT/'.venv/Lib/site-packages/llama_cpp'
testing=ROOT/'.venv-pruebas/Lib/site-packages/llama_cpp'
for path in sorted(production.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts: continue
    relative=path.relative_to(production)
    digest=sha(path)
    assert digest==sha(testing/relative),f'Diferencia en motor: {relative}'
    engine.append({'path':relative.as_posix(),'bytes':path.stat().st_size,'sha256':digest})
manifest={'date':'2026-10-07','cacao_commit':'3e9a735','llama_cpp_python':'0.3.36',
    'production_config_sha256':sha(ROOT/'config.json'),'engine_files':engine,
    'fixtures_sha256':{name:sha(ROOT/name) for name in ('pruebas.json','herramientas.json','apps_categorias.json')},
    'screenshots_sha256':{p.name:sha(p) for p in sorted((HERE/'capturas').glob('*.png'))},
    'python':sys.version,'status':'195 casos por candidato, 40 conversaciones, 40 localizaciones; motor idéntico al de producción'}
(HERE/'integridad.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Verificación completa: configuración original, motor idéntico, 780 casos y documentos completos.')
