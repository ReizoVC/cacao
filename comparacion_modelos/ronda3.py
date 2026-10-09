"""Ejecuta secuencialmente las tandas congeladas de protecciones."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'comparacion_modelos'
frozen=json.loads((HERE/'ronda3_congelado.json').read_text(encoding='utf-8'))
for name,digest in frozen.items():
    path=ROOT/name if name in ('pruebas.json','herramientas.json','agente_minimo.py','herramientas_grupo4.py','protecciones_ejecucion.py') else HERE/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
for model in ('gemma_q5','qwen_q5'):
    output=HERE/'datos/ronda3'/f'{model}.json'
    if output.exists() and json.loads(output.read_text(encoding='utf-8')).get('complete'):continue
    with (HERE/f'ronda3_{model}.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([str(ROOT/'.venv-pruebas/Scripts/python.exe'),'-B','-u',str(HERE/'ejecutar.py'),
                               model,'--round3'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                              creationflags=0x08000000)
    if result.returncode or not json.loads(output.read_text(encoding='utf-8')).get('complete'):
        raise SystemExit(f'FALLO {model}: {result.returncode}')
    print('FIN',model,flush=True)
