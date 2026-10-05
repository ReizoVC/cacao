"""
Fase 6: registrador de hábitos. Proceso aparte, sin modelo: cada memoria_wiki.muestreo_s segundos guarda en
habitos.db la app al frente, su categoría y el estado (activo, inactivo o bloqueado). Sin títulos; las apps privadas
y el incógnito no dejan fila (ver habitos.py).

Se pausa mientras exista el archivo PAUSA_HABITOS (lo crea y lo borra la herramienta registro_habitos del agente).
Una sola instancia a la vez (mutex con nombre). Los errores van a registro_habitos.log.

Uso: .venv\\Scripts\\pythonw registro_habitos.py   (sin consola; para arrancar con Windows, un acceso directo en
shell:startup, que se configura con Reizo frente al PC)
"""
import ctypes
import sys
import time
import traceback
from datetime import datetime

import habitos
from entrada import MonitorEntrada

PAUSA = habitos.BASE / "PAUSA_HABITOS"
REGISTRO = habitos.BASE / "registro_habitos.log"
RECARGAR_CATEGORIAS_S = 3600  # el agente añade apps nuevas a apps_categorias.json


def anotar(texto):
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {texto}\n")


def una_sola_instancia():
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\AsistenteRegistroHabitos")
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def bucle():
    fuente = habitos.FuenteWindows()
    privacidad = habitos.Privacidad(fuente)
    clasificador, cargado = habitos.Clasificador(), time.monotonic()
    entrada = MonitorEntrada().iniciar()
    intervalo = habitos.MW["muestreo_s"]
    anotar(f"inicio (cada {intervalo} s)")
    while True:
        time.sleep(intervalo - time.time() % intervalo)  # alineado: :00 y :30
        try:
            if PAUSA.exists():
                continue
            if time.monotonic() - cargado > RECARGAR_CATEGORIAS_S:
                clasificador, cargado = habitos.Clasificador(), time.monotonic()
            muestra = habitos.tomar_muestra(fuente, clasificador, privacidad, entrada.segundos_sin_entrada())
            if muestra:
                habitos.guardar_muestra(datetime.now(), muestra)
        except Exception:
            anotar("error:\n" + traceback.format_exc())


if __name__ == "__main__":
    if not una_sola_instancia():
        sys.exit("registro_habitos.py ya está en marcha.")
    try:
        bucle()
    except KeyboardInterrupt:
        anotar("fin (Ctrl+C)")
