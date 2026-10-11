"""
Pruebas de Cacao en segundo plano (sin terminal), sin modelo ni GPU:
  1. iniciar_cacao.py: el agente corre con python.exe sin ventana y su salida (también la de código nativo) va al
     registro; si sale con un error, aviso de Windows y línea en el registro; si sale bien, sin aviso; no abre un
     segundo Cacao; rota el registro a los 5 MB; --simular no carga nada. Usa un voz.py falso (no Gemma).
  2. avisos_windows: el texto va escapado dentro del XML y de la orden de PowerShell.
  3. confirmaciones: en segundo plano y sin la isla conectada, la respuesta es no al momento (no hay dónde ver la
     pregunta); con la isla conectada se pregunta como siempre.
  4. bandeja: los mensajes «salir» y «ver_terminal» de la isla llegan al agente; «Salir de Cacao» entra como el
     pedido "salir" (la salida limpia de siempre); la ventana de «Ver terminal» es otro proceso con su consola.
Uso: .venv\\Scripts\\python probar_segundo_plano.py   (--aviso-real muestra además una notificación de verdad)
"""
import ast
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

import websockets

import avisos_windows
import iniciar_cacao
import pedidos
import ui_isla

BASE = Path(__file__).parent
resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


def pruebas_lanzador():
    tmp = Path(tempfile.mkdtemp(prefix="cacao_fondo_"))
    script, original = tmp / "voz_falso.py", iniciar_cacao.SCRIPT
    try:
        iniciar_cacao.SCRIPT = script
        registro = tmp / "registro_cacao.log"
        avisos = []
        script.write_text(
            "import os, sys\n"
            "print('Cacao listo, ñandú', flush=True)\n"
            "os.write(2, b'mensaje nativo de llama.cpp\\n')\n"  # como el código en C, directo al descriptor 2
            "print('ESPERAR_JUEGO=' + os.environ.get('ESPERAR_JUEGO', ''), "
            "'SEGUNDO_PLANO=' + os.environ.get('CACAO_SEGUNDO_PLANO', ''))\n"
            "sys.exit(int(os.environ.get('CODIGO', '0')))\n", encoding="utf-8")
        codigo = iniciar_cacao.lanzar(registro, avisar=lambda t, x: avisos.append((t, x)))
        texto = registro.read_text(encoding="utf-8")
        ok("sale bien: código 0 y sin aviso", codigo == 0 and not avisos, codigo)
        ok("la salida va al registro (también la nativa y con tildes)", "Cacao listo, ñandú" in texto
           and "mensaje nativo de llama.cpp" in texto, texto[-200:])
        ok("el agente recibe ESPERAR_JUEGO=1 y CACAO_SEGUNDO_PLANO=1", "ESPERAR_JUEGO=1 SEGUNDO_PLANO=1" in texto)
        ok("el registro marca el arranque y el final", "Cacao arranca" in texto and "Cacao terminó" in texto)
        os.environ["CODIGO"] = "3"
        try:
            codigo = iniciar_cacao.lanzar(registro, avisar=lambda t, x: avisos.append((t, x)))
        finally:
            del os.environ["CODIGO"]
        ok("sale con un error: aviso de Windows y línea en el registro", codigo == 3 and len(avisos) == 1
           and "error" in avisos[0][0] and "código 3" in registro.read_text(encoding="utf-8"), avisos)

        llamadas = []

        class Proceso:
            def wait(self):
                return 0

        iniciar_cacao.lanzar(registro, popen=lambda *a, **k: llamadas.append(k) or Proceso(), avisar=lambda *a: None)
        ok("python.exe sin ventana (CREATE_NO_WINDOW) y sin entrada", llamadas
           and llamadas[0]["creationflags"] == iniciar_cacao.CREATE_NO_WINDOW
           and llamadas[0]["stdin"] == subprocess.DEVNULL and llamadas[0]["stderr"] == subprocess.STDOUT)
        ok("con python.exe del .venv (no pythonw: la consola oculta la heredan los PowerShell)",
           iniciar_cacao.PYTHON.name == "python.exe")

        grande = tmp / "grande.log"
        grande.write_bytes(b"x" * 2048)
        iniciar_cacao.rotar(grande, maximo=1024)
        ok("registro de más de 5 MB: se guarda como .1 y empieza otro", not grande.exists()
           and (tmp / "grande.1.log").exists())
    finally:
        iniciar_cacao.SCRIPT = original

    yo = os.getpid()
    base = str(iniciar_cacao.BASE)
    procesos = [types.SimpleNamespace(info={"pid": 10, "name": "python.exe", "exe": base + r"\.venv\Scripts\python.exe",
                                            "cmdline": ["python.exe", base + r"\voz.py"]}),
                types.SimpleNamespace(info={"pid": 11, "name": "pythonw.exe", "exe": "x",
                                            "cmdline": ["pythonw.exe", base + r"\registro_habitos.py"]}),
                types.SimpleNamespace(info={"pid": yo, "name": "python.exe", "exe": "x",
                                            "cmdline": ["python.exe", base + r"\voz.py"]})]
    ok("un Cacao en marcha se reconoce (el registro de hábitos y el propio lanzador no)",
       iniciar_cacao.cacao_en_marcha(procesos) == [10])
    r = subprocess.run([sys.executable, str(BASE / "iniciar_cacao.py"), "--simular"], capture_output=True,
                       text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=60)
    ok("--simular: comprueba sin cargar nada", r.returncode == 0 and "[simulación] Faltan: nada" in r.stdout
       and "sin ventana" in r.stdout, r.stdout[-300:] + r.stderr[-300:])


