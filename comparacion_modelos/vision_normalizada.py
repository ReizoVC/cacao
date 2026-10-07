from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
for model in ('gemma_q5','gemma_q4','qwen_q4','qwen_q5'):
    with (ROOT/f'comparacion_modelos/{model}_vision_normalized.log').open('w',encoding='utf-8') as log:
        r=subprocess.run([str(ROOT/'.venv-pruebas/Scripts/python.exe'),'-B','-u',
            str(ROOT/'comparacion_modelos/ejecutar.py'),model,'--vision-normalized'],cwd=ROOT,
            stdout=log,stderr=subprocess.STDOUT,creationflags=0x08000000)
    if r.returncode: raise SystemExit(r.returncode)
    print('FIN',model,flush=True)
