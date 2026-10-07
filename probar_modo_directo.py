"""
Pruebas sin modelo del modo sin confirmación (modo_directo.py) y de lo que lo rodea:
  1. política: qué va directo y qué vuelve a las reglas normales (ventanas y apps simuladas);
  2. teclado: texto del pedido o leído en pantalla / en un archivo;
  3. mouse: clic dentro de la app nombrada, fuera de ella, en la barra de tareas, y la comprobación justo antes;
  4. atajos bloqueados en cualquier modo;
  5. mover_archivo: 10 y 11 archivos, un .exe, carpetas importantes, y deshacer (archivos reales en una carpeta
     temporal que se borra al terminar);
  6. el agente no puede cambiar el modo (sin clic físico, sin herramienta y sin frase).
Uso: .venv\\Scripts\\python probar_modo_directo.py
"""
import ast
import json
import shutil
import sys
import tempfile
from pathlib import Path

import herramientas_grupo1 as g1
import herramientas_grupo4 as g4
import modo_directo as md

BASE = Path(__file__).parent
resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


# ventanas simuladas: rectángulos de pantalla -> app
BLOC = {"nombres": {"Bloc de notas", "Notepad"}, "proceso": "Notepad.exe", "pid": 100, "shell": False}
CHROME = {"nombres": {"Google Chrome", "chrome"}, "proceso": "chrome.exe", "pid": 200, "shell": False}
BARRA = {"nombres": {"Explorador de archivos", "explorer"}, "proceso": "explorer.exe", "pid": 300, "shell": True}
PANTALLA = [((0, 0, 1000, 1000), BLOC), ((1000, 0, 2000, 1000), CHROME), ((0, 1000, 2000, 1080), BARRA)]
estado = {"frente": BLOC}


def app_en_punto(x, y):
    return next((a for (l, t, r, b), a in PANTALLA if l <= x < r and t <= y < b), None)


def plan_mouse(accion, x=None, y=None, cantidad=None, control=None, id_ventana=None):
    return {"accion": accion, "pantalla": (x, y) if x is not None else None, "cantidad": cantidad}, None


def politica(**extra):
    return md.Politica(app_en_punto=app_en_punto, app_al_frente=lambda: estado["frente"],
                       posicion_cursor=lambda: (500, 500), planificar_mouse=plan_mouse, **extra)


def pruebas_politica():
    p = politica()
    pedido = "abre el bloc de notas y escribe hola mundo"
    for nombre, args in (("volumen", {"accion": "subir"}), ("abrir_app", {"nombre": "Spotify"}),
                         ("enfocar_ventana", {"id_ventana": 1}), ("buscar_web", {"consulta": "clima"}),
                         ("cerrar_app", {"id_ventana": 1})):
        ok(f"directa: {nombre}", p.decidir(nombre, args, pedido, [])[0])
    ok("ejecutar_powershell siempre pregunta", not p.decidir("ejecutar_powershell", {"comando": "Get-Date"},
                                                             pedido, [])[0])
    ok("cerrar_app forzado siempre pregunta", not p.decidir("cerrar_app", {"id_ventana": 1, "forzar": True},
                                                            pedido, [])[0])
    for fuente in ("leer_archivo", "buscar_web", "ejecutar_powershell"):
        d = p.decidir("volumen", {"accion": "subir"}, pedido, [fuente])
        ok(f"tras {fuente}: todo vuelve a las reglas normales", not d[0], d[1])
    d = p.decidir("buscar_web", {"consulta": "algo de la pantalla"}, pedido, ["ver_pantalla"])
    ok("tras ver_pantalla: buscar_web vuelve a las reglas normales", not d[0], d[1])
    d = p.decidir("abrir_app", {"nombre": "PowerShell"}, pedido, ["ver_pantalla"])
    ok("tras ver_pantalla: abrir una app que no nombró no va directo", not d[0], d[1])
    d = p.decidir("recordar", {"dato": "x"}, pedido, [])
    ok("recordar no está entre las directas", not d[0], d[1])