def pruebas_avisos():
    s = avisos_windows.script("Cacao <se cerró>", "Código 3 & 'algo'")
    ok("aviso: el texto va escapado en el XML", "&lt;se cerró&gt;" in s and "&amp;" in s)
    ok("aviso: las comillas simples no rompen la orden de PowerShell", "''algo''" in s or "&#x27;" in s, s[200:320])
    orden = []
    avisos_windows.notificar("t", "x", ejecutar=lambda a, **k: orden.append((a, k)) or types.SimpleNamespace(
        returncode=0))
    ok("aviso: PowerShell sin ventana", orden and orden[0][1]["creationflags"] == avisos_windows.CREATE_NO_WINDOW)
    if "--aviso-real" in sys.argv:
        ok("aviso real mostrado (míralo en la esquina de la pantalla)",
           avisos_windows.notificar("Cacao: prueba", "Esto es una prueba de las notificaciones de Cacao."))


def cargar_confirmar(segundo_plano, isla):
    arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
    nodos = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "confirmar"]
    preguntas = []

    class Confirmar:
        ultima = {"via": "teclado físico"}

        def pedir(self, *a, **k):
            preguntas.append(a)
            return True

    ns = {"SEGUNDO_PLANO": segundo_plano, "_isla": isla, "_confirmacion": Confirmar(), "_confirmar_extra": None,
          "CONFIG": {}, "print": lambda *a, **k: None}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "agente_minimo.py", "exec"), ns)
    return ns["confirmar"], preguntas


def pruebas_confirmar():
    conectada = types.SimpleNamespace(conectada=True)
    for isla, cual in ((None, "sin isla"), (types.SimpleNamespace(conectada=False), "con la isla desconectada")):
        confirmar, preguntas = cargar_confirmar(True, isla)
        t0 = time.perf_counter()
        si = confirmar("teclado", "Ejecutar teclado")
        ok(f"segundo plano, {cual}: no, al momento y sin preguntar", si is False and not preguntas
           and time.perf_counter() - t0 < 0.5)
    confirmar, preguntas = cargar_confirmar(True, conectada)
    ok("segundo plano con la isla conectada: pregunta como siempre", confirmar("teclado", "x") is True
       and len(preguntas) == 1)
    confirmar, preguntas = cargar_confirmar(False, None)
    ok("en una terminal (no segundo plano), sin isla: pregunta por Enter/Esc como antes",
       confirmar("teclado", "x") is True and len(preguntas) == 1)
    fuente = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
    ok("el segundo plano lo marca el lanzador (CACAO_SEGUNDO_PLANO)",
       'SEGUNDO_PLANO = os.environ.get("CACAO_SEGUNDO_PLANO") == "1"' in fuente)


def pruebas_bandeja():
    ruta = BASE / "ui_prueba_fondo.json"
    s = ui_isla.ServidorIsla(puerto=8767, ruta_conexion=ruta).iniciar()
    token = json.loads(ruta.read_text(encoding="utf-8"))["token"]
    cola = pedidos.ColaPedidos(leer=lambda _: "")
    terminales = []
    s.al_salir = lambda: cola.desde_isla("salir")  # lo mismo que agente_minimo.iniciar_isla
    s.al_ver_terminal = lambda: terminales.append(1)

    async def isla():
        async with websockets.connect("ws://127.0.0.1:8767",
                                      additional_headers={"Origin": "http://tauri.localhost"}) as ws:
            await ws.send(json.dumps({"tipo": "hola", "token": token, "version": ui_isla.PROTOCOLO}))
            await asyncio.sleep(0.3)
            await ws.send(json.dumps({"tipo": "ver_terminal"}))
            await ws.send(json.dumps({"tipo": "salir"}))
            await asyncio.sleep(0.3)

    try:
        asyncio.run(isla())
    finally:
        s.cerrar()
    ok("bandeja → «Ver terminal» llega al agente", terminales == [1])
    ok("bandeja → «Salir de Cacao» entra como el pedido «salir» (salida limpia: isla, micrófono, modelo, ui.json)",
       cola.pedido_isla() == "salir")
    ok("al cerrar el servidor se borra ui.json", not ruta.exists())
    fuente = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
    funcion = fuente.split("def ver_terminal", 1)[1].split("\ndef ", 1)[0]
    ok("«Ver terminal» abre otro proceso con su propia consola (cerrarla no cierra Cacao)",
       "CREATE_NEW_CONSOLE" in funcion and "Get-Content" in funcion and "-Wait" in funcion and "-Tail" in funcion)
    voz = (BASE / "voz.py").read_text(encoding="utf-8")
    ok("voz.py: el pedido «salir» cierra limpio (atajo, micrófono, isla y transcriptor en el finally)",
       'orden in ("salir", "salir del modo voz")' in voz and "a.cerrar_isla()" in voz and "microfono.cerrar()" in voz)


if __name__ == "__main__":
    for parte in (pruebas_lanzador, pruebas_avisos, pruebas_confirmar, pruebas_bandeja):
        print(f"\n== {parte.__name__} ==")
        parte()
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
