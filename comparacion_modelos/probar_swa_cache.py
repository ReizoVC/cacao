"""
Prueba de la hipótesis de swa_full (backlog #5): con swa_full=false, ¿reutilizar el prefijo de la caché KV entre
tareas rompe al agente? No toca config.json ni modelo.py: pasa swa_full al crear el modelo.

Mismo bucle y herramientas simuladas que evaluar_pruebas.py (benchmark_gramatica.py, SIN_REALES=1, CONFIRMAR=s) y el
mismo calentamiento ("hola", semilla 1). Brazos:
  A: swa_full=false, sin vaciar la caché entre casos (producción hasta 397d0a2);
  B: swa_full=false, con llm.reset() y _ctx.kv_cache_clear() antes de cada caso (como ejecutar.py);
  C: swa_full por defecto, sin vaciar (producción restaurada; control).
Registro por llamada al modelo (envoltorio de llm.generate, sin cambiar producción): tokens ya en la caché
(n_previo), tokens del prompt, prefijo común, tokens reutilizados (0 si kv_cache_seq_rm no aceptó el recorte).

Uso: .venv\\Scripts\\python comparacion_modelos\\probar_swa_cache.py [A B C] [--casos fallidos|1-42|todos]
     [--semillas 11 22 33] [--nombre etiqueta]
Por defecto: A, B y C con los 7 casos que fallaron en la semilla 11 (#26, #28, #31, #32, #33, #38 y #42).
Cada brazo corre en su propio proceso. Salida en comparacion_modelos/datos/swa_cache/ (ignorado por Git):
  <etiqueta>_<brazo>.json (todo) y resumen_<etiqueta>_<brazo>.json (totales, fallos, tokens y comparación con
  resultados_pruebas_65_fecha.json).
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SALIDA = ROOT / "comparacion_modelos" / "datos" / "swa_cache"
FALLIDOS = [26, 28, 31, 32, 33, 38, 42]
BASE_65 = ROOT / "resultados_pruebas_65_fecha.json"
BRAZOS = {"A": (False, False), "B": (False, True), "C": (None, False)}  # (swa_full, vaciar antes de cada caso)


def vram_mib():
    return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, check=True).stdout.split()[0])


class PicoVRAM(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.pico, self.parar = 0, threading.Event()

    def run(self):
        while not self.parar.is_set():
            self.pico = max(self.pico, vram_mib())
            time.sleep(0.25)


def registrar_cache(llm, registro):
    """Envuelve llm.generate y _ctx.kv_cache_seq_rm para anotar cuánto de la caché anterior se reutiliza."""
    generar, recortar = llm.generate, llm._ctx.kv_cache_seq_rm

    def generate(tokens, *args, **kwargs):
        tokens = list(tokens)
        previo = llm._input_ids[:llm.n_tokens].tolist()
        prefijo = 0
        for x, y in zip(previo, tokens):
            if x != y:
                break
            prefijo += 1
        registro.append({"n_previo": len(previo), "prompt": len(tokens), "prefijo": prefijo,
                         "intento": prefijo - 1 if prefijo == len(tokens) else prefijo, "seq_rm_ok": None})
        yield from generar(tokens, *args, **kwargs)

    def kv_cache_seq_rm(*args):
        ok = recortar(*args)
        if registro and registro[-1]["seq_rm_ok"] is None:
            registro[-1]["seq_rm_ok"] = bool(ok)
        return ok

    llm.generate = generate
    llm._ctx.kv_cache_seq_rm = kv_cache_seq_rm


def reutilizados(llamada):
    return llamada["intento"] if llamada["seq_rm_ok"] and llamada["intento"] > 0 else 0


def brazo(nombre, casos, semillas, etiqueta):
    swa_full, vaciar = BRAZOS[nombre]
    os.environ.update(SIN_REALES="1", CONFIRMAR="s")
    os.chdir(ROOT)
    import modelo
    _cargar = modelo.cargar_config

    def cargar_config():
        config = {k: v for k, v in _cargar().items() if k != "swa_full"}
        if swa_full is not None:
            config["swa_full"] = swa_full
        return config

    modelo.cargar_config = cargar_config
    base_vram = vram_mib()
    import evaluar_pruebas as ev  # carga el modelo (benchmark_gramatica) con la configuración de este brazo
    b = ev.b
    cargado_vram = vram_mib()
    ventana = next((v for k, v in b.llm.metadata.items() if k.endswith("sliding_window")), None)
    registro = []
    registrar_cache(b.llm, registro)
    pruebas = {p["id"]: p for p in json.loads((ROOT / "pruebas.json").read_text(encoding="utf-8"))["pruebas"]}
    pico = PicoVRAM()
    pico.start()
    b.correr(ev.MODO, 1, "hola")  # el mismo calentamiento que evaluar_pruebas.py
    filas = []
    for semilla in semillas:
        for i in casos:
            t = time.perf_counter()
            if vaciar:
                b.llm.reset()
                b.llm._ctx.kv_cache_clear()
            registro.clear()
            r = ev.evaluar(pruebas[i], semilla)
            llamadas = list(registro)
            filas.append({"id": i, "semilla": semilla, "frase": r["frase"], "usadas": r["usadas"],
                          "argumentos": r["argumentos"], "primera_ok": r["primera_ok"], "tarea_ok": r["tarea_ok"],
                          "error": r["error"], "respuesta": r["respuesta"],
                          "segundos": round(time.perf_counter() - t, 2), "t_modelo": round(r["tiempo"], 2),
                          "llamadas": [{**c, "reutilizados": reutilizados(c)} for c in llamadas]})
            print(f"{nombre} s{semilla} #{i:2} {'OK ' if r['tarea_ok'] else 'MAL'} {r['usadas']} "
                  f"{filas[-1]['segundos']} s {r['error'] or ''}", flush=True)
    pico.parar.set()
    pico.join()
    SALIDA.mkdir(parents=True, exist_ok=True)
    comun = {"brazo": nombre, "swa_full": swa_full, "vaciar": vaciar, "semillas": semillas, "ventana_swa": ventana,
             "vram_base_mib": base_vram, "vram_cargado_mib": cargado_vram, "vram_pico_mib": pico.pico}
    (SALIDA / f"{etiqueta}_{nombre}.json").write_text(
        json.dumps({**comun, "filas": filas}, ensure_ascii=False, indent=1), encoding="utf-8")
    resumen = resumir(comun, filas)
    (SALIDA / f"resumen_{etiqueta}_{nombre}.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
    print(json.dumps({k: resumen[k] for k in ("por_semilla", "vram_pico_mib")}, ensure_ascii=False), flush=True)


def resumir(comun, filas):
    """Lo que hace falta leer: totales por semilla (también los de la base), fallos y una línea de tokens por caso."""
    base = {(r["id"], r["semilla"]): r for r in json.loads(BASE_65.read_text(encoding="utf-8"))}
    por_semilla = {}
    for s in comun["semillas"]:
        f = [x for x in filas if x["semilla"] == s]
        bs = [base[(x["id"], s)] for x in f if (x["id"], s) in base]
        por_semilla[s] = {"casos": len(f), "primera_ok": sum(x["primera_ok"] for x in f),
                          "tarea_ok": sum(x["tarea_ok"] for x in f),
                          "base_primera_ok": sum(x["primera_ok"] for x in bs), "base_tarea_ok": sum(x["tarea_ok"] for x in bs),
                          "segundos_media": round(statistics.mean(x["segundos"] for x in f), 2)}
    diferencias = []
    for x in filas:
        b = base.get((x["id"], x["semilla"]))
        if b and (b["tarea_ok"], b["primera_ok"]) != (x["tarea_ok"], x["primera_ok"]):
            diferencias.append({"id": x["id"], "semilla": x["semilla"], "frase": x["frase"],
                                "ahora": {"tarea_ok": x["tarea_ok"], "usadas": x["usadas"], "error": x["error"]},
                                "base": {"tarea_ok": b["tarea_ok"], "usadas": b["usadas"], "error": b["error"]}})
    tokens = []
    for x in filas:
        c = x["llamadas"][0] if x["llamadas"] else {}
        tokens.append({"id": x["id"], "semilla": x["semilla"], "ok": x["tarea_ok"],
                       "n_previo": c.get("n_previo"), "prompt": c.get("prompt"),
                       "reutilizados": c.get("reutilizados"), "seq_rm_ok": c.get("seq_rm_ok"),
                       "prompt_max": max((l["prompt"] for l in x["llamadas"]), default=None),
                       "llamadas": len(x["llamadas"])})
    return {**comun, "por_semilla": por_semilla, "diferencias_con_base": diferencias, "tokens_por_caso": tokens}


def casos_de(texto):
    if texto == "fallidos":
        return FALLIDOS
    ids = sorted(p["id"] for p in json.loads((ROOT / "pruebas.json").read_text(encoding="utf-8"))["pruebas"])
    if texto == "todos":
        return ids
    desde, hasta = map(int, texto.split("-"))
    return [i for i in ids if desde <= i <= hasta]


if __name__ == "__main__":
    if os.environ.get("_BRAZO_HIJO") in BRAZOS:  # sin argumentos: evaluar_pruebas y benchmark leen sys.argv
        opciones = json.loads(os.environ["_OPCIONES"])
        brazo(os.environ["_BRAZO_HIJO"], opciones["casos"], opciones["semillas"], opciones["etiqueta"])
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("brazos", nargs="*", help="A, B o C (por defecto, los tres)")
        parser.add_argument("--casos", default="fallidos")
        parser.add_argument("--semillas", nargs="+", type=int, default=[11])
        parser.add_argument("--nombre", default="brazo")
        args = parser.parse_args()
        opciones = {"casos": casos_de(args.casos), "semillas": args.semillas, "etiqueta": args.nombre}
        if set(args.brazos) - set(BRAZOS):
            parser.error(f"brazos válidos: {sorted(BRAZOS)}")
        from guardia_juego import exigir_gpu_libre
        for nombre in args.brazos or list(BRAZOS):
            exigir_gpu_libre(f"el brazo {nombre}")
            subprocess.run([sys.executable, __file__], check=True,
                           env={**os.environ, "_BRAZO_HIJO": nombre, "_OPCIONES": json.dumps(opciones),
                                "PYTHONIOENCODING": "utf-8"})
