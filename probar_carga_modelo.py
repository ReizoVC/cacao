"""Pruebas sin modelo: importar agente_minimo no carga Gemma; cargar_modelo() lo carga una vez y en el mismo punto
del arranque que antes (modo texto, voz.py, prueba_real.py, medir_ram.py). Usa un modelo falso: no toca la GPU."""
import ast
import sys
from pathlib import Path

BASE = Path(__file__).parent
fallos = []
ejecutadas = []


def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    print(("OK " if condicion else "MAL ") + nombre + (f": {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


import agente_minimo as a  # noqa: E402

ok("importar agente_minimo no carga el modelo", a.llm is None, repr(a.llm))
ok("importar agente_minimo no sincroniza las apps (Get-StartApps)", a._cache_apps == [], len(a._cache_apps))


class LlmFalso:
    interrumpir = None


creados, sincronizados = [], []
guardado = a.crear_llm, a.sincronizar_apps
a.crear_llm = lambda config, **k: creados.append(k) or LlmFalso()
a.sincronizar_apps = lambda: sincronizados.append(1)
try:
    primero = a.cargar_modelo()
    segundo = a.cargar_modelo()
finally:
    a.crear_llm, a.sincronizar_apps = guardado
ok("cargar_modelo crea el modelo una sola vez", len(creados) == 1 and primero is segundo is a.llm, creados)
ok("cargar_modelo espera a que se cierre un juego", creados and creados[0].get("esperar_juego") is True, creados)
ok("cargar_modelo conecta el atajo de emergencia", a.llm.interrumpir == a.emergencia.comprobar)
ok("cargar_modelo sincroniza las apps después de cargar", sincronizados == [1], sincronizados)
a.llm = None


def primera_sentencia(ruta, funcion=None):
    arbol = ast.parse((BASE / ruta).read_text(encoding="utf-8"))
    if funcion:
        cuerpo = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == funcion).body
    else:  # el bloque if __name__ == "__main__"
        cuerpo = next(n for n in arbol.body if isinstance(n, ast.If) and "__main__" in ast.unparse(n.test)).body
    sentencias = [ast.unparse(n) for n in cuerpo]
    return next(s for s in sentencias if "salida_utf8()" not in s)  # la salida UTF-8 va antes (probar_salida_utf8)


ok("modo texto: lo primero del arranque es cargar_modelo()",
   primera_sentencia("agente_minimo.py") == "cargar_modelo()", primera_sentencia("agente_minimo.py"))
ok("voz.py: preparar() carga el modelo antes que Whisper y Piper",
   primera_sentencia("voz.py", "preparar") == "a.cargar_modelo()", primera_sentencia("voz.py", "preparar"))
for ruta in ("prueba_real.py", "medir_ram.py"):
    ok(f"{ruta} llama a cargar_modelo()", "a.cargar_modelo()" in (BASE / ruta).read_text(encoding="utf-8"))

print(f"{len(ejecutadas) - len(fallos)}/{len(ejecutadas)} OK")
sys.exit(1 if fallos else 0)
