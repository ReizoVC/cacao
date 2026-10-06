"""
Prueba sin modelo la elección de apps de agente_minimo.py (bloqueadas, confirmar, alias y genéricos) contra el
catálogo real de apps_categorias.json. No abre nada. Usa una base de memoria aparte (memoria_prueba_apps.db).
Uso: .venv\\Scripts\\python probar_apps.py
"""
import ast
import json
import re
import unicodedata
from pathlib import Path

from rapidfuzz import process, fuzz

import memoria

BASE = Path(__file__).parent
NOMBRES = {"normalizar", "coincide_por_siglas", "nivel_app", "_sin_articulos", "es_generico", "opciones_genericas",
           "elegir_app", "preparar_apertura", "cubre_bien", "CATEGORIAS", "ARTICULOS", "GENERICOS", "APPS_SENSIBLES"}
arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
nodos = [n for n in arbol.body
         if (isinstance(n, ast.FunctionDef) and n.name in NOMBRES)
         or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in NOMBRES for t in n.targets))]
categorias = json.loads((BASE / "apps_categorias.json").read_text(encoding="utf-8"))
respuesta = {"valor": "n"}
ns = {"re": re, "unicodedata": unicodedata, "process": process, "fuzz": fuzz, "memoria": memoria,
      "CATALOGO": json.loads((BASE / "herramientas.json").read_text(encoding="utf-8")),
      "_categorias": categorias, "confirmar": lambda *_a, **_k: respuesta["valor"] == "s"}
exec(compile(ast.Module(body=nodos, type_ignores=[]), "agente_minimo.py", "exec"), ns)
APPS = [{"nombre": d["nombre"], "id": i} for i, d in categorias.items()]
BLOQUEADAS = {a["id"] for a in APPS if ns["nivel_app"](a["id"]) == "bloqueadas"}

fallos = []


def probar(nombre, esperado, contestar="n"):
    """esperado: nombre de app, 'bloqueada', 'pregunta', 'rechazada' o 'no_encontrada'."""
    respuesta["valor"] = contestar
    app, error = ns["preparar_apertura"](nombre, APPS)
    if app:
        obtenido = app["nombre"]
    elif "bloqueada" in error.get("error", ""):
        obtenido = "bloqueada"
    elif "no autorizó" in error.get("error", ""):
        obtenido = "rechazada"
    elif "No encontré" in error.get("error", ""):
        obtenido = "no_encontrada"
    else:
        obtenido = "pregunta"
    nunca_bloqueada = not (app and app["id"] in BLOQUEADAS)
    ok = obtenido == esperado and nunca_bloqueada
    if not ok:
        fallos.append((nombre, esperado, obtenido))
    detalle = f" {error.get('coincidencias', '')}" if error and obtenido == "pregunta" else ""
    print(f"{'OK ' if ok else 'MAL'} {nombre!r:32} -> {obtenido}{detalle}")


if __name__ == "__main__":
    memoria.RUTA = BASE / "memoria_prueba_apps.db"
    memoria.RUTA.unlink(missing_ok=True)
    print(f"Apps bloqueadas en el catálogo: {sorted(categorias[i]['nombre'] for i in BLOQUEADAS)}\n")

    print("-- bloqueadas y genéricos sin alias")
    for nombre, esperado in [("editor", "pregunta"), ("el editor", "pregunta"), ("abre el editor", "pregunta"),
                             ("Editor del Registro", "bloqueada"), ("editor del registro", "bloqueada"),
                             ("regedit", "bloqueada"), ("regedit.exe", "bloqueada"), ("services.msc", "bloqueada"), ("Ejecutar", "bloqueada"),
                             ("Herramientas de Windows", "bloqueada"), ("msconfig", "bloqueada"), ("registro", "pregunta"), ("abre el registro", "pregunta"),
                             ("Servicios", "bloqueada"), ("Administración de equipos", "bloqueada"),
                             ("Programador de tareas", "bloqueada"), ("Directiva de seguridad local", "bloqueada"),
                             ("el navegador", "pregunta"), ("navegador", "pregunta"), ("juegos", "pregunta")]:
        probar(nombre, esperado)
    # cualquier variante aproximada de las bloqueadas tampoco puede llegar a ellas
    for nombre in ["editor registro", "editor de registro", "registro de windows", "servicio", "programador",
                   "tareas", "administracion", "equipos", "directivas", "taskschd", "ejecutar comando",
                   "herramientas windows", "herramientas", "configuracion del sistema"]:
        respuesta["valor"] = "n"
        app, _ = ns["preparar_apertura"](nombre, APPS)
        ok = not (app and app["id"] in BLOQUEADAS)
        if not ok:
            fallos.append((nombre, "nunca una bloqueada", app["nombre"]))
        print(f"{'OK ' if ok else 'MAL'} {nombre!r:32} -> {app['nombre'] if app else 'no abre'} (no bloqueada)")

    print("\n-- confirmar (consolas)")
    for nombre in ["PowerShell", "powershell", "Windows PowerShell", "Símbolo del sistema", "cmd", "Terminal",
                   "Developer PowerShell for VS 2022", "Git Bash", "Git CMD", "abre la terminal"]:
        probar(nombre, "rechazada", contestar="n")
    probar("Terminal", "Terminal", contestar="s")
    probar("Símbolo del sistema", "Símbolo del sistema", contestar="s")

    print("\n-- alias de memoria")
    probar("el editor", "pregunta")
    memoria.recordar("Cuando dice el editor se refiere a VS Code", "alias", "editor", "VS Code")
    probar("el editor", "Visual Studio Code")
    probar("editor", "Visual Studio Code")
    probar("mi editor", "Visual Studio Code")
    memoria.RUTA.unlink()
    memoria.recordar("Cuando dice el editor se refiere a VS Code", "alias")  # sin termino: usa el respaldo por texto
    probar("el editor", "Visual Studio Code")

    print("\n-- sin cambios respecto a antes")
    for nombre, esperado in [("WhatsApp", "WhatsApp"), ("spotify", "Spotify"), ("la calculadora", "Calculadora"),
                             ("chrome", "Google Chrome"), ("VS Code", "Visual Studio Code"), ("steam", "Steam"),
                             ("bloc de notas", "Bloc de notas"), ("firefox", "pregunta"), ("outlook", "pregunta"),
                             ("fotos", "Fotos"), ("OBS Studio", "OBS Studio (64bit)"), ("spotfy", "Spotify"),
                             ("edge", "Microsoft Edge"), ("teams", "Microsoft Teams"), ("discord", "Discord"),
                             ("word", "Word"), ("visual studio", "Visual Studio"), ("abre spotify", "Spotify"),
                             ("tareas", "pregunta"), ("el tiempo", "El Tiempo"), ("whatsapp beta", "WhatsApp Beta")]:
        probar(nombre, esperado)

    memoria.RUTA.unlink(missing_ok=True)
    print(f"\n{'TODO OK' if not fallos else f'{len(fallos)} fallos: {fallos}'}")
