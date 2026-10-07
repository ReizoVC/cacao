"""Genera los entregables solo cuando todas las mediciones están completas."""
import hashlib
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
from criterios import complete

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'comparacion_modelos/datos'
LABELS={'gemma_q5':'Gemma 4 12B Q5_K_M (referencia)', 'gemma_q4':'Gemma 4 12B UD-Q4_K_XL',
        'qwen_q4':'Qwen 3.5 9B UD-Q4_K_XL','qwen_q5':'Qwen 3.5 9B UD-Q5_K_XL'}

def pct(xs): return 100*sum(xs)/len(xs)
def percentile(xs,q):
    xs=sorted(x for x in xs if x is not None)
    return xs[round((len(xs)-1)*q)]
def hashfile(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main():
    assert hashfile(ROOT/'config.json').upper()=='FB10D3EC38A7AE49CE3C51CFECA6740D7CEFE19AA5D1EDE08EEE078FE74C884E','Cambió config.json de producción'
    rows={}
    for model in LABELS:
        data=json.loads((OUT/f'{model}.json').read_text(encoding='utf-8'))
        vis=json.loads((OUT/f'{model}_vision.json').read_text(encoding='utf-8'))
        normalized=json.loads((OUT/f'{model}_vision_normalized.json').read_text(encoding='utf-8'))
        assert data['complete'] and vis['complete'] and normalized['complete'],f'{model}: mediciones incompletas'
        assert len(normalized['vision'])==5
        vis['normalized_followup']=normalized
        assert len(data['cases'])==195 and len(data['conversation'])==10 and len(vis['vision'])==5
        assert {(r['id'],r['semilla']) for r in data['cases']}=={(i,s) for i in range(1,66) for s in (11,22,33)}
        rows[model]=(data,vis)
    prompt_hashes={d['prompt_sha256'] for d,v in rows.values()}
    assert len(prompt_hashes)==1,'El prompt difiere entre candidatos'
    lines=['# Comparación de modelos de Cacao', '', 'Fecha: 2026-10-07 (America/Lima). **Mediciones locales nuevas**, herramientas simuladas.', '',
           '## Resultados', '',
           '| Candidato | 1.ª literal | 1.ª histórica | Tareas comprobadas | JSON/esquema | 1.ª acción mediana / p95 | Generación tok/s | VRAM pico texto | Libre al pico texto | Visión píxeles / normalizada |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    summaries={}
    sanitized=[]
    for model,(d,v) in rows.items():
        cases=d['cases']
        count=sum(complete(r) for r in cases)
        decoding=sum(r.get('t_decode',0)+r.get('t_sample',0) for r in cases)
        tps=sum(r.get('tokens',0) for r in cases)/decoding
        lat=[r['first_action_s'] for r in cases if r['first_action_s'] is not None]
        hits=sum(r['hit'] for r in v['vision'])
        summaries[model]={'tasks':count,'tps':tps,'median_action':statistics.median(lat),
                          'free_text':d['gpu_min_free_mib'],'free_vision':v['gpu_min_free_mib'],'vision':hits}
        normalized_hits=sum(r['hit'] for r in v['normalized_followup']['vision'])
        lines.append(f"| {LABELS[model]} | {sum(r['first_strict'] for r in cases)}/195 | {sum(r['first_legacy'] for r in cases)}/195 | {count}/195 ({count/195:.1%}) | {sum(r['json_schema_ok'] for r in cases)}/195 | {statistics.median(lat):.2f} / {percentile(lat,.95):.2f} s | {tps:.1f} | {d['gpu_peak_mib']/1024:.2f} GiB | {d['gpu_min_free_mib']/1024:.2f} GiB | {hits}/5 / {normalized_hits}/5 |")
        for r in cases:
            sanitized.append({'model':model,'id':r['id'],'seed':r['semilla'],'first_strict':r['first_strict'],
                'first_legacy':r['first_legacy'],'task_legacy':r['task_legacy'],'task_checked':complete(r),
                'json_schema_ok':r['json_schema_ok'],'first_action_s':r['first_action_s'],
                'wall_s':r['wall_s'],'tokens':r.get('tokens',0),'t_decode':r.get('t_decode',0),
                't_sample':r.get('t_sample',0),'tools':r['herramientas'],'error_type':(r['error'] or '').split(':')[0]})
    lines += ['', '## VRAM y margen para voz', '',
        'VRAM de **toda la GPU**, incluidas las aplicaciones de fondo; no equivale a memoria exclusiva del modelo. '
        'Muestreo aproximadamente cada 250 ms más el tiempo de nvidia-smi. El pico observado puede omitir transitorios muy cortos. '
        'No se cargó un motor de voz en estas tandas. La última columna es una **estimación**, restando una reserva de 1,34 GiB '
        '(inspirada en los 1,34 GB publicados para Whisper turbo int8_float16 en `resultados_voz.md`; '
        'la unidad histórica no permite más precisión), no una prueba nueva de coexistencia.', '',
        '| Candidato | Base sin modelo | Cargado texto | Pico con visión | Libre con visión | Libre estimado tras voz |',
        '|---|---:|---:|---:|---:|---:|']
    for model,(d,v) in rows.items():
        peak=max(v['gpu_peak_mib'],v['normalized_followup']['gpu_peak_mib'])
        free=min(v['gpu_min_free_mib'],v['normalized_followup']['gpu_min_free_mib'])
        lines.append(f"| {LABELS[model]} | {d['gpu_baseline']['used']/1024:.2f} GiB | {d['gpu_loaded']['used']/1024:.2f} GiB | {peak/1024:.2f} GiB | {free/1024:.2f} GiB | {free/1024-1.34:.2f} GiB |")
    lines += ['', 'El consumo de fondo varió entre tandas: la diferencia cargado menos base fue '
        +', '.join(f"{LABELS[m]}: {(d['gpu_loaded']['used']-d['gpu_baseline']['used'])/1024:.2f} GiB" for m,(d,v) in rows.items())
        +'. Es una aproximación al incremento, no una medición exclusiva del proceso. Para voz se conserva el menor margen observado en las dos tandas de visión.']
    lines += ['', '## Detalle de errores y estabilidad', '']
    lines += ['Las tres semillas repiten las mismas 65 frases: las 195 observaciones no son tareas independientes. '
              'Las diferencias pequeñas, como cuatro tareas entre los Gemma, no prueban superioridad general. '
              'No se calcularon intervalos de confianza ni se optimizaron prompts por candidato.', '']
    lines += ['| Candidato | Conversaciones con respuesta final no vacía | Evaluación humana |', '|---|---:|---|']
    for model,(d,v) in rows.items():
        lines.append(f"| {LABELS[model]} | {sum(bool(r['respuesta']) for r in d['conversation'])}/10 | Pendiente |")
    lines += ['', 'Este recuento solo detecta salidas vacías; no puntúa calidad lingüística. En la pregunta de estudio, '
              'los dos Qwen también invocaron `registro_habitos` para pausar sin que se solicitara. La acción fue simulada.', '']
    for model,(d,v) in rows.items():
        failures={}
        for r in d['cases']:
            if not complete(r): failures.setdefault(r['id'],[]).append(r['semilla'])
        lines += [f'### {LABELS[model]}', '',
                  'Tareas no acreditadas (id: semillas): '+('; '.join(f'{i}: {ss}' for i,ss in failures.items()) or 'ninguna')+'.', '',
                  '| Semilla | Primera literal | Tarea comprobada | JSON | Media tarea |', '|---|---:|---:|---:|---:|']
        for seed in (11,22,33):
            cs=[r for r in d['cases'] if r['semilla']==seed]
            lines.append(f"| {seed} | {sum(r['first_strict'] for r in cs)}/65 | {sum(complete(r) for r in cs)}/65 | {sum(r['json_schema_ok'] for r in cs)}/65 | {statistics.mean(r['wall_s'] for r in cs):.2f} s |")
        lines += ['', 'Visión (coordenadas predichas frente al rectángulo fijado):', '']
        for r in v['vision']:
            text=r.get('response',{}).get('choices',[{'message':{'content':''}}])[0]['message']['content']
            lines.append(f"- Tarea {r['id']}, {r['task']['objetivo']}: {text or r.get('error','sin salida')}; {'acierto' if r['hit'] else 'fallo'}; {r['seconds']:.2f} s.")
        lines += ['', 'Seguimiento con contrato explícito de coordenadas 0–1000 (misma prueba para los cuatro candidatos):', '']
        for r in v['normalized_followup']['vision']:
            text=r.get('response',{}).get('choices',[{'message':{'content':''}}])[0]['message']['content']
            lines.append(f"- Tarea {r['id']}: {text or r.get('error','sin salida')}; punto en píxeles {r.get('pixel_point')}; {'acierto' if r['hit'] else 'fallo'}; {r['seconds']:.2f} s.")
        lines.append('')
    lines += ['## Método y límites', '',
        '- Mismo motor CUDA **llama-cpp-python 0.3.36**, copiado a `.venv-pruebas`; arquitectura `qwen35` cargada y probada. No fue necesaria una versión nueva. DLL y código de producción no modificados.',
        '- Contexto 16.384, todas las capas GPU, flash attention, K/V q8_0, use_mmap=false, temperatura 0,3, top_k=64, top_p=0,95, máximo 512 tokens por acción y 15 pasos por tarea. Semillas 11, 22 y 33.',
        '- Plantilla nativa de cada GGUF. Qwen con `enable_thinking=false` para el protocolo JSON de Cacao; no es una comparación del modo de razonamiento extendido. El prompt de sistema y las herramientas son idénticos.',
        '- Una tarea de calentamiento, fuera del cómputo. Historial y caché KV vacíos antes de cada frase; mide primera acción con prompt frío y kernels calientes. No comparar directamente estas latencias con las tandas históricas que reutilizaban el prefijo.',
        '- Primera acción: tiempo hasta recibir el primer JSON completo (no hasta el primer token). La mediana y p95 incluyen lectura del prompt. Tokens/s: suma de tokens de salida dividida por decode + muestreo; excluye evaluación del prompt y herramientas. Los tokenizadores de las dos familias difieren.',
        '- Primera literal exige que la primera herramienta esté en `esperado`. Primera histórica conserva `primer_paso_ok` de evaluar_pruebas.py (acepta verificaciones previas). Tareas comprobadas añade validación de argumentos/efectos mediante criterios.py; #44 acepta que la terminal ya esté enfocada. Ninguna cifra demuestra éxito en Windows real.',
        '- JSON/esquema valida el sobre de Cacao: `argumentos` admite un objeto vacío. Un `finalizar` con `{}` puede ser JSON válido y producir una respuesta vacía; no se acredita como tarea completa. La comprobación de tareas es automática, con condiciones específicas para volumen, apps, archivos y controles; otros casos conservan evidencia de herramientas más respuesta no vacía, sin evaluar exhaustivamente la verdad del texto. Un error intermedio recuperado no invalida por sí solo el éxito final.',
        '- Herramientas completamente simuladas; validaciones de ventanas reales sustituidas por fixtures. Ventanas restablecidas por caso, fecha fija, wiki vacía fija, sin hábitos, archivos, capturas personales ni memoria de producción. El catálogo local de apps se copia de solo lectura y se mantiene igual para todos.',
        '- Conversación: diez preguntas idénticas, semilla 2026, mismo agente y gramática. Respuestas finales sin editar; evaluación humana pendiente. Etiquetas A–D sorteadas; clave en archivo separado.',
        '- Visión: cinco localizaciones sobre dos capturas reales limpias (Calculadora y Bloc de notas vacío), semilla 11. Sin clics del modelo ni texto UIA suministrado. Acierto si el punto cae en el rectángulo fijado antes de medir. Presupuesto de imagen 1120; cada arquitectura puede tokenizar la imagen de forma distinta. Muestra pequeña.',
        '- La primera tanda pidió píxeles originales. Al observar salidas compatibles con una escala 0–1000, se repitieron las cinco tareas para TODOS los candidatos con ese contrato explícito y conversión a píxeles. Es un seguimiento exploratorio, no reemplaza la tanda inicial ni aplica una corrección retrospectiva a sus respuestas.',
        '- El sistema detiene la inferencia si detecta un juego. No cierra Cacao automáticamente; el usuario lo cerró antes de medir.',
        '- Incidencia de preparación: una carga de Gemma falló al reservar 2720 MiB de caché CUDA; el reintento tras las descargas funcionó. No se contabilizó como tarea. No se determinó la causa exacta.', '',
        '## Compatibilidad de la gramática', '',
        '| Candidato | Versión | Respaldos en prueba top_k=1 | Resultado |', '|---|---|---:|---|']
    for model,(d,v) in rows.items():
        lines.append(f"| {LABELS[model]} | {d['version']} | {d['grammar_probe']['fallbacks']} | Enum artificial y entero: JSON validado |")
    lines += ['', 'La prueba fuerza el camino de respaldo desde top_k a vocabulario completo; las 195 tareas comprueban además el esquema JSON de Cacao. Esto valida esta instalación, no garantiza compatibilidad con futuras versiones.', '', '## Recomendación', '',
        '**Mantener Gemma 4 12B Q5_K_M por ahora**, pendiente de tu evaluación a ciegas. Es el candidato con más tareas acreditadas en esta integración. No se cambió el modelo de producción.', '',
        'Gemma UD-Q4_K_XL reduce el tamaño en disco y algo el pico observado, pero no ganó velocidad de generación y acreditó menos tareas. Con la variación de VRAM de fondo, estas tandas no justifican un cambio por rendimiento.', '',
        'Qwen genera alrededor de 48 frente a 30 tok/s y reduce la mediana de primera acción a unos 2,5–2,6 s. Deja mucho más margen para voz, pero ambos cuantizados omitieron acciones en pedidos compuestos: por ejemplo, #29 ajusta volumen sin abrir Spotify, y #30 abre Calculadora sin ajustar volumen. Algunas respuestas dicen haber hecho ambas cosas. También hubo respuestas finales vacías aunque el JSON era válido. Son problemas medidos con el protocolo actual de Cacao; no demuestran incapacidad general del modelo.', '',
        'Si priorizas voz y quieres continuar evaluando Qwen, **UD-Q5_K_XL es el siguiente candidato**: acreditó más tareas que Q4 y conservó amplio margen de VRAM. Antes de adoptarlo habría que validar una integración que exija mensaje final y verifique todos los pasos. La visión normalizada mejoró a 4/5 para ambos Qwen; exige adaptar y verificar ese contrato en Cacao y ampliar las capturas. Ningún cambio de producción forma parte de esta comparación.', '',
        '## Evaluación a ciegas y archivos', '',
        '- [Respuestas a ciegas](respuestas_comparacion_ciegas.md): puntuar claridad, corrección, naturalidad y brevedad (1–5), sin abrir la clave.',
        '- [Clave separada](clave_comparacion_modelos.md): abrir después de puntuar.',
        '- [Mediciones por frase sin datos personales](comparacion_modelos/metricas.json). Registros completos locales en `comparacion_modelos/datos/` (excluidos de Git).',
        '- Código reproducible, criterios y capturas: `comparacion_modelos/`. Modelos en `modelos/comparacion/`; entorno en `.venv-pruebas/`; ambos excluidos de Git.', '',
        '## Procedencia e integridad', '',
        '- Gemma: [unsloth/gemma-4-12b-it-GGUF](https://huggingface.co/unsloth/gemma-4-12b-it-GGUF/tree/fc034cfff751157913579611efad8462ac1be606).',
        '- Qwen: [unsloth/Qwen3.5-9B-GGUF](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/tree/3885219b6810b007914f3a7950a8d1b469d598a5).',
        '- Tamaños y SHA256 comprobados en descargar.ps1. Tres modelos nuevos + mmproj: 20.994.365.248 bytes (19,55 GiB).',
        '- Espacio antes de descargar: 29.248.856.064 bytes (27,24 GiB). La memoria virtual de Windows redujo el margen durante la carga; no se cambiaron ajustes del sistema.',
        '- SHA256 config.json de producción: `'+hashfile(ROOT/'config.json')+'`.',
        '- SHA256 prompt común: `'+next(iter(prompt_hashes))+'`.',
        '- Commit de código de Cacao evaluado: `3e9a735`.', '']
    (ROOT/'resultados_comparacion_modelos.md').write_text('\n'.join(lines),encoding='utf-8')
    (ROOT/'comparacion_modelos/metricas.json').write_text(json.dumps(sanitized,ensure_ascii=False,indent=1),encoding='utf-8')
    vision_evidence=[]
    for model,(d,v) in rows.items():
        for normalized,tanda in ((False,v),(True,v['normalized_followup'])):
            for r in tanda['vision']:
                vision_evidence.append({'model':model,'normalized':normalized,'id':r['id'],
                    'task':r['task'],'width':r['width'],'height':r['height'],
                    'response':r.get('response',{}).get('choices',[{'message':{'content':''}}])[0]['message']['content'],
                    'pixel_point':r.get('pixel_point'),'hit':r['hit'],'seconds':r['seconds']})
    (ROOT/'comparacion_modelos/evidencia_vision.json').write_text(json.dumps(vision_evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    key_path=ROOT/'clave_comparacion_modelos.md'
    if key_path.exists():
        previous=key_path.read_text(encoding='utf-8')
        key={letter:next(m for m,label in LABELS.items() if f'- {letter}: {label}\n' in previous) for letter in 'ABCD'}
    else:
        keys=list(rows)
        random.SystemRandom().shuffle(keys)
        key=dict(zip('ABCD',keys))
    blind=['# Evaluación a ciegas — Cacao','','Puntúa cada respuesta de 1 a 5 en claridad, corrección, naturalidad y brevedad. Las respuestas se muestran sin editar. No abras la clave hasta terminar.','']
    for i in range(10):
        blind += [f'## Pregunta {i+1}', '', rows[key['A']][0]['conversation'][i]['question'], '']
        for letter,model in key.items():
            blind += [f'### Respuesta {letter}', '', rows[model][0]['conversation'][i]['respuesta'] or '[Sin respuesta]', '',
                      'Claridad: __ /5 · Corrección: __ /5 · Naturalidad: __ /5 · Brevedad: __ /5','']
    (ROOT/'respuestas_comparacion_ciegas.md').write_text('\n'.join(blind),encoding='utf-8')
    (ROOT/'clave_comparacion_modelos.md').write_text('# Clave de la evaluación a ciegas\n\nAbrir solo después de puntuar.\n\n'+'\n'.join(f'- {letter}: {LABELS[model]}' for letter,model in key.items())+'\n',encoding='utf-8')
    print(json.dumps(summaries,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
