from pathlib import Path
import subprocess
import json
import time
ROOT=Path(__file__).resolve().parents[1]
for mode in ('baseline','prompt','schema','combined'):
    output=ROOT/f'comparacion_modelos/datos/ronda2/qwen_q5_diagnostic_{mode}.json'
    if output.exists() and json.loads(output.read_text(encoding='utf-8')).get('complete'):continue
    with (ROOT/f'comparacion_modelos/diagnostico_{mode}.log').open('w',encoding='utf-8') as log:
        r=subprocess.run([str(ROOT/'.venv-pruebas/Scripts/python.exe'),'-B','-u',str(ROOT/'comparacion_modelos/ejecutar.py'),'qwen_q5','--diagnostic',mode],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=0x08000000)
    if r.returncode: raise SystemExit(r.returncode)
    print('FIN DIAGNOSTICO',mode,flush=True)
