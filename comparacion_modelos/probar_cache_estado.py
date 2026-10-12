"""
Fase A: ¿la caché por estados del prompt de sistema (cache_estado.py) da las MISMAS salidas que sin caché?

Mismo arnés que probar_swa_cache.py (benchmark_gramatica con el código de producción, SIN_REALES=1, CONFIRMAR=s), con
el perfil indicado (por defecto qwen9b, sin tocar config.json), decodificación greedy (temperature 0) y semilla fija.
Dos brazos, cada uno en su propio proceso:
  sin: como hoy (Qwen recalcula todo el prompt en cada llamada);
  con: CacheEstado restaura el estado tras el prompt de sistema antes de cada llamada.
Guarda por llamada el texto generado y el tiempo; al final compara los dos brazos llamada a llamada.
Una sola diferencia = no vale.

Uso: .venv\\Scripts\\python comparacion_modelos\\probar_cache_estado.py [--casos 1-42] [--semilla 11] [--perfil qwen9b]
Salida: comparacion_modelos/datos/cache_estado/<perfil>_{sin,con}.json y comparacion_<perfil>.json (ignorado por Git).
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SALIDA = HERE / "datos" / "cache_estado"
sys.path.insert(0, str(HERE))


def vram_mib():
    return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, check=True).stdout.split()[0])


def brazo(nombre, casos, semilla, perfil):
    os.environ.update(SIN_REALES="1", CONFIRMAR="s")
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    import psutil

    import modelo
    _aplicar = modelo.aplicar_perfil
    modelo.aplicar_perfil = lambda config: _aplicar({**config, "modelo_activo": perfil})
    base_vram = vram_mib()
    import evaluar_pruebas as ev  # carga el modelo (benchmark_gramatica)
    b = ev.b
    b.ns["CAMINO_RAPIDO"] = False  # fase A mide solo el modelo: sin el camino rápido de la fase B
    # el pedido lleva la fecha y la hora (con_fecha): fija en los dos brazos, o los prompts no serían idénticos
    from datetime import datetime
    fecha_fija, con_fecha = datetime(2026, 10, 12, 10, 0), b.ns["con_fecha"]
    b.ns["con_fecha"] = lambda pedido, ahora=None: con_fecha(pedido, fecha_fija)
    cargado_vram = vram_mib()
    ram_antes = psutil.Process().memory_info().rss
    cache = None
    if nombre == "con":
        from cache_estado import CacheEstado
        cache = CacheEstado(b.llm, lambda: b.ns["prompt_sistema"]())
    llamadas = []
    llamar = b.llm.create_chat_completion

    def greedy(**kwargs):  # misma llamada, con temperature 0: el muestreador usa greedy
        t = time.perf_counter()
        r = llamar(**{**kwargs, "temperature": 0.0})
        llamadas.append({"texto": r["choices"][0]["message"]["content"],
                         "segundos": round(time.perf_counter() - t, 3)})
        return r

    b.llm.create_chat_completion = greedy
    pruebas = {p["id"]: p for p in json.loads((ROOT / "pruebas.json").read_text(encoding="utf-8"))["pruebas"]}
    b.correr(ev.MODO, 1, "hola")  # el mismo calentamiento que evaluar_pruebas.py
    filas = []
    for i in casos:
        llamadas.clear()
        t = time.perf_counter()
        r = ev.evaluar(pruebas[i], semilla)
        filas.append({"id": i, "semilla": semilla, "usadas": r["usadas"], "tarea_ok": r["tarea_ok"],
                      "error": r["error"], "segundos": round(time.perf_counter() - t, 2),
                      "t_modelo": round(r["tiempo"], 2), "llamadas": list(llamadas)})
        print(f"{nombre} #{i:2} {'OK ' if r['tarea_ok'] else 'MAL'} {r['usadas']} {filas[-1]['segundos']} s", flush=True)
    SALIDA.mkdir(parents=True, exist_ok=True)
    datos = {"brazo": nombre, "perfil": perfil, "semilla": semilla, "vram_base_mib": base_vram,
             "vram_cargado_mib": cargado_vram, "vram_final_mib": vram_mib(),
             "ram_rss_mb_antes_cache": round(ram_antes / 2**20), "ram_rss_mb_final": round(
                 psutil.Process().memory_info().rss / 2**20),
             "cache": cache.resumen() if cache else None, "filas": filas}
    (SALIDA / f"{perfil}_{nombre}.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def comparar(perfil):
    sin = json.loads((SALIDA / f"{perfil}_sin.json").read_text(encoding="utf-8"))
    con = json.loads((SALIDA / f"{perfil}_con.json").read_text(encoding="utf-8"))
    diferencias = []
    for a, b in zip(sin["filas"], con["filas"]):
        ta, tb = [x["texto"] for x in a["llamadas"]], [x["texto"] for x in b["llamadas"]]
        if ta != tb:
            k = next((j for j, (x, y) in enumerate(zip(ta, tb)) if x != y), min(len(ta), len(tb)))
            diferencias.append({"id": a["id"], "llamada": k, "sin": ta[k] if k < len(ta) else None,
                                "con": tb[k] if k < len(tb) else None})

    def media(filas, clave):
        return round(sum(f[clave] for f in filas) / len(filas), 3)

    def por_llamada(filas):
        xs = [x["segundos"] for f in filas for x in f["llamadas"]]
        return round(sum(xs) / len(xs), 3) if xs else None

    resultado = {"perfil": perfil, "casos": len(sin["filas"]), "identicas": not diferencias,
                 "diferencias": diferencias,
                 "segundos_por_llamada": {"sin": por_llamada(sin["filas"]), "con": por_llamada(con["filas"])},
                 "t_modelo_por_tarea": {"sin": media(sin["filas"], "t_modelo"), "con": media(con["filas"], "t_modelo")},
                 "segundos_por_tarea": {"sin": media(sin["filas"], "segundos"), "con": media(con["filas"], "segundos")},
                 "completas": {"sin": sum(f["tarea_ok"] for f in sin["filas"]),
                               "con": sum(f["tarea_ok"] for f in con["filas"])},
                 "vram_cargado_mib": {"sin": sin["vram_cargado_mib"], "con": con["vram_cargado_mib"]},
                 "vram_final_mib": {"sin": sin["vram_final_mib"], "con": con["vram_final_mib"]},
                 "ram_rss_mb": {"sin": sin["ram_rss_mb_final"], "con_antes": con["ram_rss_mb_antes_cache"],
                                "con_final": con["ram_rss_mb_final"]},
                 "cache": con["cache"]}
    (SALIDA / f"comparacion_{perfil}.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
    print(json.dumps({k: v for k, v in resultado.items() if k != "diferencias"}, ensure_ascii=False, indent=1))
    print(f"diferencias: {len(diferencias)}")
    for d in diferencias[:5]:
        print(json.dumps(d, ensure_ascii=False)[:600])


def main():
    if os.environ.get("_BRAZO_HIJO"):
        o = json.loads(os.environ["_OPCIONES"])
        return brazo(os.environ["_BRAZO_HIJO"], o["casos"], o["semilla"], o["perfil"])
    parser = argparse.ArgumentParser()
    parser.add_argument("--casos", default="1-42")
    parser.add_argument("--semilla", type=int, default=11)
    parser.add_argument("--perfil", default="qwen9b")
    parser.add_argument("--solo-comparar", action="store_true")
    args = parser.parse_args()
    if not args.solo_comparar:
        desde, hasta = map(int, args.casos.split("-"))
        ids = sorted(p["id"] for p in json.loads((ROOT / "pruebas.json").read_text(encoding="utf-8"))["pruebas"])
        opciones = {"casos": [i for i in ids if desde <= i <= hasta], "semilla": args.semilla, "perfil": args.perfil}
        sys.path.insert(0, str(ROOT))
        from guardia_juego import exigir_gpu_libre
        for nombre in ("sin", "con"):
            exigir_gpu_libre(f"el brazo {nombre}")
            subprocess.run([sys.executable, __file__], check=True,
                           env={**os.environ, "_BRAZO_HIJO": nombre, "_OPCIONES": json.dumps(opciones),
                                "PYTHONIOENCODING": "utf-8"})
    comparar(args.perfil)


if __name__ == "__main__":
    main()
