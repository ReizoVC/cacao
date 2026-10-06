"""
Pruebas sin modelo de la actividad medida con entrada física y de los periodos dudosos:
  1. MonitorEntrada (reloj simulado): 10 min sin entrada física marcan 'inactivo' aunque GetLastInputInfo diga que hubo
     entrada; las teclas y el mouse inyectados (sin dispositivo) no reinician el contador; las teclas físicas, los
     clics y el movimiento real sí; la deriva del mouse no; los mandos siguen contando; sin Raw Input, respaldo;
  2. la reflexión (Vigilante y Guardia de deteccion.py) usa ese mismo contador;
  3. periodos_dudosos en una base temporal: el resumen diario, la actividad por hora (reflexión y sugerencias),
     hay_datos y los días ya resumidos dejan fuera las muestras dudosas, y no se borra ninguna fila;
  4. el monitor real (solo lectura): registra Raw Input de teclado y mouse.
Uso: .venv\\Scripts\\python probar_actividad_fisica.py
"""
import ast
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import deteccion
import entrada
import habitos

BASE = Path(__file__).parent
resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def avanzar(self, s):
        self.t += s


class FuenteFalsa:
    def bloqueada(self):
        return False

    def ventana_al_frente(self):
        return None  # sin ventana: la muestra es {"app": "-", ..., "estado"}


def estado(monitor):
    return habitos.tomar_muestra(FuenteFalsa(), None, None, monitor.segundos_sin_entrada())["estado"]


def monitor(reloj):
    m = entrada.MonitorEntrada(reloj=reloj)
    m.raw_teclado_ok = True
    return m


TECLADO, RATON = 0x1111, 0x2222  # hDevice de dispositivos físicos; 0 = inyectado


def pruebas_monitor():
    original = entrada.segundos_sin_teclado_ni_mouse
    entrada.segundos_sin_teclado_ni_mouse = lambda: 0.0  # GetLastInputInfo: "acaban de tocar el teclado"
    try:
        r = Reloj()
        m = monitor(r)
        r.avanzar(10 * 60)
        ok("10 min sin entrada física: 'inactivo' aunque GetLastInputInfo diga 0 s", estado(m) == "inactivo",
           f"{m.segundos_sin_entrada():.0f} s")

        r = Reloj()
        m = monitor(r)
        for _ in range(600):  # una tecla y un movimiento inyectados por segundo durante 10 min
            r.avanzar(1)
            m.procesar_teclado(0, 0)
            m.procesar_raton(0, 0, 0x0001, 300, 200)  # clic y movimiento grande, pero inyectados
        ok("entrada inyectada (teclas, clics y movimiento) no reinicia el contador", estado(m) == "inactivo"
           and m.inyectados == 1200, f"{m.segundos_sin_entrada():.0f} s, {m.inyectados} inyectados")

        m.procesar_teclado(TECLADO, 1)  # solo soltar
        ok("soltar una tecla no cuenta (solo la pulsación)", estado(m) == "inactivo")
        m.procesar_teclado(TECLADO, 0)
        ok("una tecla física reinicia el contador", m.segundos_sin_entrada() == 0 and estado(m) == "activo")

        r.avanzar(10 * 60)
        for _ in range(600):
            r.avanzar(1)
            m.procesar_raton(RATON, 0, 0, 2, -1)  # deriva del sensor: 3 cuentas por segundo
        ok("deriva del mouse (3 cuentas/s) durante 10 min: sigue 'inactivo'", estado(m) == "inactivo")
        m.procesar_raton(RATON, 0, 0, 40, 25)
        ok("movimiento físico real reinicia el contador", estado(m) == "activo")
        r.avanzar(700)
        m.procesar_raton(RATON, 0, 0x0001, 0, 0)
        ok("un clic físico reinicia el contador", estado(m) == "activo")
        r.avanzar(700)
        m.procesar_raton(RATON, 0, 0x0400, 0, 0)  # RI_MOUSE_WHEEL
        ok("la rueda física reinicia el contador", estado(m) == "activo")
        r.avanzar(700)
        ABS = 0x3333
        m.procesar_raton(ABS, entrada.MOUSE_MOVE_ABSOLUTE, 0, 30000, 30000)
        ok("mouse absoluto (tableta): la primera posición no cuenta", estado(m) == "inactivo")
        m.procesar_raton(ABS, entrada.MOUSE_MOVE_ABSOLUTE, 0, 36000, 30000)
        ok("mouse absoluto: un movimiento real cuenta", estado(m) == "activo")

        r.avanzar(700)
        m._registrar(("xinput", 0), {"botones": set(), "ejes": {}, "hat": None})
        m._registrar(("xinput", 0), {"botones": {1}, "ejes": {}, "hat": None})
        ok("un botón de mando sigue contando", estado(m) == "activo")

        r = Reloj()
        m = monitor(r)
        r.avanzar(30)
        ok("al arrancar cuenta desde ese momento", abs(m.segundos_sin_entrada() - 30) < 0.01)
        m.raw_teclado_ok = False
        ok("sin Raw Input de teclado y mouse, respaldo con GetLastInputInfo", m.segundos_sin_entrada() == 0.0)
    finally:
        entrada.segundos_sin_teclado_ni_mouse = original


