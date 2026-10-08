"""Tandas completas, secuenciales, con protocolo congelado."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'comparacion_modelos'
OUT=HERE/'datos/ronda2'
diagnostic_path=OUT/'qwen_q5_diagnostic_combined.json'
while True:
    try:
        if json.loads(diagnostic_path.read_text(encoding='utf-8')).get('complete'):break
    except (OSError,json.JSONDecodeError):pass
    time.sleep(5)
time.sleep(5)
frozen=json.loads((HERE/'ronda2_congelado.json').read_text(encoding='utf-8'))
for name,digest in frozen.items():
    path=ROOT/name if name=='pruebas.json' else HERE/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,f'Cambio tras congelar: {name}'
for vision in (False,True):
    for model in ('gemma_q5','qwen_q5'):
        suffix='_vision' if vision else ''
        path=OUT/f'{model}{suffix}.json'
        if path.exists() and json.loads(path.read_text(encoding='utf-8')).get('complete'):continue
        with (HERE/f'ronda2_{model}{suffix}.log').open('w',encoding='utf-8') as log:
            command=[str(ROOT/'.venv-pruebas/Scripts/python.exe'),'-B','-u',str(HERE/'ejecutar.py'),model,'--round2']
            if vision:command.append('--vision-only')
            print('INICIO',model,suffix,flush=True)
            result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=0x08000000)
        if result.returncode or not json.loads(path.read_text(encoding='utf-8')).get('complete'):raise SystemExit(f'FALLO {model} {suffix}: {result.returncode}')
        print('FIN',model,suffix,flush=True)
