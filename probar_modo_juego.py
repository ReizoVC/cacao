"""
Modo juego: pruebas de la lógica con juego SIMULADO (sin modelo) y, con --medir, cuánto tarda en descargar y recargar
Gemma (+ visión) y Whisper de verdad, con el mismo juego simulado. No abre ningún juego ni toca nada del PC: el
"juego" es una lista de procesos falsa.
Uso: .venv\\Scripts\\python probar_modo_juego.py [--medir | --medir-whisper]
"""
import ast
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import deteccion
import habitos
import simular_habitos as sim
from modo_juego import JUEGO, NORMAL, ModoJuego
from probar_fase6 import SistemaFalso, STEAM_BANDEJA

BASE = Path(__file__).parent
resultados = []
WALLPAPER = r"D:\Steam\steamapps\common\wallpaper_engine\wallpaper64.exe"


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


def vigilante_falso(procesos):
    sistema = SistemaFalso(lambda: 0.0, procesos=procesos)
    return deteccion.Vigilante(sistema, habitos.Clasificador(sim.CATEGORIAS_SIM), habitos.MW), sistema


def pruebas_logica():
    v, s = vigilante_falso(STEAM_BANDEJA + [WALLPAPER])
    llamadas = []
    cerrojo = threading.Lock()
    paradas = []
    m = ModoJuego(v, cerrojo, lambda: llamadas.append("descargar"), lambda: llamadas.append("cargar"),
                  parar_reflexion=lambda: paradas.append(1), confirmar=2, anotar=lambda *_: None)
    for _ in range(3):
        m.comprobar()
    ok("Steam en la bandeja y Wallpaper Engine no son juego", m.estado == NORMAL and not llamadas)
    s.procesos.append(sim.V["hades"][0])
    m.comprobar()
    ok("una sola comprobación con juego no basta (evita parpadeos)", m.estado == NORMAL and not llamadas)
    m.comprobar()
    ok("dos seguidas: descarga, para la reflexión y queda en pausa", m.estado == JUEGO and llamadas == ["descargar"]
       and paradas and m.en_pausa() == "Hades", m.en_pausa())
    ok("mensaje de pausa con el nombre del juego", "Hades" in m.mensaje() and "pausa" in m.mensaje())
    s.procesos.remove(sim.V["hades"][0])
    m.comprobar()
    s.procesos.append(sim.V["hades"][0])  # el juego se reinicia: no recarga
    m.comprobar()
    s.procesos.remove(sim.V["hades"][0])
    m.comprobar()
    ok("un reinicio del juego no provoca recarga", m.estado == JUEGO and llamadas == ["descargar"])
    m.comprobar()
    ok("dos seguidas sin juego: recarga y vuelve a normal", m.estado == NORMAL and llamadas == ["descargar", "cargar"]
       and m.en_pausa() is None)
    ok("tiempos registrados", [t["accion"] for t in m.tiempos] == ["descargar", "cargar"])

    # no descarga a mitad de un pedido: espera al cerrojo
    s.procesos.append(sim.V["hades"][0])
    cerrojo.acquire()
    hilo = threading.Thread(target=lambda: (m.comprobar(), m.comprobar()))
    hilo.start()
    time.sleep(0.3)
    a_mitad = list(llamadas)
    cerrojo.release()
    hilo.join(2)
    ok("con un pedido en curso, espera a que termine para descargar", a_mitad == ["descargar", "cargar"]
       and llamadas[-1] == "descargar")

    # si la recarga falla, sigue en pausa y lo reintenta
    s.procesos.remove(sim.V["hades"][0])
    fallos = {"n": 1}

    def cargar_que_falla():
        if fallos["n"]:
            fallos["n"] -= 1
            raise RuntimeError("CUDA ocupada")
        llamadas.append("cargar")

    m.cargar = cargar_que_falla
    m.comprobar()
    try:
        m.comprobar()
    except RuntimeError:
        pass
    ok("recarga fallida: sigue en pausa", m.estado == JUEGO)
    m.comprobar()
    m.comprobar()
    ok("y la reintenta después", m.estado == NORMAL and llamadas[-1] == "cargar")

    # el agente: un pedido en pausa no llega al modelo
    arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
    nodo = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "atender_con_memoria")
    usado = []

    class PlanFalso:
        def pedido(self):
            usado.append("pedido")
            raise AssertionError("no debía tocar el modelo")

    ns = {"_modo_juego": type("M", (), {"en_pausa": lambda self: "Hades",
                                        "mensaje": lambda self: "Estoy en pausa porque Hades está abierto"})()}
    exec(compile(ast.Module(body=[nodo], type_ignores=[]), "agente_minimo.py", "exec"), ns)
    r = ns["atender_con_memoria"]("pon el volumen al 30", [], PlanFalso())
    ok("pedido en modo juego: aviso de pausa sin llamar al modelo", "pausa" in r and not usado, r)


