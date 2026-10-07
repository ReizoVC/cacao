"""
Pruebas sin modelo de la comprobación de efecto y de la tabla de obstáculos (obstaculos.py):
  1. hubo_efecto / esperar_efecto: sin cambios -> False; ventana nueva, título, foco o portapapeles -> True;
  2. teclado y mouse (envío simulado) devuelven efecto_visible y la nota para el modelo;
  3. tabla en una memoria.db temporal: Ctrl+S sin efecto y luego Ctrl+G con efecto -> alternativa 'atajo'; luego
     el menú -> 'controles'; con contenido externo o si la tarea falla, nada;
  4. ejecutor (extraído con ast): la próxima vez sustituye Ctrl+S por Ctrl+G antes de pedir confirmación, o
     indica el menú sin enviar nada; los avisos para Reizo (resuelto, y "¿me ayudas?").
Uso: .venv\\Scripts\\python probar_obstaculos.py
"""
import ast
import json
import sys
import tempfile
from pathlib import Path

import herramientas_grupo4 as g4
import memoria
import modo_directo as md
import obstaculos

BASE = Path(__file__).parent
resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


FOTO = {"frente": 1, "titulo": "*hola: Bloc de notas", "ventanas": frozenset({1}), "foco": 5, "portapapeles": 10}


def pruebas_efecto():
    ok("efecto: sin cambios -> no", not g4.hubo_efecto(FOTO, dict(FOTO)))
    for clave, valor in (("ventanas", frozenset({1, 2})), ("titulo", "hola: Bloc de notas"), ("foco", 6),
                         ("portapapeles", 11), ("frente", 2)):
        ok(f"efecto: cambia {clave} -> sí", g4.hubo_efecto(FOTO, {**FOTO, clave: valor}))
    ok("esperar_efecto: sin cambios en 0,3 s -> False",
       g4.esperar_efecto(FOTO, espera=0.3, foto=lambda: dict(FOTO), dormir=lambda s: None) is False)
    fotos = iter([dict(FOTO), dict(FOTO), {**FOTO, "ventanas": frozenset({1, 2})}])
    ok("esperar_efecto: un diálogo que aparece tarde -> True",
       g4.esperar_efecto(FOTO, espera=5, foto=lambda: next(fotos), dormir=lambda s: None) is True)


def pruebas_herramientas():
    enviados = []
    guardado = (g4._enviar, g4.instantanea, g4.esperar_efecto, g4.estado_despues, g4.isla_al_frente, g4.proceso_de)
    g4._enviar = lambda *a, **k: enviados.append(a or k)
    g4.instantanea = lambda: dict(FOTO)
    g4.estado_despues = lambda: {}
    g4.isla_al_frente = lambda: False
    g4.proceso_de = lambda h: "notepad.exe"
    try:
        g4.esperar_efecto = lambda antes, **k: False
        r = g4.teclado("atajo", teclas=["ctrl", "s"])
        ok("teclado: atajo sin efecto -> efecto_visible False y nota para el modelo",
           r["efecto_visible"] is False and "Ctrl+G" in r["nota"] and r["app"] == "notepad.exe", r)
        g4.esperar_efecto = lambda antes, **k: True
        r = g4.teclado("atajo", teclas=["ctrl", "g"])
        ok("teclado: atajo con efecto -> efecto_visible True", r["efecto_visible"] is True)
        r = g4.teclado("escribir", texto="hola")
        ok("teclado: escribir no se mide (el texto no cambia ventanas)", "efecto_visible" not in r)
    finally:
        (g4._enviar, g4.instantanea, g4.esperar_efecto, g4.estado_despues, g4.isla_al_frente,
         g4.proceso_de) = guardado


def con_base_temporal(funcion):
    original = memoria.RUTA
    memoria.RUTA = Path(tempfile.mkdtemp()) / "memoria_prueba.db"
    try:
        funcion()
    finally:
        memoria.RUTA = original


