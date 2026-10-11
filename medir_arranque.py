"""
Arranque de Cacao con la Fase 1 (carga perezosa, swa_full de config.json), sin micrófono, sin isla y sin
herramientas reales: todas las implementaciones se cambian por simuladas antes de cargar.

Mide como medir_ram.py (working set, memoria privada y RAM disponible del sistema, con psutil) y añade la VRAM total
de nvidia-smi (también el pico durante el pedido, muestreado cada 0,25 s). Comprueba:
  1. que importar agente_minimo no usa la GPU;
  2. que cargar_modelo() carga una vez y una segunda llamada devuelve el mismo objeto sin subir la VRAM;
  3. que responde a un pedido simulado ("pon el volumen al 30").
Uso: .venv\\Scripts\\python medir_arranque.py   -> resultados_arranque_fase1.json
"""
import gc
import json
import subprocess
import threading
import time
from pathlib import Path

import psutil

BASE = Path(__file__).parent
PEDIDO = "pon el volumen al 30"
proceso = psutil.Process()
filas = []


def vram_mib():
    salida = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                            capture_output=True, text=True, check=True).stdout
    return int(salida.split()[0])


def medir(etapa, **extra):
    gc.collect()
    m = proceso.memory_info()
    fila = {"etapa": etapa, "vram_mib": vram_mib(), "working_set_mb": round(m.rss / 2**20),
            "privada_mb": round(m.private / 2**20),
            "sistema_disponible_mb": round(psutil.virtual_memory().available / 2**20), **extra}
    filas.append(fila)
    print(json.dumps(fila, ensure_ascii=False), flush=True)


class PicoVRAM(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.pico, self.parar = 0, threading.Event()

    def run(self):
        while not self.parar.is_set():
            self.pico = max(self.pico, vram_mib())
            time.sleep(0.25)


medir("antes de importar")
import agente_minimo as a  # noqa: E402

llamadas = []


def simulada(nombre):
    def herramienta(**args):
        llamadas.append({"herramienta": nombre, "argumentos": args})
        if nombre == "volumen":  # la misma forma que volumen_sim de benchmark_gramatica.py
            return {"ok": True, "volumen_actual": args.get("cantidad", 50), "silenciado": False}
        return {"ok": True, "simulado": True}
    return herramienta


for nombre in list(a.IMPLEMENTACIONES):
    a.IMPLEMENTACIONES[nombre] = simulada(nombre)
a.confirmar = lambda *args, **kwargs: False  # nada pide confirmación aquí; si lo hiciera, es un no

medir("agente_minimo importado", llm_cargado=a.llm is not None)
t = time.perf_counter()
primero = a.cargar_modelo()
medir("modelo cargado", segundos=round(time.perf_counter() - t, 1),
      swa_full=a.CONFIG.get("swa_full"), use_mmap=a.CONFIG.get("use_mmap"))
t = time.perf_counter()
segundo = a.cargar_modelo()
medir("segunda llamada a cargar_modelo", segundos=round(time.perf_counter() - t, 3), mismo_objeto=primero is segundo)

pico = PicoVRAM()
pico.start()
historial = [{"role": "system", "content": a.prompt_sistema()}]
t = time.perf_counter()
respuesta = a.atender(PEDIDO, historial)
segundos = round(time.perf_counter() - t, 1)
pico.parar.set()
pico.join()
medir("pedido simulado", segundos=segundos, pico_vram_mib=pico.pico, respuesta=respuesta, llamadas=llamadas)

(BASE / "resultados_arranque_fase1.json").write_text(
    json.dumps({"pedido": PEDIDO, "filas": filas}, ensure_ascii=False, indent=1), encoding="utf-8")
