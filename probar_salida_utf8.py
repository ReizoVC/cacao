"""Pruebas sin modelo: voz.py y el modo texto escriben en UTF-8 aunque no los arranque el lanzador (que pone
PYTHONIOENCODING). Corre Python en subprocesos con la salida a una tubería y sin variables de codificación."""
import ast
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
TEXTO = "Canción «Año» ñandú 🎵"
fallos = []
ejecutadas = []


def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    print(("OK " if condicion else "MAL ") + nombre + (f": {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


def correr(codigo):
    entorno = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    return subprocess.run([sys.executable, "-c", codigo], cwd=BASE, env=entorno, capture_output=True, timeout=120)


sin = correr(f"print({TEXTO!r})")
ok("sin nada, la salida a una tubería no es UTF-8 (el fallo que se corrige)",
   sin.returncode != 0 or sin.stdout.decode("utf-8", "replace").strip() != TEXTO,
   f"código {sin.returncode}")

con = correr(f"import agente_minimo as a; a.salida_utf8(); print({TEXTO!r}); import sys; print({TEXTO!r}, file=sys.stderr)")
ok("con salida_utf8, stdout sale en UTF-8", con.returncode == 0 and con.stdout.decode("utf-8").strip() == TEXTO,
   con.stdout[-200:] or con.stderr[-300:])
ok("y stderr también", TEXTO in con.stderr.decode("utf-8", "replace"))

import agente_minimo as a  # noqa: E402  (no carga el modelo)

guardado = sys.stdout, sys.stderr
sys.stdout = sys.stderr = None  # como con pythonw
try:
    a.salida_utf8()
    sin_consola = True
except Exception as e:  # noqa: BLE001
    sin_consola = e
finally:
    sys.stdout, sys.stderr = guardado
ok("sin consola (pythonw) no falla", sin_consola is True, sin_consola)


def bloque_main(ruta):
    arbol = ast.parse((BASE / ruta).read_text(encoding="utf-8"))
    return next(n for n in arbol.body if isinstance(n, ast.If) and "__main__" in ast.unparse(n.test)).body


ok("modo texto: lo primero es salida_utf8()", ast.unparse(bloque_main("agente_minimo.py")[0]) == "salida_utf8()")
ok("voz.py: lo primero es a.salida_utf8()", ast.unparse(bloque_main("voz.py")[0]) == "a.salida_utf8()")

print(f"{len(ejecutadas) - len(fallos)}/{len(ejecutadas)} OK")
sys.exit(1 if fallos else 0)