def pruebas_reflexion():
    original = entrada.segundos_sin_teclado_ni_mouse
    entrada.segundos_sin_teclado_ni_mouse = lambda: 0.0
    try:
        r = Reloj()
        m = monitor(r)
        r.avanzar(15 * 60)
        sistema = deteccion.SistemaWindows(m)
        ok("reflexión: el sistema de la vigilancia usa el contador físico", sistema.segundos_sin_entrada() >= 900)
        cfg = {**habitos.MW["reflexion"], **habitos.MW, "gpu_ventana_s": 0}
        v = deteccion.Vigilante.__new__(deteccion.Vigilante)
        v.sistema, v.c = sistema, cfg
        v.juego_abierto = lambda: None
        v.audio_que_bloquea = lambda: None
        v.reloj, v.dormir = r, lambda s: r.avanzar(s)
        sistema.pantalla_completa = lambda: False
        sistema.uso_gpu = lambda: 0
        ok("reflexión: 15 min sin entrada física, puede empezar (GetLastInputInfo diría que no)",
           v.motivo_para_no_empezar(inactividad_min=10) is None, v.motivo_para_no_empezar(inactividad_min=10))
        m.procesar_teclado(0, 0)
        ok("reflexión: una tecla inyectada no la frena", v.motivo_para_no_empezar(inactividad_min=10) is None)
        m.procesar_teclado(TECLADO, 0)
        ok("reflexión: una tecla física sí", v.motivo_para_no_empezar(inactividad_min=10) == "actividad reciente")
    finally:
        entrada.segundos_sin_teclado_ni_mouse = original
    fuente = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
    ok("agente: la reflexión y el modo juego comparten el Vigilante con MonitorEntrada",
       "Vigilante(SistemaWindows(MonitorEntrada().iniciar())" in fuente and "ModoJuego(vigilante" in fuente)
    fuente = (BASE / "registro_habitos.py").read_text(encoding="utf-8")
    ok("registro de hábitos: usa MonitorEntrada.segundos_sin_entrada",
       "entrada.segundos_sin_entrada()" in fuente and "MonitorEntrada().iniciar()" in fuente)


