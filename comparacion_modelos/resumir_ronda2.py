"""Anexa ronda 2 sin sustituir la evidencia de la primera ronda."""
import hashlib
import json
from pathlib import Path
import random
import statistics
from criterios import complete
from integracion import complete_round2
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'comparacion_modelos'
OLD=HERE/'datos'
NEW=OLD/'ronda2'
LABELS={'gemma_q5':'Gemma Q5','qwen_q5':'Qwen Q5'}
MARKER='\n## Ronda 2 — integración común y formatos de visión\n'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def stats(data):
    cs=data['cases'];lat=sorted(r['first_action_s'] for r in cs if r['first_action_s'] is not None)
    return {'tasks':sum(complete_round2(r) for r in cs),'blank':sum(not str(r['respuesta'] or '').strip() for r in cs),
        'blank_conversation':sum(not str(r['respuesta'] or '').strip() for r in data['conversation']),
        'json':sum(r['json_schema_ok'] for r in cs),'first':sum(r['first_strict'] for r in cs),
        'median':statistics.median(lat),'p95':lat[round((len(lat)-1)*.95)],
        'task_mean':statistics.mean(r['wall_s'] for r in cs),
        'tps':sum(r.get('tokens',0) for r in cs)/sum(r.get('t_decode',0)+r.get('t_sample',0) for r in cs)}

def classify(r):
    actions=[json.loads(o['choices'][0]['message']['content']) for o in r.get('outputs',[])]
    if r.get('error') and 'UnicodeEncodeError' in r['error']:
        return 'Entorno del ejecutor','Impresión CP1252 abortó al encontrar caracteres no representables; no es fallo de capacidad.'
    if r['id']==44:
        return 'Evaluador','PowerShell ya estaba enfocado; el criterio anterior dependía de la palabra terminal.'
    if not r.get('respuesta'):
        misplaced=any(a.get('herramienta')=='finalizar' and not a.get('argumentos',{}).get('mensaje') and a.get('mensaje_final') for a in actions)
        if misplaced:return 'Prompt + gramática permisiva','El modelo escribió la respuesta en mensaje_final de finalizar; el loop lee argumentos.mensaje. No faltó texto generado.'
        return 'Prompt / protocolo; causalidad pendiente','Respuesta final vacía; el sobre JSON permitía argumentos vacíos. Ver diagnóstico y repetición.'
    if r['id'] in (29,30,31,34):
        return 'Prompt + cierre anticipado','mensaje_final terminó toda la tarea después de una sola acción; otras acciones pedidas no se ejecutaron.'
    if r['id']==58:
        return 'Prompt / planificación residual','Abrió otra instancia o no enfocó el Bloc existente; no completó la escritura en la ventana solicitada.'
    if r['id']==57:return 'Prompt / interpretación residual','Confundió bajar la rueda del mouse con bajar el volumen.'
    if r['id']==56:return 'Prompt / elección de herramienta residual','Cerró la app mediante cerrar_app en vez de ejecutar el clic solicitado.'
    return 'Capacidad residual no determinada','No hay evidencia suficiente para separar una limitación del modelo de un problema de integración.'

