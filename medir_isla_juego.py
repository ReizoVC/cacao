"""
Mide cuánta GPU usa la isla (asistente-ui.exe y sus procesos de WebView2) con Cacao compacto despierto y en modo
juego (dormido, a pocos cuadros por segundo). Sin Cacao ni modelo: un servidor de prueba (ui_isla.ServidorIsla) hace
de agente y le manda el estado. Cierra Cacao antes (usa el puerto 8765 y el mismo ui.json).

Contadores de Windows "GPU Engine(pid_*)\\Utilization Percentage" (lo mismo que enseña el Administrador de tareas),
sumados para todos los motores de esos procesos, una muestra por segundo.

Uso: .venv\\Scripts\\python medir_isla_juego.py [segundos por fase, 20 por defecto]
     -> resultados_isla_juego.json
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

import ui_isla

BASE = Path(__file__).parent
EXE = Path(json.loads((BASE / "config.json").read_text(encoding="utf-8"))["ui"]["exe"])


def pids_isla(isla):
    """La isla y sus descendientes (msedgewebview2.exe, que pinta)."""
    try:
        p = psutil.Process(isla.pid)
        return {isla.pid} | {c.pid for c in p.children(recursive=True)}
    except psutil.Error:
        return {isla.pid}


def gpu_por_pid(segundos):
    """[{pid: % de GPU sumando motores}] una muestra por segundo, con typeperf (sin ventana)."""
    salida = subprocess.run(["typeperf", r"\GPU Engine(*)\Utilization Percentage", "-sc", str(segundos), "-si", "1"],
                            capture_output=True, text=True, timeout=segundos + 60,
                            creationflags=subprocess.CREATE_NO_WINDOW).stdout
    filas = [l for l in salida.splitlines() if l.startswith('"')]
    cabecera = [c.strip('"') for c in filas[0].split('","')]
    muestras = []
    for fila in filas[1:]:
        valores = [v.strip('"') for v in fila.split('","')]
        por_pid = {}
        for nombre, valor in zip(cabecera[1:], valores[1:]):
            if "pid_" not in nombre:
                continue
            pid = int(nombre.split("pid_")[1].split("_")[0])
            try:
                por_pid[pid] = por_pid.get(pid, 0.0) + float(valor or 0)
            except ValueError:
                pass
        muestras.append(por_pid)
    return muestras


def medir(isla, segundos):
    muestras = gpu_por_pid(segundos)
    pids = pids_isla(isla)
    serie = [sum(v for p, v in m.items() if p in pids) for m in muestras]
    return {"media_pct": round(sum(serie) / max(1, len(serie)), 3), "max_pct": round(max(serie or [0]), 3),
            "muestras": len(serie), "procesos": len(pids)}


def main():
    segundos = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    servidor = ui_isla.ServidorIsla().iniciar()
    isla = subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
    try:
        limite = time.time() + 30
        while not servidor.conectada and time.time() < limite:
            time.sleep(0.2)
        if not servidor.conectada:
            sys.exit("La isla no se conectó (¿Cacao sigue abierto?)")
        servidor.enviar({"tipo": "modos", "sin_confirmacion": False, "escucha": True, "seguimiento": True})
        time.sleep(4)  # el saludo de arranque termina y queda compacta
        servidor.estado("reposo")
        time.sleep(3)
        normal = medir(isla, segundos)
        servidor.estado("juego", "Estoy en pausa porque un juego está abierto")
        time.sleep(3)
        juego = medir(isla, segundos)
        servidor.estado("escuchando")
        time.sleep(1.5)
        servidor.estado("juego", "Estoy en pausa porque un juego está abierto")
        time.sleep(2)
        resultado = {"fecha": time.strftime("%Y-%m-%d %H:%M"), "segundos_por_fase": segundos,
                     "compacta_despierta": normal, "modo_juego": juego}
        (BASE / "resultados_isla_juego.json").write_text(json.dumps(resultado, indent=1), encoding="utf-8")
        print(json.dumps(resultado, indent=1))
    finally:
        isla.terminate()
        servidor.cerrar()


if __name__ == "__main__":
    main()