def vram_mb():
    try:
        salida = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
        return int(salida.split()[0])
    except (OSError, ValueError, IndexError):
        return None


def medir_gemma(ciclos=2):
    """Gemma + mmproj de verdad, juego simulado: VRAM y tiempos de descarga y recarga."""
    from modelo import cargar_config, crear_llm
    from vision import ManejadorVision
    config = cargar_config()
    base = vram_mb()
    t0 = time.perf_counter()
    estado = {"llm": crear_llm(config)}
    carga_inicial = time.perf_counter() - t0
    vision = ManejadorVision(config["mmproj"])
    vision._init_mtmd_context(estado["llm"])  # como tras la primera captura: el mmproj también en la GPU
    estado["llm"].create_chat_completion(messages=[{"role": "user", "content": "hola"}], max_tokens=1)
    cargada = vram_mb()

    def descargar():
        vision.cerrar()
        vision.verbose = False
        estado["llm"].close()
        estado["llm"] = None
        import gc
        gc.collect()

    def cargar():
        estado["llm"] = crear_llm(config)
        vision._init_mtmd_context(estado["llm"])

    v, s = vigilante_falso(STEAM_BANDEJA)
    m = ModoJuego(v, threading.Lock(), descargar, cargar, confirmar=2, anotar=print)
    filas = []
    for ciclo in range(ciclos):
        s.procesos.append(sim.V["hades"][0])
        m.comprobar()
        m.comprobar()
        time.sleep(2)
        descargada = vram_mb()
        s.procesos.remove(sim.V["hades"][0])
        m.comprobar()
        m.comprobar()
        r = estado["llm"].create_chat_completion(messages=[{"role": "user", "content": "di hola"}], max_tokens=5)
        filas.append({"ciclo": ciclo + 1, "descargar_s": m.tiempos[-2]["segundos"], "cargar_s": m.tiempos[-1]["segundos"],
                      "vram_con_modelo_mb": cargada, "vram_en_juego_mb": descargada, "vram_tras_recargar_mb": vram_mb(),
                      "responde_tras_recargar": bool(r["choices"][0]["message"]["content"])})
        print(json.dumps(filas[-1]), flush=True)
    return {"vram_sin_modelo_mb": base, "carga_inicial_s": round(carga_inicial, 2), "ciclos": filas}


def medir_whisper(ciclos=2):
    from transcripcion import TranscriptorWhisper
    base = vram_mb()
    t0 = time.perf_counter()
    t = TranscriptorWhisper()
    carga_inicial = time.perf_counter() - t0
    cargada = vram_mb()
    filas = []
    for ciclo in range(ciclos):
        t0 = time.perf_counter()
        t.descargar()
        d = time.perf_counter() - t0
        time.sleep(1)
        descargada = vram_mb()
        t0 = time.perf_counter()
        t.cargar()
        c = time.perf_counter() - t0
        filas.append({"ciclo": ciclo + 1, "descargar_s": round(d, 2), "cargar_s": round(c, 2), "vram_cargado_mb": cargada,
                      "vram_descargado_mb": descargada})
        print(json.dumps(filas[-1]), flush=True)
    return {"vram_sin_whisper_mb": base, "carga_inicial_s": round(carga_inicial, 2), "ciclos": filas}


if __name__ == "__main__":
    if "--medir" in sys.argv:
        r = medir_gemma()
        (BASE / "resultados_modo_juego_gemma.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    elif "--medir-whisper" in sys.argv:
        r = medir_whisper()
        (BASE / "resultados_modo_juego_whisper.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    else:
        pruebas_logica()
        fallos = [x for x in resultados if not x[1]]
        print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
