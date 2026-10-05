"""
Modo juego: pruebas de la lógica con juego SIMULADO (sin modelo) y, con --medir, cuánto tarda en descargar y recargar
Gemma (+ visión) y Whisper de verdad, con el mismo juego simulado. No abre ningún juego ni toca nada del PC: el
"juego" es una lista de procesos falsa, con ventanas y uso de GPU simulados y un reloj simulado.
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


class Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


HADES = sim.V["hades"][0]
ROBLOX = r"C:\Users\sim\AppData\Local\Roblox\Versions\version-1\RobloxPlayerBeta.exe"


def escenario(procesos=(), ventanas=(), gpu_proc=None):
    """Sistema falso con reloj simulado; el modo juego comprueba cada 5 s (avanzar() mueve el reloj)."""
    reloj = Reloj()
    s = SistemaFalso(reloj, procesos=STEAM_BANDEJA + [WALLPAPER] + list(procesos), ventanas=ventanas,
                     gpu_proc=gpu_proc)
    clasificador = habitos.Clasificador({**sim.CATEGORIAS_SIM, ROBLOX: {"nombre": "Roblox", "categoria": "juegos"}})
    v = deteccion.Vigilante(s, clasificador, habitos.MW, reloj=reloj)
    llamadas = []
    m = ModoJuego(v, threading.Lock(), lambda: llamadas.append("descargar"), lambda: llamadas.append("cargar"),
                  confirmar=2, anotar=lambda *_: None, reloj=reloj)

    def avanzar(segundos):
        """Avanza el reloj de 5 en 5 s, con una comprobación del modo juego en cada paso."""
        for _ in range(int(segundos // 5)):
            reloj.t += 5
            m.comprobar()

    return s, v, m, llamadas, avanzar, reloj


def vigilante_falso(procesos):  # para las mediciones: un juego con ventana visible
    s, v, m, _, avanzar, reloj = escenario(procesos)
    return v, s


def pruebas_logica():
    # 1. juego activo (ventana visible)
    s, v, m, llamadas, avanzar, reloj = escenario([HADES], ventanas=[HADES])
    avanzar(5)
    ok("activo: una sola comprobación no basta", m.estado == NORMAL and not llamadas)
    avanzar(5)
    ok("activo: con ventana visible entra en pausa a los 10 s", m.estado == JUEGO and llamadas == ["descargar"]
       and m.en_pausa() == "Hades", m.en_pausa())

    # 2. minimizado un momento: sin ventana ni GPU durante 90 s, luego vuelve
    s.ventanas = set()
    avanzar(90)
    ok("minimizado 90 s: sigue en pausa (margen de 2 min)", m.estado == JUEGO and llamadas == ["descargar"])
    s.ventanas = {HADES}
    avanzar(60)
    ok("vuelve a la ventana: sigue en pausa, sin recargas", m.estado == JUEGO and llamadas == ["descargar"])

    # 3. se cierra a la bandeja (el proceso sigue): termina tras 2 min sin señales
    s.ventanas = set()
    avanzar(115)
    ok("en la bandeja: aún en pausa a los 115 s", m.estado == JUEGO)
    avanzar(20)
    ok("en la bandeja: recarga tras 2 min sin ventana ni GPU", m.estado == NORMAL
       and llamadas == ["descargar", "cargar"], f"{reloj.t:.0f} s")
    ok("tiempos registrados", [t["accion"] for t in m.tiempos] == ["descargar", "cargar"])

    # 4. en la bandeja desde el principio (Roblox al cerrarlo): nunca es un juego activo
    s, v, m, llamadas, avanzar, _ = escenario([ROBLOX], ventanas=[])
    avanzar(300)
    ok("Roblox en la bandeja 5 min: nunca pausa", m.estado == NORMAL and not llamadas and v.juego_abierto() is None)

    # 5. GPU: sostenida sin ventana (minimizado pero renderizando) sí; un pico suelto no
    s, v, m, llamadas, avanzar, _ = escenario([HADES], ventanas=[], gpu_proc={HADES: 40})
    avanzar(30)
    ok("GPU sostenida sin ventana: juego activo", m.estado == JUEGO)
    s, v, m, llamadas, avanzar, _ = escenario([HADES], ventanas=[], gpu_proc={HADES: 0})
    avanzar(10)
    s.gpu_proc[HADES] = 60
    avanzar(5)
    s.gpu_proc[HADES] = 0
    avanzar(60)
    ok("un pico de GPU de 5 s: no es juego activo", m.estado == NORMAL and not llamadas)

    # 6. comandos "estoy jugando" / "ya terminé"
    s, v, m, llamadas, avanzar, _ = escenario()
    r = m.estoy_jugando()
    ok("'estoy jugando' sin juego detectado: pausa al momento", m.estado == JUEGO and llamadas == ["descargar"], r)
    avanzar(300)
    ok("forzado: sigue en pausa aunque no haya señales", m.estado == JUEGO)
    r = m.ya_termine()
    ok("'ya terminé': recarga al momento", m.estado == NORMAL and llamadas[-1] == "cargar", r)
    s, v, m, llamadas, avanzar, _ = escenario([ROBLOX], ventanas=[ROBLOX])
    avanzar(10)
    r = m.ya_termine()
    avanzar(60)
    ok("'ya terminé' con Roblox aún visible: se ignora ese proceso y no vuelve a pausar", m.estado == NORMAL
       and llamadas == ["descargar", "cargar"], r)
    s.reabrir(ROBLOX)  # lo cierra y lo vuelve a abrir: otro pid
    avanzar(10)
    ok("al volver a abrir el juego (otro proceso): pausa de nuevo", m.estado == JUEGO)

    # 7. la reflexión usa la misma detección
    s, v, m, _, avanzar, reloj = escenario([ROBLOX], ventanas=[])
    reloj.t = 1000
    v.dormir = lambda seg: setattr(reloj, "t", reloj.t + seg)
    ok("reflexión: Roblox en la bandeja no la bloquea", v.motivo_para_no_empezar() is None)
    s.ventanas = {ROBLOX}
    reloj.t += 10
    ok("reflexión: Roblox con ventana sí la bloquea", (v.motivo_para_no_empezar() or "").startswith("juego abierto"))

    # 8. la regla de mis pruebas (guardia_juego) también
    import guardia_juego
    for nombre, kw, esperado in [("en la bandeja", {"ventanas": []}, None),
                                 ("con ventana", {"ventanas": [ROBLOX]}, "Roblox"),
                                 ("GPU sostenida", {"ventanas": [], "gpu_proc": {ROBLOX: 50}}, "Roblox")]:
        reloj = Reloj()
        sistema = SistemaFalso(reloj, procesos=[ROBLOX], **kw)
        original = habitos.Clasificador
        habitos.Clasificador = lambda: original({ROBLOX: {"nombre": "Roblox", "categoria": "juegos"}})
        try:
            r = guardia_juego.juego_abierto(sistema, dormir=lambda seg: setattr(reloj, "t", reloj.t + seg), reloj=reloj)
        finally:
            habitos.Clasificador = original
        ok(f"regla de mis pruebas, Roblox {nombre}: {'bloquea' if esperado else 'no bloquea'}", r == esperado, r)

    # 9. el agente: comandos sin modelo y pedido en pausa
    arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
    nombres = {"atender_con_memoria", "comando_modo_juego", "FRASES_JUGANDO", "FRASES_TERMINE", "normalizar"}
    nodos = [n for n in arbol.body if (isinstance(n, ast.FunctionDef) and n.name in nombres)
             or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in nombres for t in n.targets))]
    usado = []

    class PlanFalso:
        def pedido(self):
            usado.append("pedido")
            raise AssertionError("no debía tocar el modelo")

    class ModoFalso:
        pausa = "Hades"

        def en_pausa(self):
            return self.pausa

        def mensaje(self):
            return "Estoy en pausa porque Hades está abierto"

        def estoy_jugando(self):
            self.pausa = "un juego"
            return "Vale, libero la GPU"

        def ya_termine(self):
            self.pausa = None
            return "Listo, ya volví"

    import unicodedata
    ns = {"_modo_juego": ModoFalso(), "unicodedata": unicodedata}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "agente_minimo.py", "exec"), ns)
    r = ns["atender_con_memoria"]("pon el volumen al 30", [], PlanFalso())
    ok("pedido en modo juego: aviso de pausa sin llamar al modelo", "pausa" in r and not usado, r)
    r = ns["atender_con_memoria"]("Ya terminé.", [], PlanFalso())
    ok("'Ya terminé.' lo atiende el código, sin el modelo", r == "Listo, ya volví" and not usado, r)
    r = ns["atender_con_memoria"]("estoy jugando", [], PlanFalso())
    ok("'estoy jugando' lo atiende el código", r.startswith("Vale") and not usado, r)


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

    s, v, _, _, _, reloj = escenario()
    m = ModoJuego(v, threading.Lock(), descargar, cargar, confirmar=2, anotar=print)
    filas = []
    for ciclo in range(ciclos):
        s.procs.append(HADES)  # juego simulado con ventana visible (SistemaFalso: todas visibles por defecto)
        for _ in range(2):
            reloj.t += 5
            m.comprobar()
        time.sleep(2)
        descargada = vram_mb()
        s.procs.remove(HADES)
        reloj.t += 125  # 2 min sin señales
        for _ in range(2):
            reloj.t += 5
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
