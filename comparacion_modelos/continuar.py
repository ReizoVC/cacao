"""Secuencia estricta: un solo modelo ocupa la GPU. Admite reanudar resultados completos."""
from pathlib import Path
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv-pruebas/Scripts/python.exe'
RUNNER = ROOT / 'comparacion_modelos/ejecutar.py'
OUT = ROOT / 'comparacion_modelos/datos'

for vision in (False, True):
    for model in ('gemma_q5','gemma_q4','qwen_q4','qwen_q5'):
        suffix = '_vision' if vision else ''
        path = OUT / f'{model}{suffix}.json'
        if path.exists() and json.loads(path.read_text(encoding='utf-8')).get('complete'):
            continue
        if (ROOT/'comparacion_modelos/DETENER').exists():
            raise SystemExit('Detención solicitada')
        with (ROOT/f'comparacion_modelos/{model}{suffix}.log').open('w',encoding='utf-8') as log:
            cmd = [str(PYTHON),'-B','-u',str(RUNNER),model] + (['--vision-only'] if vision else [])
            print('INICIO',model,suffix,flush=True)
            result = subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                                    creationflags=0x08000000)
        if result.returncode or not path.exists() or not json.loads(path.read_text(encoding='utf-8')).get('complete'):
            print('FALLO',model,suffix,result.returncode,flush=True)
            raise SystemExit(1)
        print('TERMINADO',model,suffix,flush=True)
        time.sleep(5)