def pruebas_tabla():
    def cuerpo():
        ok("tabla: nombre del atajo normalizado", obstaculos.nombre_atajo(["S", "Control"]) == "ctrl+s"
           and obstaculos.nombre_atajo(["mayus", "ctrl", "s"]) == "ctrl+shift+s")
        intentos = [{"app": "notepad.exe", "accion": "ctrl+s", "tipo": "atajo", "efecto": False},
                    {"app": "notepad.exe", "accion": "ctrl+g", "tipo": "atajo", "efecto": True}]
        ok("tabla: con contenido externo en la tarea no guarda nada", obstaculos.resolver(intentos, True) == []
           and obstaculos.consultar("notepad.exe", "ctrl+s") is None)
        g = obstaculos.resolver(intentos, False)
        ok("tabla: Ctrl+S sin efecto y Ctrl+G con efecto -> alternativa atajo",
           g == [("notepad.exe", "ctrl+s", "ctrl+g", "atajo")]
           and obstaculos.consultar("notepad.exe", "ctrl+s")["alternativa"] == "ctrl+g", g)
        intentos = [{"app": "word.exe", "accion": "ctrl+s", "tipo": "atajo", "efecto": False},
                    {"app": "otra.exe", "accion": "ctrl+g", "tipo": "atajo", "efecto": True},
                    {"app": "word.exe", "accion": "Archivo", "tipo": "control", "efecto": True},
                    {"app": "word.exe", "accion": "Guardar\ncomo", "tipo": "control", "efecto": True}]
        g = obstaculos.resolver(intentos, False)
        ok("tabla: por el menú -> alternativa 'controles' (solo la misma app, nombres limpios)",
           g == [("word.exe", "ctrl+s", "Archivo > Guardar como", "controles")], g)
        intentos = [{"app": "x.exe", "accion": "ctrl+a", "tipo": "atajo", "efecto": False}]
        ok("tabla: un fallo sin otro camino no guarda alternativa", obstaculos.resolver(intentos, False) == []
           and obstaculos.consultar("x.exe", "ctrl+a") is None)
    con_base_temporal(cuerpo)


def cargar_agente(preguntas, enviados):
    nombres = {"ejecutar", "camino_conocido", "anotar_intento", "cerrar_obstaculos", "legible", "nombre_app",
               "NOMBRES_APPS", "_tarea", "decision_modo", "_decision", "_modos", "_guardia", "TEXTO_EXTERNO",
               "GUARDAN_SOBRE_REIZO", "SOLO_CONSULTAN"}
    arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
    nodos = [n for n in arbol.body if (isinstance(n, ast.FunctionDef) and n.name in nombres)
             or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in nombres for t in n.targets))]
    catalogo = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))
    avisos_isla = []
    g4_falso = type("G4", (), {"proceso_de": staticmethod(lambda h: "notepad.exe"), "guardia_directa": None,
                               "win32gui": type("W", (), {"GetForegroundWindow": staticmethod(lambda: 1)})})()
    ns = {"json": json, "modo_directo": md, "obstaculos": obstaculos, "herramientas_grupo4": g4_falso,
          "PLANIFICADORES": {}, "Detenido": KeyError, "print": lambda *a, **k: None,
          "HERRAMIENTAS": {h["nombre"]: h for h in catalogo["herramientas"]},
          "_isla": type("I", (), {"enviar": staticmethod(lambda m: avisos_isla.append(m))})(),
          "confirmar": lambda herramienta, resumen, *a, **k: preguntas.append(resumen) or True,
          "emergencia": type("E", (), {"comprobar": staticmethod(lambda: None)})()}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "agente_minimo.py", "exec"), ns)

    def teclado(accion, teclas=None, texto=None):
        enviados.append(teclas)
        efecto = teclas != ["ctrl", "s"]
        return {"ok": True, "efecto_visible": efecto, "app": "notepad.exe"}

    ns["IMPLEMENTACIONES"] = {"teclado": teclado,
                              "mouse": lambda **k: {"ok": True, "efecto_visible": True, "app": "notepad.exe",
                                                    "control": f"{k.get('control')} (MenuItem)"}}
    return ns, avisos_isla