def pruebas_teclado():
    p = politica()
    estado["frente"] = BLOC
    pedido = "En el Bloc de notas escribe: Hola, ¿cómo estás?"
    d = p.decidir("teclado", {"accion": "escribir", "texto": "Hola, ¿cómo estás?"}, pedido, [])
    ok("teclado: texto del pedido en la app nombrada, directo", d[0], d)
    d = p.decidir("teclado", {"accion": "escribir", "texto": "hola como estas"}, pedido, ["ver_pantalla",
                                                                                         "listar_controles"])
    ok("teclado: ver_pantalla/listar_controles para ubicar no lo impiden", d[0], d)
    d = p.decidir("teclado", {"accion": "escribir", "texto": "Contraseña: 1234 (leída en pantalla)"}, pedido,
                  ["ver_pantalla"])
    ok("teclado: texto leído en pantalla (no está en el pedido) pregunta", not d[0], d[1])
    d = p.decidir("teclado", {"accion": "escribir", "texto": "Hola, ¿cómo estás?"}, pedido, ["leer_archivo"])
    ok("teclado: tras leer un archivo pregunta aunque el texto coincida", not d[0], d[1])
    d = p.decidir("teclado", {"accion": "escribir", "texto": "texto copiado de una web"},
                  "escribe en el bloc de notas lo que diga la web", ["buscar_web"])
    ok("teclado: texto de la web pregunta", not d[0], d[1])
    estado["frente"] = CHROME
    d = p.decidir("teclado", {"accion": "escribir", "texto": "Hola, ¿cómo estás?"}, pedido, [])
    ok("teclado: la ventana al frente no es la app nombrada, pregunta", not d[0], d[1])
    estado["frente"] = BLOC
    d = p.decidir("teclado", {"accion": "atajo", "teclas": ["ctrl", "s"]}, "guarda el bloc de notas", [])
    ok("teclado: Ctrl+S en la app nombrada, directo", d[0], d)
    d = p.decidir("teclado", {"accion": "tecla", "teclas": ["h", "o", "l", "a"]}, "en el bloc de notas pon algo", [])
    ok("teclado: 'tecla' con letras es escribir, pregunta", not d[0], d[1])
    d = p.decidir("teclado", {"accion": "tecla", "teclas": ["enter"]}, "en el bloc de notas pulsa enter", [])
    ok("teclado: Enter en la app nombrada, directo", d[0], d)


def pruebas_mouse():
    p = politica()
    pedido = "en el bloc de notas haz clic en Archivo"
    d = p.decidir("mouse", {"accion": "clic", "x": 400, "y": 300}, pedido, ["ver_pantalla"])
    ok("mouse: clic dentro de la ventana de la app nombrada, directo", d[0], d)
    d = p.decidir("mouse", {"accion": "clic", "x": 1500, "y": 300}, pedido, ["ver_pantalla"])
    ok("mouse: clic fuera de esa ventana (en Chrome), pregunta", not d[0], d[1])
    d = p.decidir("mouse", {"accion": "clic", "x": 400, "y": 1050}, pedido, [])
    ok("mouse: clic en la barra de tareas, pregunta", not d[0], d[1])
    d = p.decidir("mouse", {"accion": "desplazar", "cantidad": -3}, pedido, [])
    ok("mouse: desplazar con el cursor sobre la app nombrada, directo", d[0], d)
    # justo antes de actuar se vuelve a mirar: si la ventana cambió, no se hace
    ns = cargar_ejecutor()
    guardia = ns["_guardia"]({"pid": 100})
    md_original = ns["modo_directo"].app_en_punto
    ns["modo_directo"].app_en_punto = app_en_punto
    try:
        ok("guardia: mismo punto, misma app, deja hacerlo", guardia("mouse", (400, 300)) is None)
        ok("guardia: la ventana cambió (otra app en el punto), no lo hace", guardia("mouse", (1500, 300)) is not None)
    finally:
        ns["modo_directo"].app_en_punto = md_original


def pruebas_atajos():
    bloqueados = [["win", "r"], ["win", "x"], ["win", "i"], ["win", "s"], ["win", "e"], ["win", "b"], ["win", "5"],
                  ["win"], ["ctrl", "esc"], ["ctrl", "shift", "esc"], ["ctrl", "alt", "supr"], ["alt", "f4"],
                  ["win", "v"], ["win", "h"], ["win", "l"], ["win", "g"], ["win", "ctrl", "enter"], ["win", "j"],
                  ["ctrl", "alt", "shift", "q"]]
    for teclas in bloqueados:
        _, error = g4.planificar_teclado("atajo", teclas=teclas)
        ok(f"atajo bloqueado: {'+'.join(teclas)}", error and error.get("bloqueado"), (error or {}).get("error"))
    _, error = g4.planificar_teclado("tecla", teclas=["win"])
    ok("tecla Windows sola bloqueada", error and error.get("bloqueado"))
    for teclas in (["win", "d"], ["win", "izquierda"], ["ctrl", "s"], ["alt", "tab"]):
        _, error = g4.planificar_teclado("atajo", teclas=teclas)
        ok(f"atajo permitido: {'+'.join(teclas)}", error is None, error)


