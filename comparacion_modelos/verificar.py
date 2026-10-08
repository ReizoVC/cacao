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
if (HERE/'metricas_ronda2.json').exists():
    subprocess.run([sys.executable,'-B',str(HERE/'probar_integracion.py')],check=True)
    integrated=json.loads((HERE/'metricas_ronda2.json').read_text(encoding='utf-8'))
    assert len(integrated)==390
    for model in ('gemma_q5','qwen_q5'):
        cases=[r for r in integrated if r['model']==model]
        assert {(r['id'],r['seed']) for r in cases}=={(i,s) for i in range(1,66) for s in (11,22,33)}
    frozen=json.loads((HERE/'ronda2_congelado.json').read_text(encoding='utf-8'))
    for name,digest in frozen.items():assert sha(ROOT/name if name=='pruebas.json' else HERE/name)==digest
    vision_frozen=json.loads((HERE/'ronda2_vision_congelada.json').read_text(encoding='utf-8'))
    for name,digest in vision_frozen.items():assert sha(HERE/name)==digest
    vision2=json.loads((HERE/'vision_ronda2.json').read_text(encoding='utf-8'))
    assert {(r['model'],r['id']) for r in vision2}=={(m,i) for m in ('gemma_q5','qwen_q5') for i in range(1,6)}
    final_data=[json.loads((HERE/'datos/ronda2'/f'{m}.json').read_text(encoding='utf-8')) for m in ('gemma_q5','qwen_q5')]
    assert all(d['complete'] and len(d['conversation'])==10 for d in final_data)
    assert len({d['prompt_sha256'] for d in final_data})==1
    assert len({d['integration']['schema_sha256'] for d in final_data})==1
    blind2=(ROOT/'respuestas_integracion_ciegas.md').read_text(encoding='utf-8')
    assert blind2.count('## Pregunta ')==10
    for letter in 'WXYZ':assert blind2.count(f'### Respuesta {letter}\n')==10
    assert not any(name in blind2 for name in ('Gemma','Qwen','Q5_K','UD-Q4'))
    assert '## Ronda 2 — integración común y formatos de visión' in report
if (ROOT/'resultados_ciegas.md').exists():
    fresh_blind=(ROOT/'resultados_ciegas.md').read_text(encoding='utf-8')
    assert fresh_blind.count('## Pregunta ')==10
    for letter in 'AB':assert fresh_blind.count(f'### Respuesta {letter}\n')==10
    assert not any(name in fresh_blind.lower() for name in ('gemma','qwen','q5_k','ud-q5'))
    evidence=json.loads((HERE/'conversacion_nueva_integridad.json').read_text(encoding='utf-8'))
    for model,summary in evidence.items():
        raw_path=HERE/'datos/conversacion_nueva/ronda2'/f'{model}.json'
        assert sha(raw_path)==summary['raw_sha256']
        current=json.loads(raw_path.read_text(encoding='utf-8'))
        previous=json.loads((HERE/'datos/ronda2'/f'{model}.json').read_text(encoding='utf-8'))
        assert current['complete'] and len(current['conversation'])==10 and not current['cases']
        assert current['prompt_sha256']==previous['prompt_sha256']
        assert current['integration']['schema_sha256']==previous['integration']['schema_sha256']
        for new,old in zip(current['conversation'],previous['conversation']):
            assert new['question']==old['question'] and new['json_schema_ok'] and not new['error'] and new['respuesta'].strip()
            assert new['outputs'][-1]['created']>old['outputs'][-1]['created']
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
if (HERE/'metricas_ronda2.json').exists():
    manifest['round2']={'cases':len(integrated),'new_conversations':20,'blind_answers_including_references':40,
        'vision_localizations':10,'frozen_sha256':sha(HERE/'ronda2_congelado.json'),
        'metrics_sha256':sha(HERE/'metricas_ronda2.json'),'human_spanish_evaluation':'pendiente'}
(HERE/'integridad.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Verificación completa: configuración original, motor idéntico, referencias y nueva ronda completas.')