def main():
    frozen=read(HERE/'ronda2_congelado.json')
    for name,digest in frozen.items():
        assert sha(ROOT/name if name=='pruebas.json' else HERE/name)==digest
    for name,digest in read(HERE/'ronda2_vision_congelada.json').items():assert sha(HERE/name)==digest
    assert sha(ROOT/'config.json').upper()=='FB10D3EC38A7AE49CE3C51CFECA6740D7CEFE19AA5D1EDE08EEE078FE74C884E'
    rows={m:read(NEW/f'{m}.json') for m in LABELS}
    visions={m:read(NEW/f'{m}_vision.json') for m in LABELS}
    older={m:read(OLD/f'{m}.json') for m in LABELS}
    for m,d in rows.items():
        assert d['complete'] and visions[m]['complete']
        assert {(r['id'],r['semilla']) for r in d['cases']}=={(i,s) for i in range(1,66) for s in (11,22,33)}
        assert len(d['conversation'])==10 and len(visions[m]['vision'])==5
    assert len({d['prompt_sha256'] for d in rows.values()})==1
    assert len({d['integration']['schema_sha256'] for d in rows.values()})==1
    diagnostics={mode:read(NEW/f'qwen_q5_diagnostic_{mode}.json') for mode in ('baseline','prompt','schema','combined')}
    qs=stats(rows['qwen_q5']);gs=stats(rows['gemma_q5'])
    automatic=qs['tasks']>=186 and qs['blank']==0 and qs['blank_conversation']==0
    lines=[MARKER.strip(),'','Protocolo fijado antes de las tandas completas: [ronda2_protocolo.md](comparacion_modelos/ronda2_protocolo.md). '
        'Producción sigue con Gemma Q5; no se cambió config.json ni .venv. No se descargaron modelos nuevos.','',
        '**Aceptación fijada:** Qwen necesita ≥186/195 tareas completas, cero respuestas finales vacías '
        'en las 195 tareas y las diez preguntas, y no empeorar el español según tu evaluación a ciegas.','',
        '### Comparación automática','',
        '| Modelo / ronda | Tareas completas | Primera literal | JSON/esquema | Vacías tareas / conversación | Primera acción mediana / p95 | Media tarea | tok/s |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for m in LABELS:
        for title,data in (('anterior recalculada',older[m]),('integración común',rows[m])):
            s=stats(data)
            lines.append(f"| {LABELS[m]} / {title} | {s['tasks']}/195 ({s['tasks']/195:.1%}) | {s['first']}/195 | {s['json']}/195 | {s['blank']} / {s['blank_conversation']} | {s['median']:.2f} / {s['p95']:.2f} s | {s['task_mean']:.2f} s | {s['tps']:.1f} |")
    lines += ['', '**Resultado automático de Qwen:** '+('cumple ambos requisitos automáticos; el español sigue pendiente.' if automatic else 'NO cumple todos los requisitos automáticos; no pasa el criterio fijado.') , '',
        'La condición de español aún no tiene puntuación humana. No se declara aprobado el criterio completo. '
        'Las 195 observaciones son tres repeticiones de las mismas 65 frases, sin prueba adicional de generalización.', '',
        'Se conserva el evaluador anterior salvo #44: la terminal PowerShell ya enfocada acredita el pedido. '
        'La referencia Qwen se recalculó con la misma corrección; las cifras originales permanecen arriba. '
        'Los otros requisitos de argumentos y efectos no se relajaron.','',
        'Gemma cambió de '+str(stats(older['gemma_q5'])['tasks'])+' a '+str(gs['tasks'])+' tareas completas. '
        +('No perdió tareas en el total.' if gs['tasks']>=stats(older['gemma_q5'])['tasks'] else 'El ajuste empeoró el total de Gemma; no cumple el objetivo de evitar regresión.')
        +' Las diferencias de latencia se muestran en la tabla; no se presupone que el ajuste sea gratuito.', '',
        '### Qué se corrigió y qué se verificó','',
        '- **Plantilla y pensamiento:** se mantiene la plantilla nativa del GGUF de Qwen con enable_thinking=false. '
        'El sufijo renderizado incluye un bloque think ya cerrado antes de generar. La primera ronda ya lo hacía; '
        'no se detectó pensamiento activo ni una plantilla equivocada que explique estos fallos. El historial '
        'se serializa mediante esa plantilla; no se cambió al protocolo XML de herramientas nativas.',
        '- **Prompt/descripciones comunes:** formato explícito finalizar → argumentos.mensaje, acciones pendientes '
        'antes de finalizar, advertencia de que mensaje_final corta TODA la tarea y consejos sin cambios de ajustes. '
        'El mismo texto y descripción de finalizar se aplican a ambos modelos.',
        '- **Gramática:** el sobre anterior permitía argumentos vacíos y mensaje_final en finalizar. Ahora '
        'oneOf separa finalizar, exige mensaje no vacío y exito, y excluye mensaje_final allí. Las otras acciones '
        'también excluyen mensaje_final; siempre se requiere finalizar. Esto añade una llamada en pedidos '
        'que antes tenían cierre rápido. No se suministra al modelo la herramienta esperada ni '
        'se fuerza una secuencia basada en las respuestas del set.',
        '- **Convertidor JSON:** el piloto V3 encontró JSONDecodeError en Qwen #14 s22: un salto de línea '
        'literal en pensamiento. La regla char de llama-cpp-python 0.3.36 excluía comillas y barra, '
        'pero permitía controles U+0000–U+001F. Se corrigió esa regla en memoria del proceso para ambos '
        'modelos, antes de compilar la gramática. Se mantienen json.loads y validación estrictos; '
        'no se arregla ni reemplaza la salida generada para acreditarla. Esta corrección no modifica .venv '
        'ni archivos de .venv-pruebas.',
        '- **Entorno:** stdout/stderr UTF-8. Dos fallos anteriores fueron UnicodeEncodeError al imprimir caracteres '
        'del pensamiento, no errores de JSON ni ausencia de capacidad. El diagnóstico base con UTF-8 permite '
        'comprobar esa recuperación sin cambiar prompt/esquema.',
        '- **Capacidad real:** no se puede demostrar una limitación intrínseca a partir de estas tareas. Los errores '
        'que persistan se registran como residuales bajo esta integración; no se atribuyen automáticamente a tamaño '
        'del modelo. Todas las herramientas siguen siendo simuladas.', '',
        '### Diagnóstico factorial exploratorio de Qwen','',
        'Doce observaciones originales representativas, mismas frases y semillas; registro UTF-8 en todas. '
        'Base, prompt y esquema corresponden al piloto previo a las dos aclaraciones de apertura y rueda; '
        'combined corresponde al contrato final con esas aclaraciones y la regla de controles JSON corregida. No es un factorial perfectamente '
        'aislado de esos cambios; se conserva el diagnóstico anterior en los registros. '
        'No es una segunda puntuación de aceptación. Las causas por familia son hipótesis apoyadas por salida '
        'y código; una mejora agregada no prueba la causa de cada observación individual.', '',
        '| Ajuste | Tareas completas / 12 | Respuestas vacías |', '|---|---:|---:|']
    for mode,d in diagnostics.items():
        lines.append(f"| {mode} | {sum(complete_round2(r) for r in d['cases'])}/12 | {sum(not r['respuesta'] for r in d['cases'])} |")
    lines += ['', 'El piloto inicial conservaba el cierre rápido: prompt y esquema combinados acreditaron 9/12 '
        'pero todavía omitieron acciones en #29 y #30. Se detuvo una tanda parcial de Gemma y se archivó '
        'sin puntuarla. Antes de las tandas definitivas se fijó retirar mensaje_final para ambos modelos. '
        'Los pilotos completos y la tanda parcial se conservan en datos/piloto_ronda2_v1, fuera de Git.', '',
        'El siguiente contrato, sin cierre rápido, obtuvo 188/195 en Gemma frente a 190/195 de referencia. '
        'Se rechazó ese ajuste común y no se declara como resultado final. Antes de repetir ambos modelos '
        'se aclararon apertura directa y signo de la rueda usando el contrato de Windows existente. '
        'Datos conservados en datos/piloto_ronda2_v2. El set y el umbral no se modificaron; estas iteraciones '
        'usan el mismo set conocido y pueden sobreajustarlo, por lo que falta validación fuera de él.', '',
        'El piloto V3 acreditó 195/195 en Gemma y fue detenido durante Qwen tras detectar el salto de línea '
        'JSON sin escapar. Se conservó íntegro en datos/piloto_ronda2_v3. No se acredita como tanda final '
        'ni se combina con observaciones de otras versiones: ambos modelos se repitieron desde cero '
        'con la corrección común del convertidor y nuevas huellas congeladas.', '',
        'Límite de las simulaciones: las listas de controles y las ventanas son fixtures; no actualizan '
        'contenido escrito ni desaparición de una ventana tras cerrarla. La puntuación comprueba argumentos '
        'y resultados de herramientas, no una interfaz que evolucione con todas las acciones. Un modelo '
        'que insiste en verificar puede encontrar esa falta de cambios. No se atribuye a capacidad real '
        'del modelo sin repetir en una simulación con estado completo o en apps de prueba reales.']
    audit=[]
    final={(r['id'],r['semilla']):r for r in rows['qwen_q5']['cases']}
    lines += ['', '### Auditoría de cada fallo original de Qwen Q5','',
        '| ID | Semilla | Clasificación | Evidencia del fallo original | Ronda 2 |','|---|---:|---|---|---|']
    for r in older['qwen_q5']['cases']:
        if complete(r):continue
        category,evidence=classify(r)
        new=final[r['id'],r['semilla']]
        audit.append({'kind':'task','id':r['id'],'seed':r['semilla'],'category':category,'evidence':evidence,
            'round2_complete':complete_round2(new),'round2_blank':not bool(new['respuesta'])})
        lines.append(f"| {r['id']} | {r['semilla']} | {category} | {evidence} | {'Completa' if complete_round2(new) else 'Falla'} |")
    lines += ['', 'Se añaden entorno y evaluador como categorías porque forzar esos errores a plantilla, '
        'pensamiento, gramática, prompt o capacidad atribuiría una causa incorrecta al modelo.', '',
        'En las diez preguntas originales, siete respuestas finales de Qwen estaban vacías y en la pregunta '
        'de estudio se pausaron hábitos sin autorización (simulada). Las vacías se revisan con el mismo análisis '
        'de campos y se incluyen junto con su repetición en la evaluación a ciegas.', '',
        '| Pregunta de conversación | Clasificación | Evidencia original | Ronda 2 |','|---|---|---|---|']
    for r in older['qwen_q5']['conversation']:
        unsolicited=any(e['herramienta']=='registro_habitos' for e in r['effects'])
        if r['respuesta'] and not unsolicited:continue
        category,evidence=classify(r) if not r['respuesta'] else ('Prompt / acción no solicitada','Pausó el registro de hábitos al recibir un pedido de consejo para estudiar.')
        new=rows['qwen_q5']['conversation'][r['id']-1]
        new_unsolicited=any(e['herramienta']=='registro_habitos' for e in new['effects'])
        status=('Vacía' if not new['respuesta'] else 'Con respuesta')+('; pausa hábitos no solicitada' if new_unsolicited else '')
        audit.append({'kind':'conversation','id':r['id'],'seed':2026,'category':category,'evidence':evidence,'round2_blank':not bool(new['respuesta']),'round2_unsolicited_action':new_unsolicited})
        lines.append(f"| {r['id']} | {category} | {evidence} | {status} |")
    lines += ['', '### Fallos nuevos y regresiones por frase','']
    for m,d in rows.items():
        failures=[f"#{r['id']} s{r['semilla']}" for r in d['cases'] if not complete_round2(r)]
        oldmap={(r['id'],r['semilla']):r for r in older[m]['cases']}
        regress=[f"#{r['id']} s{r['semilla']}" for r in d['cases'] if complete_round2(oldmap[r['id'],r['semilla']]) and not complete_round2(r)]
        lines += [f"- {LABELS[m]}: fallos {', '.join(failures) or 'ninguno'}; nuevas regresiones {', '.join(regress) or 'ninguna'}."]
    lines += ['', '| Fallo nuevo de Qwen | Herramientas ejecutadas | Clasificación residual |','|---|---|---|']
    for r in rows['qwen_q5']['cases']:
        if complete_round2(r):continue
        if r.get('error'):
            residual='Entorno/ejecución: '+r['error'].split(':')[0]+'; causalidad no determinada'
        elif not r.get('respuesta'):
            residual='Protocolo de salida; respuesta final vacía'
        elif r['id'] in (29,30,31,34):
            residual='Prompt/planificación: falta una acción o su efecto requerido, pese a retirar el cierre rápido'
        elif r['id']==13 and r['herramientas']==['finalizar']:
            residual='Interpretación: pidió aclarar una frase ambigua; el criterio congelado exige bajar volumen. No prueba incapacidad.'
        elif r['id']==14:
            residual='Planificación/diagnóstico excesivo: no finalizó satisfactoriamente; las ventanas estáticas pueden alimentar el bucle.'
        elif r['id'] in (8,9,10) and 'enfocar_ventana' in r['herramientas'] and 'abrir_app' not in r['herramientas']:
            residual='Contrato del benchmark: enfocó una ventana existente en vez de abrir_app. No acredita la apertura requerida, aunque reutilizar una ventana puede ser útil en uso real.'
        elif r['id']==59 and r['herramientas']==['finalizar']:
            residual='Rechazo operativo residual: dijo que no podía guardar archivos y omitió Ctrl+S pese a disponer de teclado. No ejecutó una verificación.'
        elif r['id']==59:
            residual='Planificación/verificación: escritura o cierre de tarea no acreditados; los controles estáticos no reflejan el texto escrito.'
        elif r['id']==43 and r['herramientas']==['finalizar']:
            residual='Omisión operativa residual: afirmó traer Bloc de notas al frente sin ejecutar ninguna acción. No hay fallo de plantilla, pensamiento o JSON en esta observación.'
        elif r['id']==56:
            residual='Elección de herramienta: cerró la app, pero omitió el clic solicitado en X; no acredita el método pedido.'
        else:
            residual='Prompt/elección de herramienta o argumentos; capacidad intrínseca no demostrada'
        audit.append({'kind':'round2_failure','id':r['id'],'seed':r['semilla'],'category':residual,'tools':r['herramientas']})
        lines.append(f"| #{r['id']} s{r['semilla']} | {', '.join(r['herramientas'])} | {residual} |")
    lines += ['', '### Visión con el formato de cada familia','',
        'Gemma: box_2d [y_min,x_min,y_max,x_max], 0–1000, según '
        '[Google](https://ai.google.dev/gemma/docs/capabilities/vision/image). '
        'Qwen: point_2d [x,y], 0–1000, según el '
        '[cookbook Qwen3-VL](https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/spatial_understanding.ipynb). '
        'Este último es una referencia de su antecesor: no se encontró recomendación específica para Qwen3.5. '
        'El centro se convierte a píxeles ANTES de evaluar con los rectángulos verificados (errata del 7 descrita abajo). Mismas cinco tareas, '
        'capturas, presupuesto 1120 y semilla 11. No se hicieron clics.', '',
        '| Modelo | Formato | Aciertos | Pico VRAM texto / visión | Libre al pico texto / visión |','|---|---|---:|---:|---:|']
    for m,d in rows.items():
        v=visions[m]
        lines.append(f"| {LABELS[m]} | {'box_2d Y/X' if m.startswith('gemma') else 'point_2d X/Y'} | {sum(r['hit'] for r in v['vision'])}/5 | {d['gpu_peak_mib']/1024:.2f} / {v['gpu_peak_mib']/1024:.2f} GiB | {d['gpu_min_free_mib']/1024:.2f} / {v['gpu_min_free_mib']/1024:.2f} GiB |")
    lines.append('')
    for m,v in visions.items():
        for r in v['vision']:
            content=r.get('response',{}).get('choices',[{'message':{'content':''}}])[0]['message']['content']
            lines.append(f"- {LABELS[m]}, tarea {r['id']}: `{content}` → {r.get('pixel_point')}; {'acierto' if r['hit'] else 'fallo'} ({r['seconds']:.2f} s).")
    corrected=[]
    rects={t['id']:t['rect'] for t in read(HERE/'vision.json')}
    for r in read(HERE/'evidencia_vision.json'):
        xy=r.get('pixel_point') or json.loads(r['response'])
        x0,y0,x1,y1=rects[r['id']]
        corrected.append({'model':r['model'],'normalized':r['normalized'],'id':r['id'],
            'pixel_point':xy,'rect':rects[r['id']],'hit_original':r['hit'],
            'hit_corrected':x0<=xy['x']<=x1 and y0<=xy['y']<=y1})
    (HERE/'reevaluacion_vision_referencia.json').write_text(json.dumps(corrected,indent=2),encoding='utf-8')
    lines += ['', '**Errata de la primera ronda:** el rectángulo del número 7 señalaba la tecla vecina xʸ. '
        'Se revisó directamente la captura y se corrigió antes de esta nueva tanda. Los objetivos y las '
        'respuestas no cambian. Se conserva arriba la puntuación publicada; este recálculo reemplaza '
        'su interpretación para visión. Detalle en [ronda2_vision_errata.md](comparacion_modelos/ronda2_vision_errata.md).', '',
        '| Referencia anterior | Píxeles recalculada | Normalizada recalculada |', '|---|---:|---:|']
    for m in ('gemma_q5','gemma_q4','qwen_q4','qwen_q5'):
        counts=[sum(r['hit_corrected'] for r in corrected if r['model']==m and r['normalized']==normalized) for normalized in (False,True)]
        lines.append(f"| {m} | {counts[0]}/5 | {counts[1]}/5 |")
    lines += ['', 'La VRAM incluye otras aplicaciones; no mide memoria exclusiva ni coexistencia con Qwen3-TTS. '
        'No se cambió el contexto para ganar espacio. En Gemma, el centro del número 7 quedó solo '
        '0,185 píxeles fuera del rectángulo verificado: cuenta como fallo bajo el criterio congelado. '
        'Cinco capturas no bastan para inferir capacidad visual general.', '',
        '### Evaluación humana pendiente y decisión','',
        '[Respuestas nuevas y anteriores mezcladas a ciegas](respuestas_integracion_ciegas.md), '
        '[clave separada](clave_integracion_modelos.md). Hay cuatro etiquetas constantes por pregunta '
        '(Gemma y Qwen, antes y después), sorteadas sin revelar la correspondencia. Puntuar claridad, '
        'corrección, naturalidad y brevedad de 1 a 5. Las respuestas se guardan sin editar.', '',
        ('Qwen cumple la parte automática; **queda pendiente tu español a ciegas antes de recomendar un cambio**.' if automatic else
         'Qwen **no pasa el criterio fijado** en esta ronda. Mantener la producción actual; los ajustes y sus límites quedan documentados.'), '',
        'Esta ronda actualiza la recomendación histórica de arriba. Gemma conserva mayor fiabilidad de tareas '
        'en este set. Qwen ofrece menor espera inicial, más tokens por segundo, mejor localización medida '
        'y mucho más margen para voz. Su media de tiempo por tarea fue ligeramente mayor por los pasos '
        'y bucles, así que más tok/s no significa que termine todos los pedidos antes. No se valida aquí '
        'Qwen3-TTS simultáneo ni se migra la producción.', '',
        '### Integridad y reproducción','',
        '- Prompt común SHA256: `'+rows['gemma_q5']['prompt_sha256']+'`.',
        '- Esquema común SHA256: `'+rows['gemma_q5']['integration']['schema_sha256']+'`.',
        '- Motor CUDA llama-cpp-python 0.3.36 en .venv-pruebas. Se vuelve a probar el respaldo después de top_k=1 '
        'en cada tanda; no se instaló otra versión.',
        '- Pruebas originales y criterios congelados: comparacion_modelos/ronda2_congelado.json. '
        'No se modificaron las frases ni herramientas.json de producción.',
        '- Secuencia: ejecutar ronda2.py tras los diagnósticos y luego resumir_ronda2.py. '
        'Datos crudos locales excluidos; evidencia sanitizada en comparacion_modelos/metricas_ronda2.json '
        'y auditoria_qwen_ronda2.json. Configuración y motor verificados con verificar.py.', '']
    target=ROOT/'resultados_comparacion_modelos.md'
    previous=target.read_text(encoding='utf-8').split(MARKER)[0]
    target.write_text(previous.rstrip()+'\n'+ '\n'.join(lines),encoding='utf-8')
    pilots=[]
    for folder in ('piloto_ronda2_v1','piloto_ronda2_v2','piloto_ronda2_v3'):
        for file in sorted((OLD/folder).glob('*.json')):
            d=read(file)
            if not d.get('cases'):continue
            pilots.append({'pilot':folder,'file':file.name,'model':d['model'],
                'cases':len(d['cases']),'credited':sum(complete_round2(r) for r in d['cases']),
                'conversation_count':len(d['conversation']),'prompt_sha256':d['prompt_sha256'],
                'included_in_acceptance':False})
    (HERE/'ronda2_pilotos.json').write_text(json.dumps(pilots,ensure_ascii=False,indent=2),encoding='utf-8')
    pilot3=read(OLD/'piloto_ronda2_v3/qwen_q5.json')
    control_failure=next(r for r in pilot3['cases'] if r['id']==14 and r['semilla']==22)
    audit.append({'kind':'integration_pilot_v3','id':14,'seed':22,
        'category':'Gramática / convertidor JSON-schema',
        'evidence':'La regla char admitía controles sin escapar; salto de línea literal dentro de pensamiento.',
        'error':control_failure['error'],
        'raw_content':control_failure['outputs'][-1]['choices'][0]['message']['content'],
        'included_in_acceptance':False})
    (HERE/'auditoria_qwen_ronda2.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    aggregate={m:{'stats':stats(d),'gpu_baseline':d['gpu_baseline'],'gpu_loaded':d['gpu_loaded'],
        'gpu_peak_mib':d['gpu_peak_mib'],'gpu_min_free_mib':d['gpu_min_free_mib'],
        'vision_peak_mib':visions[m]['gpu_peak_mib'],'vision_min_free_mib':visions[m]['gpu_min_free_mib'],
        'template_probe':d['template_probe'],'grammar_fallbacks':d['grammar_probe']['fallbacks'],
        'json_control_characters_excluded':d['integration']['json_control_characters_excluded'],
        'strict_char_rule':d['integration']['strict_char_rule'],
        'prompt_sha256':d['prompt_sha256'],'schema_sha256':d['integration']['schema_sha256']} for m,d in rows.items()}
    (HERE/'resumen_ronda2.json').write_text(json.dumps(aggregate,ensure_ascii=False,indent=2),encoding='utf-8')
    vision_evidence=[]
    for m,v in visions.items():
        for r in v['vision']:
            vision_evidence.append({'model':m,'id':r['id'],'task':r['task'],'width':r['width'],'height':r['height'],
                'response':r.get('response',{}).get('choices',[{'message':{'content':''}}])[0]['message']['content'],
                'pixel_point':r.get('pixel_point'),'hit':r['hit'],'seconds':r['seconds']})
    (HERE/'vision_ronda2.json').write_text(json.dumps(vision_evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    metrics=[]
    for m,d in rows.items():
        for r in d['cases']:
            metrics.append({'model':m,'id':r['id'],'seed':r['semilla'],'complete':complete_round2(r),
                'blank':not bool(r['respuesta']),'json':r['json_schema_ok'],'first':r['first_strict'],
                'first_action_s':r['first_action_s'],'wall_s':r['wall_s'],'tools':r['herramientas'],
                'tokens':r.get('tokens',0),'t_decode':r.get('t_decode',0),'t_sample':r.get('t_sample',0)})
    (HERE/'metricas_ronda2.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=1),encoding='utf-8')
    sources={m+' antes':older[m] for m in LABELS}|{m+' después':rows[m] for m in LABELS}
    keypath=ROOT/'clave_integracion_modelos.md'
    if keypath.exists():
        content=keypath.read_text(encoding='utf-8')
        key={letter:next(s for s in sources if f'- {letter}: {s}\n' in content) for letter in 'WXYZ'}
    else:
        shuffled=list(sources);random.SystemRandom().shuffle(shuffled);key=dict(zip('WXYZ',shuffled))
    blind=['# Español — comparación de integración a ciegas','','Cuatro variantes por pregunta. Puntúa claridad, corrección, naturalidad y brevedad de 1 a 5. No abrir la clave antes. Respuestas sin editar.','']
    for i in range(10):
        blind += [f'## Pregunta {i+1}','',sources[key['W']]['conversation'][i]['question'],'']
        for letter,source in key.items():
            blind += [f'### Respuesta {letter}','',sources[source]['conversation'][i]['respuesta'] or '[Sin respuesta]','','Claridad: __ /5 · Corrección: __ /5 · Naturalidad: __ /5 · Brevedad: __ /5','']
    (ROOT/'respuestas_integracion_ciegas.md').write_text('\n'.join(blind),encoding='utf-8')
    keypath.write_text('# Clave de integración — abrir después\n\n'+'\n'.join(f'- {letter}: {source}' for letter,source in key.items())+'\n',encoding='utf-8')
    print(json.dumps({'qwen':qs,'gemma':gs,'automatic_pass':automatic,'spanish':'pendiente'},ensure_ascii=False))

if __name__=='__main__':main()
