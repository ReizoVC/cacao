"""Entrega veinte respuestas nuevas, mezcladas por pregunta, con clave separada."""
import hashlib
import json
from pathlib import Path
import random

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/'datos/conversacion_nueva/ronda2'
models=('gemma_q5','qwen_q5')
data={m:json.loads((OUT/f'{m}.json').read_text(encoding='utf-8')) for m in models}
reference=json.loads((HERE/'resumen_ronda2.json').read_text(encoding='utf-8'))
for model,d in data.items():
    assert d['complete'] and len(d['conversation'])==10 and not d['cases']
    assert d['prompt_sha256']==reference[model]['prompt_sha256']
    assert d['integration']['schema_sha256']==reference[model]['schema_sha256']
    assert d['integration']['json_control_characters_excluded']
    assert all(r['json_schema_ok'] and not r['error'] and str(r['respuesta'] or '').strip() for r in d['conversation'])
assert [r['question'] for r in data[models[0]]['conversation']]==[r['question'] for r in data[models[1]]['conversation']]

key_file=ROOT/'clave_resultados_ciegas.md'
mapping_file=OUT/'clave.json'
if mapping_file.exists():
    mapping=json.loads(mapping_file.read_text(encoding='utf-8'))
else:
    mapping={}
    for i in range(1,11):
        order=list(models);random.SystemRandom().shuffle(order)
        mapping[str(i)]=dict(zip('AB',order))
    mapping_file.write_text(json.dumps(mapping,indent=2),encoding='utf-8')
blind=['# Diez preguntas de conversación — evaluación a ciegas','',
    'Dos respuestas recién generadas por pregunta, sin editar. Las letras se mezclan de nuevo en cada pregunta: A no identifica siempre la misma variante. Evalúa cada respuesta antes de abrir la clave.','']
key=['# Clave — abrir únicamente después de evaluar','',
    'Correspondencia por pregunta; las letras no son constantes entre preguntas.','']
for i in range(1,11):
    blind += [f'## Pregunta {i}','',data[models[0]]['conversation'][i-1]['question'],'']
    key += [f'## Pregunta {i}','']
    for letter,model in mapping[str(i)].items():
        blind += [f'### Respuesta {letter}','',data[model]['conversation'][i-1]['respuesta'],'',
            'Claridad: __/5 · Corrección: __/5 · Naturalidad: __/5 · Brevedad: __/5','']
        key.append(f'- {letter}: {model}')
    key.append('')
text='\n'.join(blind)
assert text.count('## Pregunta ')==10
assert all(text.count(f'### Respuesta {letter}\n')==10 for letter in 'AB')
assert not any(name.lower() in text.lower() for name in ('Gemma','Qwen','Q5_K_M','UD-Q5'))
(ROOT/'resultados_ciegas.md').write_text(text,encoding='utf-8')
key_file.write_text('\n'.join(key),encoding='utf-8')
evidence={m:{'raw_sha256':hashlib.sha256((OUT/f'{m}.json').read_bytes()).hexdigest(),
    'prompt_sha256':d['prompt_sha256'],'schema_sha256':d['integration']['schema_sha256'],
    'count':10,'seed':2026,'valid_json':10,'blank':0,
    'completion_timestamps':[r['outputs'][-1]['created'] for r in d['conversation']]} for m,d in data.items()}
(HERE/'conversacion_nueva_integridad.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
report_path=ROOT/'resultados_comparacion_modelos.md'
marker='\n## Complemento — conversación nueva y revisión semántica\n'
report=report_path.read_text(encoding='utf-8').split(marker)[0]
report_path.write_text(report.rstrip()+'\n'+marker.strip()+'\n\n'
    'Se ejecutó nuevamente la inferencia de las diez preguntas con cada Q5, usando '
    'la misma integración corregida, semilla 2026 y parámetros. Veinte respuestas '
    'no vacías, con JSON validado. No se copiaron respuestas anteriores; con la '
    'misma semilla pueden coincidir. La puntuación humana sigue pendiente.\n\n'
    '[Nueva evaluación a ciegas](resultados_ciegas.md), '
    '[clave separada: abrir después](clave_resultados_ciegas.md). '
    'A/B se sortean por pregunta; no identifican siempre al mismo modelo.\n\n'
    '[Clasificación semántica de los siete fallos de Qwen](clasificacion_fallos_qwen.md): '
    'dos alternativas funcionales (#10 s22 y #56 s22), una aclaración segura pendiente '
    '(#13 s11) y cuatro fallos operativos (#14 s11, #43 s22, #59 s22 y #59 s33). '
    '#14 añadió acciones no pedidas. #59 s22 escribió texto literal e intentó '
    'guardar por PowerShell en una ruta inventada: la escritura fue bloqueada. '
    'No se ejecutó ninguna acción real. La puntuación congelada permanece 188/195.\n\n'
    'Huellas y fechas de estas inferencias: '
    'comparacion_modelos/conversacion_nueva_integridad.json. Producción intacta.\n',encoding='utf-8')
print('Veinte respuestas nuevas verificadas. Clave separada; evaluación humana pendiente.')
