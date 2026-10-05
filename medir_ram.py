"""
Mide la RAM del proceso del agente tarea a tarea, con 6 tareas reales de solo lectura (las mismas de la prueba 3:
listar apps, ventanas y carpetas; no abre, cierra ni escribe nada).
Uso: .venv\\Scripts\\python medir_ram.py [mmap|nommap]   -> resultados_ram_<modo>.json
"""
import gc
import json
import sys
import time
import tracemalloc
from pathlib import Path

import psutil

import modelo

BASE = Path(__file__).parent
MODO = sys.argv[1] if len(sys.argv) > 1 else "mmap"
proceso = psutil.Process()
filas = []


def medir(etapa, **extra):
    gc.collect()
    m = proceso.memory_info()
    fila = {"etapa": etapa, "working_set_mb": round(m.rss / 2**20), "privada_mb": round(m.private / 2**20),
            "sistema_disponible_mb": round(psutil.virtual_memory().available / 2**20),
            "objetos_python": len(gc.get_objects()),
            "python_heap_mb": round(tracemalloc.get_traced_memory()[0] / 2**20, 1) if tracemalloc.is_tracing() else None,
            **extra}
    filas.append(fila)
    print(json.dumps(fila, ensure_ascii=False), flush=True)


medir("antes de cargar")
_cargar = modelo.cargar_config


def cargar_config():
    config = _cargar()
    config["use_mmap"] = MODO == "mmap"
    return config


modelo.cargar_config = cargar_config
import agente_minimo as a  # noqa: E402  (carga el modelo con el use_mmap elegido)

medir("modelo cargado")
TAREAS = ["revisa una por una mis apps de música, de juegos, de oficina y de desarrollo y dime cuántas hay "
          "de cada categoría",
          "lista las ventanas abiertas, luego los archivos de mis descargas y luego los de mi escritorio, "
          "y resúmeme todo"] * 3
tracemalloc.start(25)
base = tracemalloc.take_snapshot()
for i, tarea in enumerate(TAREAS, 1):
    historial = [{"role": "system", "content": a.prompt_sistema()}]
    t = time.perf_counter()
    respuesta = a.atender(tarea, historial)
    medir(f"tarea {i}", segundos=round(time.perf_counter() - t, 1), respuesta=respuesta[:80])
    if i == 1:
        tras_1 = tracemalloc.take_snapshot()
final = tracemalloc.take_snapshot()
crecimiento = [{"donde": str(s.traceback[0]), "kb": round(s.size_diff / 1024), "bloques": s.count_diff}
               for s in final.compare_to(tras_1, "traceback")[:8]]
print("Mayor crecimiento del heap de Python entre la tarea 1 y la 6:")
for c in crecimiento:
    print("  ", c)
(BASE / f"resultados_ram_{MODO}.json").write_text(
    json.dumps({"modo": MODO, "filas": filas, "crecimiento_python": crecimiento}, ensure_ascii=False, indent=1),
    encoding="utf-8")
