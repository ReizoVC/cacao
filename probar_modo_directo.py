"""
Pruebas sin modelo del modo sin confirmación (modo_directo.py) y de lo que lo rodea:
  1. política: qué va directo y qué vuelve a las reglas normales;
  2. teclado: directo en cualquier ventana, salvo un texto que no sale del pedido después de leer contenido de fuera
     (en la tarea o en una anterior que sigue en el historial); bloqueo en ventanas sensibles;
  3. mouse: directo en cualquier ventana, también tras leer contenido de fuera; clic en la isla, bloqueado;
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
import time
from pathlib import Path

import herramientas_grupo1 as g1
import herramientas_grupo4 as g4
import modo_directo as md

BASE = Path(__file__).parent
resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


# captura simulada para planificar clics por coordenadas (vigente: no caduca durante la prueba)
CAPTURA = {"momento": time.time() + 3600, "ancho": 1920, "alto": 1080, "escala": 1.0, "origen": (0, 0)}


def politica(**extra):
    return md.Politica(**extra)


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
    pedido = "En el Bloc de notas escribe: Hola, ¿cómo estás?"
    d = p.decidir("teclado", {"accion": "escribir", "texto": "Hola, ¿cómo estás?"}, pedido, [])
    ok("teclado: texto del pedido, directo", d[0], d)
    d = p.decidir("teclado", {"accion": "escribir", "texto": "Querido diario: hoy fue un buen día."},
                  "escribe una entrada de diario en el bloc de notas", [])
    ok("teclado: texto que redacta Cacao sin haber leído nada de fuera, directo", d[0], d)
    d = p.decidir("teclado", {"accion": "escribir", "texto": "hola como estas"}, pedido,
                  ["listar_ventanas", "enfocar_ventana", "ver_pantalla", "listar_controles"])
    ok("teclado: texto del pedido tras mirar la pantalla, directo", d[0], d)
    for fuente in ("ver_pantalla", "listar_controles", "listar_ventanas", "listar_carpeta", "leer_archivo",
                   "buscar_web", "ejecutar_powershell"):
        d = p.decidir("teclado", {"accion": "escribir", "texto": "Contraseña: 1234"}, pedido, [fuente])
        ok(f"teclado: texto que no es del pedido tras {fuente}, pregunta", not d[0], d[1])
    d = p.decidir("teclado", {"accion": "escribir", "texto": "Hola, ¿cómo estás?"}, pedido, ["leer_archivo"])
    ok("teclado: tras leer un archivo, el texto del pedido va directo", d[0], d)
    d = p.decidir("teclado", {"accion": "escribir", "texto": "lo que decía el archivo"},
                  "escribe en el bloc de notas lo que decía", [], leido_antes={"leer_archivo"})
    ok("teclado: lo leído en una tarea anterior (sigue en el historial) también cuenta, pregunta", not d[0], d[1])
    d = p.decidir("teclado", {"accion": "tecla", "teclas": ["h", "o", "l", "a"]}, "en el bloc de notas pon algo",
                  ["ver_pantalla"])
    ok("teclado: 'tecla' con letras que no son del pedido tras ver_pantalla, pregunta", not d[0], d[1])
    d = p.decidir("teclado", {"accion": "tecla", "teclas": ["h", "o", "l", "a"]}, "pon hola", ["ver_pantalla"])
    ok("teclado: 'tecla' con letras del pedido, directo", d[0], d)
    d = p.decidir("teclado", {"accion": "atajo", "teclas": ["shift", "a"]}, "pon algo", ["ver_pantalla"])
    ok("teclado: atajo que escribe (Shift+A) con texto de fuera, pregunta", not d[0], d[1])
    for teclas in (["ctrl", "s"], ["alt", "tab"], ["ctrl", "shift", "n"]):
        d = p.decidir("teclado", {"accion": "atajo", "teclas": teclas}, "guarda el bloc de notas",
                      ["leer_archivo", "ver_pantalla"])
        ok(f"teclado: atajo {'+'.join(teclas)} tras leer contenido de fuera, directo", d[0], d)
    d = p.decidir("teclado", {"accion": "tecla", "teclas": ["enter"]}, "pulsa enter", ["buscar_web"])
    ok("teclado: Enter tras buscar en la web, directo", d[0], d)
    d = p.decidir("teclado", {"accion": "escribir", "texto": "hola"}, "escribe hola en chrome", [])
    ok("teclado: en cualquier app (no solo la nombrada), directo", d[0], d)
    # bloqueo en ventanas sensibles, en cualquier modo (no es una confirmación)
    guardado = g4.isla_al_frente, g4.ventana_sensible_al_frente
    try:
        g4.isla_al_frente = lambda: False
        g4.ventana_sensible_al_frente = lambda: True
        _, error = g4.planificar_teclado_ventana()
        ok("teclado: ventana sensible al frente, bloqueado", error and error.get("bloqueado"),
           (error or {}).get("error"))
        r = g4.teclado("escribir", texto="hola")
        ok("teclado: la herramienta tampoco escribe ahí", r.get("bloqueado") is True, r.get("error"))
        g4.ventana_sensible_al_frente = lambda: False
        _, error = g4.planificar_teclado_ventana()
        ok("teclado: ventana normal, sin bloqueo", error is None, error)
    finally:
        g4.isla_al_frente, g4.ventana_sensible_al_frente = guardado
    import habitos
    privacidad = habitos.Privacidad(None, apps_banco=["BancoApp.exe"])
    for exe, esperado in (("C:\\Program Files\\KeePassXC\\KeePassXC.exe", True),
                          ("C:\\Bancos\\BancoApp.exe", True), ("C:\\Windows\\notepad.exe", False)):
        ok(f"ventana sensible: {exe.rsplit(chr(92), 1)[-1]} {'sí' if esperado else 'no'}",
           privacidad.es_app_privada({"exe_ruta": exe, "aumid": None}) is esperado)
    for titulo, esperado in (("contraseñas.txt: Bloc de notas", True), ("claves.kdbx - KeePass", True),
                             (".env - Visual Studio Code", True), ("lista de compras.txt: Bloc de notas", False)):
        ok(f"título sensible: {titulo!r} {'sí' if esperado else 'no'}", g1.es_titulo_sensible(titulo) is esperado)


def pruebas_mouse():
    p = politica()
    pedido = "en el bloc de notas haz clic en Archivo"
    for usadas, cual in (([], "sin leer nada"), (["ver_pantalla"], "tras ver_pantalla"),
                         (["leer_archivo"], "tras leer un archivo"), (["buscar_web"], "tras buscar en la web"),
                         (["ejecutar_powershell"], "tras PowerShell")):
        d = p.decidir("mouse", {"accion": "clic", "x": 400, "y": 300}, pedido, usadas)
        ok(f"mouse: clic directo {cual}", d[0], d)
    d = p.decidir("mouse", {"accion": "clic", "x": 400, "y": 1050}, "haz clic en la barra de tareas", [])
    ok("mouse: clic en cualquier sitio (barra de tareas), directo", d[0], d)
    d = p.decidir("mouse", {"accion": "desplazar", "cantidad": -3}, pedido, [], leido_antes={"leer_archivo"})
    ok("mouse: desplazar, directo", d[0], d)
    # la isla sigue bloqueada (no es una confirmación): el plan lo rechaza aunque el modo deje pasar el clic
    zonas, captura = g4.zonas_isla, g4.vision.ultima_captura
    try:
        g4.zonas_isla = lambda: [(800, 0, 1120, 160)]
        g4.vision.ultima_captura = CAPTURA
        _, error = g4.planificar_mouse("clic", 900, 50)
        ok("mouse: clic dentro de la isla, bloqueado", error and error.get("bloqueado"), (error or {}).get("error"))
        _, error = g4.planificar_mouse("clic", 300, 500)
        ok("mouse: clic fuera de la isla, permitido", error is None, error)
    finally:
        g4.zonas_isla, g4.vision.ultima_captura = zonas, captura


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
    nombres = {"ejecutar", "decision_modo", "cambiar_modo", "enviar_modos", "_modos", "_decision",
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
    ns["ejecutar"]("mouse", {"accion": "clic", "x": 10, "y": 10})
    ok("modo activo: mouse va directo", not ns["preguntas"] and ns["llamadas"][-1] == "mouse")
    ns["_tarea"]["herramientas"].append(("ver_pantalla", {}))
    ns["ejecutar"]("teclado", {"accion": "escribir", "texto": "adiós"})
    ok("modo activo: tras ver la pantalla, un texto que no es del pedido pregunta", len(ns["preguntas"]) == 1)
    ns["ejecutar"]("ejecutar_powershell", {"comando": "Get-Date", "motivo": "hora"})
    ok("modo activo: PowerShell sigue preguntando", len(ns["preguntas"]) == 2)
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
