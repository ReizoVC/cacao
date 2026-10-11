"""
Tokens del prompt de sistema por partes, con el tokenizador del modelo de cada perfil, cargado con vocab_only (solo el
vocabulario: sin pesos ni capas en la GPU, como probar_gramatica_json.py). No cambia producción.

Partes: reglas generales (las líneas antes de «Herramientas disponibles:»), el ejemplo de mensaje_final, cada
herramienta (descripción + esquema de parámetros, como la escribe prompt_sistema), el contrato de la ronda 2 (RULES,
solo qwen9b), MODO_VOZ y el total con la plantilla de chat (system + un pedido corto). La memoria y la wiki van a
rutas temporales vacías: el prompt no lleva datos personales (en producción pueden sumar algo más).

Uso: .venv\\Scripts\\python comparacion_modelos\\medir_prompt.py [--perfil gemma|qwen9b ...] [--guardar]
Salida: tabla en pantalla y, con --guardar, comparacion_modelos/datos/prompt_tokens_<fecha>.json (ignorado por Git).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hijo(perfil):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    import modelo
    _aplicar = modelo.aplicar_perfil
    modelo.aplicar_perfil = lambda config: _aplicar({**config, "modelo_activo": perfil})
    import agente_minimo as a
    temporal = Path(tempfile.mkdtemp(prefix="cacao_prompt_"))
    a.memoria.RUTA, a.wiki.VAULT = temporal / "memoria.db", temporal / "wiki"
    from llama_cpp import Llama
    llm = Llama(model_path=str(a.CONFIG["modelo"]), vocab_only=True, verbose=False)

    def n(texto):
        return len(llm.tokenize(texto.encode("utf-8"), add_bos=False, special=False))

    prompt = a.prompt_sistema()
    lineas = prompt.split("\n")
    corte = lineas.index("Herramientas disponibles:")
    reglas = [l for l in lineas[:corte] if not l.startswith("Ejemplo para 'baja un poco")]
    ejemplo = [l for l in lineas[:corte] if l.startswith("Ejemplo para 'baja un poco")]
    herramientas = {}
    for linea in lineas[corte + 1:]:
        if linea.startswith("- ") and ":" in linea:
            nombre = linea[2:].split(":", 1)[0]
            if nombre in a.HERRAMIENTAS:
                herramientas[nombre] = n(linea)
    rules = getattr(sys.modules.get("contrato_ronda2"), "RULES", "") if a.CONFIG.get("contrato_ronda2") else ""
    mensajes = [{"role": "system", "content": prompt}, {"role": "user", "content": "pon el volumen al 30"}]
    plantilla = None
    try:  # la plantilla del propio modelo (como modelo.manejador_sin_pensamiento o el formato por defecto)
        from llama_cpp.llama_chat_format import Jinja2ChatFormatter
        prefijo = modelo.SIN_PENSAMIENTO if a.CONFIG.get("sin_pensamiento") else ""
        f = Jinja2ChatFormatter(template=prefijo + llm.metadata["tokenizer.chat_template"],
                                eos_token=llm.detokenize([llm.token_eos()], special=True).decode(),
                                bos_token=llm.detokenize([llm.token_bos()], special=True).decode())
        plantilla = len(llm.tokenize(f(messages=mensajes).prompt.encode("utf-8"), add_bos=False, special=True))
    except Exception as e:  # se informa sin inventar la cifra
        plantilla = f"no medido: {type(e).__name__}"
    print("FILA " + json.dumps({
        "perfil": perfil, "modelo": Path(a.CONFIG["modelo"]).name, "contrato_ronda2": bool(a.CONFIG.get("contrato_ronda2")),
        "total_prompt_sistema": n(prompt), "total_con_voz": n(a.prompt_sistema(voz=True)),
        "reglas": n("\n".join(reglas)), "ejemplo_mensaje_final": n("\n".join(ejemplo)) if ejemplo else 0,
        "contrato_rules": n(rules) if rules else 0, "modo_voz": n(a.MODO_VOZ),
        "herramientas_total": sum(herramientas.values()), "herramientas": herramientas,
        "con_plantilla_y_pedido": plantilla}, ensure_ascii=False))


def main():
    if os.environ.get("_PERFIL_HIJO"):
        return hijo(os.environ["_PERFIL_HIJO"])
    args = sys.argv[1:]
    guardar = "--guardar" in args
    perfiles = [args[i + 1] for i, x in enumerate(args) if x == "--perfil"] or ["gemma", "qwen9b"]
    filas = []
    for perfil in perfiles:
        r = subprocess.run([sys.executable, __file__], capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ, "_PERFIL_HIJO": perfil, "PYTHONIOENCODING": "utf-8"})
        linea = next((l for l in r.stdout.splitlines() if l.startswith("FILA ")), None)
        filas.append(json.loads(linea[5:]) if linea else {"perfil": perfil, "error": r.stderr[-1500:]})
    for f in filas:
        if "error" in f:
            print(f["perfil"], "ERROR", f["error"])
            continue
        print(f"\n{f['perfil']} ({f['modelo']}): prompt de sistema {f['total_prompt_sistema']} tokens "
              f"(voz {f['total_con_voz']}); con plantilla y un pedido corto: {f['con_plantilla_y_pedido']}")
        print(f"  reglas {f['reglas']} · ejemplo de mensaje_final {f['ejemplo_mensaje_final']} · contrato RULES "
              f"{f['contrato_rules']} · MODO_VOZ {f['modo_voz']} · herramientas {f['herramientas_total']}")
        for nombre, t in sorted(f["herramientas"].items(), key=lambda x: -x[1]):
            print(f"    {nombre:22} {t:5}")
    if guardar:
        destino = ROOT / "comparacion_modelos" / "datos" / f"prompt_tokens_{time.strftime('%Y-%m-%d_%H%M')}.json"
        if destino.exists():
            raise SystemExit(f"{destino} ya existe: no lo sobrescribo.")
        destino.write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nGuardado en {destino}")


if __name__ == "__main__":
    main()
