"""
Prueba de la hipótesis de swa_full (backlog #5): con swa_full=false, ¿reutilizar el prefijo de la caché KV entre
tareas rompe al agente? No toca config.json ni modelo.py: pasa swa_full al crear el modelo.

Mismo bucle y herramientas simuladas que evaluar_pruebas.py (benchmark_gramatica.py, SIN_REALES=1, CONFIRMAR=s),
los 7 casos que fallaron en la semilla 11 (#26, #28, #31, #32, #33, #38 y #42), en ese orden, tras el mismo
calentamiento ("hola", semilla 1). Brazos:
  A: swa_full=false, sin vaciar la caché entre casos (producción hasta 397d0a2);
  B: swa_full=false, con llm.reset() y _ctx.kv_cache_clear() antes de cada caso (como ejecutar.py);
  C: swa_full por defecto, sin vaciar (producción restaurada; control).
Cada brazo corre en su propio proceso (un modelo cargado por brazo). Sin argumentos corre A, B y C.
Uso: .venv\\Scripts\\python comparacion_modelos\\probar_swa_cache.py [A|B|C ...]
Salida: comparacion_modelos/datos/swa_cache/brazo_<X>.json (ignorado por Git).
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SALIDA = ROOT / "comparacion_modelos" / "datos" / "swa_cache"
CASOS = [26, 28, 31, 32, 33, 38, 42]
SEMILLA = 11
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


def brazo(nombre):
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
    pruebas = {p["id"]: p for p in json.loads((ROOT / "pruebas.json").read_text(encoding="utf-8"))["pruebas"]}
    pico = PicoVRAM()
    pico.start()
    b.correr(ev.MODO, 1, "hola")  # el mismo calentamiento que evaluar_pruebas.py
    filas = []
    for i in CASOS:
        t = time.perf_counter()
        if vaciar:
            b.llm.reset()
            b.llm._ctx.kv_cache_clear()
        r = ev.evaluar(pruebas[i], SEMILLA)
        filas.append({"id": i, "frase": r["frase"], "usadas": r["usadas"], "argumentos": r["argumentos"],
                      "primera_ok": r["primera_ok"], "tarea_ok": r["tarea_ok"], "error": r["error"],
                      "respuesta": r["respuesta"], "segundos": round(time.perf_counter() - t, 2),
                      "t_modelo": round(r["tiempo"], 2)})
        print(f"{nombre} #{i:2} {'OK ' if r['tarea_ok'] else 'MAL'} {r['usadas']} {filas[-1]['segundos']} s "
              f"{r['error'] or ''}", flush=True)
    pico.parar.set()
    pico.join()
    resumen = {"brazo": nombre, "swa_full": swa_full, "vaciar": vaciar, "semilla": SEMILLA,
               "aciertos": sum(f["tarea_ok"] for f in filas), "casos": len(filas),
               "segundos_total": round(sum(f["segundos"] for f in filas), 1),
               "vram_base_mib": base_vram, "vram_cargado_mib": cargado_vram, "vram_pico_mib": pico.pico,
               "filas": filas}
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / f"brazo_{nombre}.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{nombre}: {resumen['aciertos']}/{resumen['casos']}, {resumen['segundos_total']} s, "
          f"VRAM {base_vram} → {cargado_vram} (pico {pico.pico}) MiB", flush=True)


if __name__ == "__main__":
    if os.environ.get("_BRAZO_HIJO") in BRAZOS:  # sin argumentos: evaluar_pruebas y benchmark leen sys.argv
        brazo(os.environ["_BRAZO_HIJO"])
    else:
        from guardia_juego import exigir_gpu_libre
        for nombre in sys.argv[1:] or list(BRAZOS):
            exigir_gpu_libre(f"el brazo {nombre}")
            subprocess.run([sys.executable, __file__], check=True,
                           env={**os.environ, "_BRAZO_HIJO": nombre, "PYTHONIOENCODING": "utf-8"})