def pruebas_mover():
    tmp = Path(tempfile.mkdtemp(prefix="modo_directo_"))
    g1.CARPETAS_PERMITIDAS.append(tmp.resolve())
    historial = g4.HISTORIAL_MOVIMIENTOS
    g4.HISTORIAL_MOVIMIENTOS = tmp / "historial.json"
    try:
        (tmp / "diez").mkdir()
        for i in range(10):
            (tmp / "diez" / f"f{i}.txt").write_text("x")
        (tmp / "once").mkdir()
        for i in range(11):
            (tmp / "once" / f"f{i}.txt").write_text("x")
        (tmp / "programa.exe").write_bytes(b"MZ")
        (tmp / "conscript").mkdir()
        (tmp / "conscript" / "a.txt").write_text("x")
        (tmp / "conscript" / "instalar.ps1").write_text("x")
        (tmp / "importante").mkdir()
        (tmp / "nota.txt").write_text("x")
        (tmp / "destino").mkdir()
        p = politica(importantes=[(tmp / "importante").resolve()])
        d = p.decidir("mover_archivo", {"origen": str(tmp / "diez"), "destino": str(tmp / "destino")}, "", [])
        ok("mover: carpeta con 10 archivos, directo", d[0], d)
        d = p.decidir("mover_archivo", {"origen": str(tmp / "once"), "destino": str(tmp / "destino")}, "", [])
        ok("mover: 11 archivos, pregunta", not d[0], d[1])
        d = p.decidir("mover_archivo", {"origen": str(tmp / "nota.txt"), "destino": str(tmp / "destino")}, "", [], 10)
        ok("mover: el archivo 11 de la tarea (uno a uno), pregunta", not d[0], d[1])
        d = p.decidir("mover_archivo", {"origen": str(tmp / "programa.exe"), "destino": str(tmp / "destino")}, "", [])
        ok("mover: un .exe, pregunta", not d[0], d[1])
        d = p.decidir("mover_archivo", {"origen": str(tmp / "conscript"), "destino": str(tmp / "destino")}, "", [])
        ok("mover: carpeta con un .ps1 dentro, pregunta", not d[0], d[1])
        d = p.decidir("mover_archivo", {"origen": str(tmp / "nota.txt"), "destino": str(tmp / "importante")}, "", [])
        ok("mover: destino en una carpeta importante, pregunta", not d[0], d[1])
        d = p.decidir("mover_archivo", {"origen": str(tmp / "nota.txt"), "destino": str(tmp / "destino")}, "",
                      ["ver_pantalla"])
        ok("mover: tras ver_pantalla vuelve a las reglas normales", not d[0], d[1])
        # deshacer: dos movimientos en una tarea vuelven los dos
        g4.tarea_actual = "t1"
        r1 = g4.mover_archivo(str(tmp / "nota.txt"), str(tmp / "destino"))
        r2 = g4.mover_archivo(str(tmp / "diez"), "diez_renombrada")
        ok("mover: movimientos reales anotados en el historial", r1["ok"] and r2["ok"]
           and len(json.loads(g4.HISTORIAL_MOVIMIENTOS.read_text(encoding="utf-8"))) == 2)
        r = g4.deshacer_movimiento()
        ok("deshacer: los dos vuelven a su sitio", r["ok"] and (tmp / "nota.txt").exists() and (tmp / "diez").exists()
           and not (tmp / "destino" / "nota.txt").exists(), r)
        r = g4.deshacer_movimiento()
        ok("deshacer: sin nada más que deshacer, lo dice", not r["ok"], r.get("error"))
        g4.tarea_actual = "t2"
        g4.mover_archivo(str(tmp / "nota.txt"), str(tmp / "destino"))
        (tmp / "nota.txt").write_text("otro")  # alguien puso otro archivo con el mismo nombre en el origen
        r = g4.deshacer_movimiento()
        ok("deshacer: nunca sobrescribe", not r["ok"] and (tmp / "destino" / "nota.txt").exists(), r.get("error"))
    finally:
        g1.CARPETAS_PERMITIDAS.remove(tmp.resolve())
        g4.HISTORIAL_MOVIMIENTOS = historial
        g4.tarea_actual = None
        shutil.rmtree(tmp, ignore_errors=True)


# ---------- el agente (funciones de agente_minimo.py extraídas con ast, sin modelo) ----------

