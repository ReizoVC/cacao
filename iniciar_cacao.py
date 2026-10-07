"""
Arranque de Cacao sin ninguna ventana de terminal: lo lanza Cacao.lnk (y el acceso de Inicio) con pythonw.exe.

- Arranca el agente en modo voz (voz.py: isla, palabra «Cacao»…) con python.exe sin ventana (CREATE_NO_WINDOW): su
  consola existe pero no se ve, así que tampoco aparecen las de los PowerShell que lanza. Toda su salida (lo que
  antes se veía en la terminal, también los mensajes de llama.cpp y Whisper) va a registro_cacao.log; al pasar de
  5 MB se guarda el anterior en registro_cacao.1.log. Para verla: bandeja de la isla → «Ver terminal».
- Se queda esperando a que Cacao termine: si sale con un error (también si el proceso cae sin traza), avisa con una
  notificación de Windows y lo anota en el registro. «Salir de Cacao» (bandeja) es una salida normal: sin aviso.
- No abre un segundo Cacao si ya hay uno (avisa con una notificación).
- Con un juego activo, el agente espera a que se cierre antes de cargar Gemma y Whisper (ESPERAR_JUEGO=1).
- Sin permisos de administrador.

Uso: pythonw iniciar_cacao.py [--al-inicio]   (--al-inicio: espera 60 s tras iniciar sesión)
     python  iniciar_cacao.py --simular        (solo comprueba y dice lo que haría; no carga nada)
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import avisos_windows

BASE = Path(__file__).resolve().parent
PYTHON = BASE / ".venv" / "Scripts" / "python.exe"
SCRIPT = BASE / "voz.py"
REGISTRO = BASE / "registro_cacao.log"
MAX_REGISTRO = 5 * 1024 * 1024
CREATE_NO_WINDOW = 0x0800_0000


def decir(texto):
    if sys.stdout is not None:  # con pythonw no hay dónde escribir
        print(texto, flush=True)


def cacao_en_marcha(procesos=None):
    """PID de los Python de esta carpeta que ejecutan voz.py o agente_minimo.py (no este lanzador)."""
    import psutil
    encontrados = []
    for p in procesos if procesos is not None else psutil.process_iter(["pid", "name", "cmdline", "exe"]):
        try:
            info = p.info
            linea = " ".join(info.get("cmdline") or [])
            if (info.get("name") or "").lower() not in ("python.exe", "pythonw.exe") or info["pid"] == os.getpid():
                continue
            if str(BASE).lower() in (linea + " " + (info.get("exe") or "")).lower() and \
                    ("voz.py" in linea or "agente_minimo.py" in linea):
                encontrados.append(info["pid"])
        except (KeyError, TypeError):
            continue
    return encontrados


def rotar(registro=REGISTRO, maximo=MAX_REGISTRO):
    if registro.exists() and registro.stat().st_size > maximo:
        registro.replace(registro.with_name(registro.stem + ".1" + registro.suffix))


def anotar(registro, texto):
    with open(registro, "a", encoding="utf-8") as f:
        f.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} {texto} ===\n")


def entorno():
    return {**os.environ, "ESPERAR_JUEGO": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1",
            "CACAO_SEGUNDO_PLANO": "1"}


def lanzar(registro=REGISTRO, popen=subprocess.Popen, avisar=avisos_windows.notificar):
    """Arranca voz.py sin ventana, espera a que termine y avisa si fue por un error. Devuelve el código de salida."""
    rotar(registro)
    anotar(registro, "Cacao arranca")
    with open(registro, "ab") as salida:
        proceso = popen([str(PYTHON), str(SCRIPT)], cwd=str(BASE), stdout=salida, stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW, env=entorno())
        codigo = proceso.wait()
    if codigo == 0:
        anotar(registro, "Cacao terminó")
    else:
        anotar(registro, f"Cacao se cerró por un error (código {codigo})")
        avisar("Cacao se cerró por un error",
               f"Código {codigo}. Los detalles están en {registro.name} (carpeta {BASE}).")
    return codigo


def main(argv=None):
    parser = argparse.ArgumentParser(description="Arranca Cacao sin ventana de terminal.")
    parser.add_argument("--al-inicio", action="store_true", help="espera antes de arrancar (inicio de sesión)")
    parser.add_argument("--espera-s", type=int, default=60)
    parser.add_argument("--simular", action="store_true", help="solo comprobar; no carga nada")
    args = parser.parse_args(argv)

    faltan = [str(r) for r in (PYTHON, SCRIPT, BASE / "config.json", BASE / "herramientas.json") if not r.exists()]
    avisos = []
    if not faltan:
        config = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
        isla = Path(config.get("ui", {}).get("exe", ""))
        if config.get("ui", {}).get("lanzar") and not isla.exists():
            avisos.append(f"No encuentro la isla ({isla}): Cacao funcionará sin ella.")
        if not config.get("voz", {}).get("palabra_activacion", {}).get("activa", True):
            avisos.append("La palabra de activación está desactivada en config.json.")
    en_marcha = cacao_en_marcha()

    if args.simular:
        decir(f"[simulación] Carpeta: {BASE}")
        decir(f"[simulación] Faltan: {', '.join(faltan) or 'nada'}")
        decir(f"[simulación] Avisos: {' '.join(avisos) or 'ninguno'}")
        decir(f"[simulación] Cacao ya en marcha: {'sí, PID ' + ', '.join(map(str, en_marcha)) if en_marcha else 'no'}")
        decir(f"[simulación] Esperaría: {args.espera_s if args.al_inicio else 0} s")
        decir(f"[simulación] Ejecutaría sin ventana: {PYTHON} {SCRIPT} > {REGISTRO.name}")
        return 0
    if faltan:
        anotar(REGISTRO, f"No puedo arrancar Cacao; faltan: {', '.join(faltan)}")
        avisos_windows.notificar("Cacao no puede arrancar", f"Faltan: {', '.join(faltan)}")
        return 1
    if en_marcha:
        avisos_windows.notificar("Cacao ya está en marcha", "No abro otro.")
        return 0
    if args.al_inicio:
        time.sleep(args.espera_s)  # driver de la GPU, audio y WebView2 listos tras iniciar sesión
        if cacao_en_marcha():  # alguien lo abrió a mano mientras tanto
            return 0
    if avisos:
        anotar(REGISTRO, "Aviso: " + " ".join(avisos))
    return lanzar()


if __name__ == "__main__":
    sys.exit(main())