def pruebas_ejecutor():
    def cuerpo():
        preguntas, enviados = [], []
        ns, avisos = cargar_agente(preguntas, enviados)
        ns["_tarea"].update(pedido="guarda el bloc de notas", herramientas=[], intentos=[], avisos=[])
        ns["ejecutar"]("teclado", {"accion": "atajo", "teclas": ["ctrl", "s"]})
        ok("ejecutor: un atajo sin efecto se avisa en la isla al momento",
           avisos and "no tuvo efecto en el Bloc de notas" in avisos[-1]["texto"], avisos)
        ns["ejecutar"]("teclado", {"accion": "atajo", "teclas": ["ctrl", "g"]})
        mensaje = ns["cerrar_obstaculos"](True)
        ok("ejecutor: al terminar bien, guarda Ctrl+G y se lo dice a Reizo",
           "Ctrl+S no hizo nada en el Bloc de notas; funcionó Ctrl+G" in mensaje, mensaje)
        # la próxima vez
        preguntas.clear(), enviados.clear()
        ns["_tarea"].update(intentos=[], avisos=[])
        ns["ejecutar"]("teclado", {"accion": "atajo", "teclas": ["ctrl", "s"]})
        ok("ejecutor: la próxima vez envía directo Ctrl+G", enviados == [["ctrl", "g"]], enviados)
        ok("ejecutor: la confirmación ya muestra Ctrl+G (no Ctrl+S)", preguntas and '"g"' in preguntas[-1]
           and '"s"' not in preguntas[-1], preguntas)
        ok("ejecutor: y avisa del cambio", "Usé Ctrl+G en vez de Ctrl+S" in ns["cerrar_obstaculos"](True))
        # camino por menú
        obstaculos.registrar_alternativa("notepad.exe", "ctrl+shift+s", "Archivo > Guardar como", "controles")
        enviados.clear()
        r = ns["ejecutar"]("teclado", {"accion": "atajo", "teclas": ["ctrl", "shift", "s"]})
        ok("ejecutor: si lo que funciona es el menú, no envía nada y le indica el camino al modelo",
           not enviados and "Archivo > Guardar como" in r["error"] and not r.get("bloqueado"), r)
        # sin solución
        ns["_tarea"].update(intentos=[], avisos=[])
        ns["IMPLEMENTACIONES"]["teclado"] = lambda **k: {"ok": True, "efecto_visible": False, "app": "notepad.exe"}
        ns["ejecutar"]("teclado", {"accion": "atajo", "teclas": ["ctrl", "q"]})
        mensaje = ns["cerrar_obstaculos"](False)
        ok("ejecutor: sin otro camino y la tarea falla -> pide ayuda", "¿me ayudas?" in mensaje, mensaje)
        # contenido externo
        ns["_tarea"].update(intentos=[], avisos=[], herramientas=[("leer_archivo", {})])
        ns["IMPLEMENTACIONES"]["teclado"] = lambda teclas=None, **k: {"ok": True, "efecto_visible": teclas != ["ctrl", "e"],
                                                                      "app": "notepad.exe"}
        ns["ejecutar"]("teclado", {"accion": "atajo", "teclas": ["ctrl", "e"]})
        ns["ejecutar"]("teclado", {"accion": "atajo", "teclas": ["ctrl", "f"]})
        ns["cerrar_obstaculos"](True)
        ok("ejecutor: con contenido externo en la tarea no aprende nada", obstaculos.consultar("notepad.exe", "ctrl+e")
           is None)
    con_base_temporal(cuerpo)
    fuente = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
    ok("agente: la respuesta final (isla y voz) lleva el aviso de obstáculos",
       "aviso_obstaculos = cerrar_obstaculos(bool(exito_tarea))" in fuente)


if __name__ == "__main__":
    for parte in (pruebas_efecto, pruebas_herramientas, pruebas_tabla, pruebas_ejecutor):
        print(f"\n== {parte.__name__} ==", flush=True)
        parte()
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