def pruebas_dudosos():
    tmp = Path(tempfile.mkdtemp())
    ruta_original = habitos.RUTA
    habitos.RUTA = tmp / "habitos_prueba.db"
    try:
        dia1, dia2, dia3 = datetime(2026, 10, 3), datetime(2026, 10, 4), datetime(2026, 10, 5)
        for dia in (dia1, dia2, dia3):
            for minuto in range(0, 120, 1):  # 2 h de 09:00 a 11:00, una muestra por minuto (dos de 30 s)
                for s in (0, 30):
                    habitos.guardar_muestra(dia.replace(hour=9) + timedelta(minutes=minuto, seconds=s),
                                            {"app": "code.exe", "categoria": "desarrollo", "estado": "activo"})

        class Clasif:
            def nombre(self, app):
                return app

        habitos.resumir_dias(dia2, Clasif())  # dia1 ya resumido antes de marcar
        antes = habitos.resumen_dias(dia1, dia2)
        ok("dudosos: antes de marcar, el día 1 tiene su resumen", len(antes) == 1 and antes[0][4] == 120)
        periodo, n = habitos.marcar_dudoso(dia1, dia2.replace(hour=10), "GetLastInputInfo no fiable")
        ok("dudosos: el periodo cuenta sus muestras", n == 240 + 120, n)
        ok("dudosos: el día 1 (ya resumido) deja de usarse", habitos.resumen_dias(dia1, dia2) == [])
        habitos.resumir_dias(dia3 + timedelta(days=1), Clasif())
        r2 = habitos.resumen_dias(dia2, dia3)
        ok("dudosos: el día 2 se resume solo con lo fiable (10:00-11:00 = 60 min)",
           len(r2) == 1 and r2[0][4] == 60 and r2[0][5] == "10:00", r2)
        act = habitos.actividad_por_hora(dia1, dia3 + timedelta(days=1))
        ok("dudosos: la actividad por hora (reflexión y sugerencias) no tiene las horas dudosas",
           (dia1.strftime("%Y-%m-%d"), 9, "code.exe") not in act and (dia2.strftime("%Y-%m-%d"), 9, "code.exe") not in act
           and act.get((dia2.strftime("%Y-%m-%d"), 10, "code.exe")) == 60
           and act.get((dia3.strftime("%Y-%m-%d"), 9, "code.exe")) == 60, sorted(act.items())[:4])
        ok("dudosos: hay_datos no ve datos fiables en el día 1 (no habrá reflexión de ese día)",
           not habitos.hay_datos(dia1, dia2) and habitos.hay_datos(dia3, dia3 + timedelta(days=1)))
        with sqlite3.connect(habitos.RUTA) as con:
            filas = con.execute("SELECT COUNT(*) FROM muestras").fetchone()[0]
            resumen = con.execute("SELECT COUNT(*) FROM resumen_diario WHERE dia = ?", ("2026-10-03",)).fetchone()[0]
        ok("dudosos: no se borra ninguna muestra ni el resumen antiguo", filas == 3 * 240 and resumen == 1,
           f"{filas} muestras")
        ok("dudosos: periodos_dudosos guarda desde, hasta y motivo",
           habitos.periodos_dudosos()[0][1:4] == ("2026-10-03 00:00:00", "2026-10-04 10:00:00",
                                                  "GetLastInputInfo no fiable"))
        arbol = ast.parse((BASE / "sugerencias.py").read_text(encoding="utf-8"))
        ok("sugerencias: no lee muestras directamente (usa actividad_por_hora)",
           "FROM muestras" not in ast.unparse(arbol))
    finally:
        habitos.RUTA = ruta_original


def prueba_real():
    m = entrada.MonitorEntrada().iniciar()
    limite = time.monotonic() + 5
    while not (m.raw_teclado_ok and m.rawinput_ok) and time.monotonic() < limite:
        time.sleep(0.05)
    time.sleep(1)
    ok("monitor real: Raw Input de teclado y mouse registrado (solo lectura)", m.raw_teclado_ok,
       f"teclado/mouse={m.raw_teclado_ok} mandos={m.rawinput_ok} sin entrada física {m.segundos_sin_entrada():.1f} s, "
       f"GetLastInputInfo {entrada.segundos_sin_teclado_ni_mouse():.1f} s")
    m.cerrar()


if __name__ == "__main__":
    for parte in (pruebas_monitor, pruebas_reflexion, pruebas_dudosos, prueba_real):
        print(f"\n== {parte.__name__} ==", flush=True)
        parte()
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
