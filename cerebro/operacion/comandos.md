---
estado: verificado
verificado_commit: d95855d
verificado_fecha: 2026-10-11
fuentes: [evaluar_pruebas.py, iniciar_cacao.py, comparacion_modelos/ejecutar.py, crear_acceso_directo.ps1, voz.py, config.json, modelo.py]
---
# Comandos útiles

Ejecutar desde la raíz del repositorio. Todo usa el intérprete `.venv\Scripts\python` (en Git Bash:
`.venv/Scripts/python`).

## Sin modelo (seguros)

```
.venv\Scripts\python probar_protecciones_ejecucion.py
.venv\Scripts\python probar_modo_directo.py
.venv\Scripts\python probar_fase6.py            # o una sección: probar_fase6.py <seccion>
.venv\Scripts\python probar_fase7.py A          # solo A: sin argumentos abre la isla real (B)
cd comparacion_modelos & ..\.venv-pruebas\Scripts\python -m unittest probar_criterios probar_integracion
.venv\Scripts\python iniciar_cacao.py --simular
python -I cerebro/frescura.py                   # frescura del cerebro, solo lectura
```

Lista completa en [[suites]].

## Con modelo (GPU libre, sin juego y sin Cacao en marcha)

```
set SIN_REALES=1 & set CONFIRMAR=s & .venv\Scripts\python evaluar_pruebas.py 11 22 33
.venv\Scripts\python voz.py --medir 5
.venv\Scripts\python comparacion_modelos\ejecutar.py gemma_q5 --round3 [--swa-full false] [--test-set <json>]
```

`ejecutar.py` acepta `model` (ver `MODELS`), `--smoke`, `--vision-only`, `--round2`, `--round3`, `--diagnostic`,
`--server-url`, `--engine-tag`, `--swa-full` (roto desde eb5a9c4: busca una línea de `modelo.py` que cambió), `--test-set`
y `--salida DIR` (945fa17: carpeta nueva, sin sobrescribir rondas) ([[comparacion-modelos]]).

## Modelo activo (Gemma o Qwen)

En `config.json`, `"modelo_activo": "gemma"` o `"qwen9b"` y reiniciar Cacao ([[configuracion-vigente]]). Comprobar
sin cargar el modelo: `.venv\Scripts\python probar_carga_modelo.py`.

## Git

```
git status --short                 # resultados y datos están ignorados
git add -f resultados_<tema>.md    # publicar un informe sanitizado
git check-ignore -v <ruta>         # por qué se ignora algo
```

## Trucos del entorno (Windows)

- **Python con `-I`** (aislado) ignora `PYTHONIOENCODING`. Para imprimir tildes o símbolos en la consola cp1252, usa
  `sys.stdout.reconfigure(encoding="utf-8")` dentro del script.
- **Leer JSON con tildes:** abre siempre con `encoding="utf-8"`. Los JSON escritos por PowerShell traen BOM: usa
  `utf-8-sig`.
- **PowerShell 5.1:** no hay `&&`. Encadena con `; if ($?) { … }`.

## No ejecutar sin permiso

- `prueba_real.py` y `prueba_presencial_isla.py`;
- `crear_acceso_directo.ps1 -Inicio`;
- `grabar_*.py`;
- cualquier script que use el micrófono, los altavoces o las herramientas reales.