def cargar_ejecutor():
    nombres = {"ejecutar", "decision_modo", "_guardia", "cambiar_modo", "enviar_modos", "_modos", "_decision",
               "_tarea", "TEXTO_EXTERNO", "GUARDAN_SOBRE_REIZO", "SOLO_CONSULTAN", "camino_conocido",
               "anotar_intento", "legible", "nombre_app", "NOMBRES_APPS"}
    arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
    nodos = [n for n in arbol.body if (isinstance(n, ast.FunctionDef) and n.name in nombres)
             or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in nombres for t in n.targets))]
    catalogo = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))
    preguntas, llamadas, enviados = [], [], []

    class IslaFalsa:
        def enviar(self, m):
            enviados.append(m)

    obstaculos_falso = type("O", (), {"consultar": staticmethod(lambda app, accion: None),
                                      "nombre_atajo": staticmethod(lambda teclas: "+".join(teclas or [])),
                                      "contar_uso": staticmethod(lambda *a: None)})()
    ns = {"json": json, "modo_directo": md, "herramientas_grupo4": g4, "PLANIFICADORES": {}, "Detenido": KeyError,
          "obstaculos": obstaculos_falso,
          "HERRAMIENTAS": {h["nombre"]: h for h in catalogo["herramientas"]}, "_isla": IslaFalsa(),
          "confirmar": lambda *a, **k: preguntas.append(a) or False,
          "emergencia": type("E", (), {"comprobar": staticmethod(lambda: None)})(), "print": lambda *a, **k: None}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "agente_minimo.py", "exec"), ns)
    ns["IMPLEMENTACIONES"] = {h: (lambda h_: lambda **a: llamadas.append(h_) or {"ok": True})(h)
                              for h in ns["HERRAMIENTAS"]}
    ns["_politica"] = politica()
    ns["preguntas"], ns["llamadas"], ns["enviados"] = preguntas, llamadas, enviados
    return ns


def pruebas_agente():
    ns = cargar_ejecutor()
    ns["_tarea"].update(pedido="en el bloc de notas escribe hola", herramientas=[], movidos=0)
    estado["frente"] = BLOC
    ns["ejecutar"]("teclado", {"accion": "escribir", "texto": "hola"})
    ok("modo apagado: teclado pregunta como siempre", len(ns["preguntas"]) == 1 and not ns["llamadas"])
    ns["cambiar_modo"]("sin_confirmacion", False, "isla")
    ok("agente: sin clic físico el modo no cambia", ns["_modos"]["sin_confirmacion"] is False
       and any(m.get("tipo") == "aviso" for m in ns["enviados"]))
    ns["cambiar_modo"]("sin_confirmacion", True, "bandeja")
    ok("clic físico en la bandeja: modo activado y la isla lo sabe", ns["_modos"]["sin_confirmacion"] is True
       and {"tipo": "modos", "sin_confirmacion": True} in ns["enviados"])
    ns["preguntas"].clear()
    ns["_decision"].update(clave=None)
    ns["ejecutar"]("teclado", {"accion": "escribir", "texto": "hola"})
    ok("modo activo: teclado con texto del pedido va directo", not ns["preguntas"] and ns["llamadas"] == ["teclado"])
    ns["ejecutar"]("teclado", {"accion": "escribir", "texto": "adiós"})
    ok("modo activo: texto que no es del pedido pregunta", len(ns["preguntas"]) == 1)
    ns["cambiar_modo"]("sin_confirmacion", True, "isla")
    ok("otro clic físico lo desactiva", ns["_modos"]["sin_confirmacion"] is False)
    ns["cambiar_modo"]("cualquier_otro", True, "isla")
    ok("un modo desconocido no se crea", "cualquier_otro" not in ns["_modos"])
    # ninguna herramienta ni frase cambia el modo
    catalogo = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))
    sospechosas = [h["nombre"] for h in catalogo["herramientas"]
                   if "modo" in h["nombre"] or "confirmaci" in json.dumps(h.get("parametros", {}))]
    ok("ninguna herramienta del agente toca el modo", not sospechosas, sospechosas)
    fuente = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    escrituras = [n for n in ast.walk(arbol) if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Subscript) and getattr(t.value, "id", None) == "_modos" for t in n.targets)]
    funciones = {f.name for f in ast.walk(arbol) if isinstance(f, ast.FunctionDef)
                 for n in escrituras if f.lineno <= n.lineno <= f.end_lineno}
    ok("solo cambiar_modo (clic físico) y el atajo de emergencia (que lo apaga) escriben el modo",
       funciones <= {"cambiar_modo", "atender"}, funciones)
    ok("no hay frase de voz que lo active", "sin confirmaci" not in "".join(
        ast.literal_eval(n.value) if isinstance(n.value, ast.Constant) else "" for n in arbol.body
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "").startswith("FRASES") for t in n.targets)))


if __name__ == "__main__":
    for parte in (pruebas_politica, pruebas_teclado, pruebas_mouse, pruebas_atajos, pruebas_mover, pruebas_agente):
        print(f"\n== {parte.__name__} ==")
        parte()
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
