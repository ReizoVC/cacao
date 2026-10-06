"""
Pruebas sin modelo del campo de texto de la isla, lado del agente:
  1. ServidorIsla: un pedido de la isla llega a al_pedido solo tras el saludo con el token correcto;
  2. ColaPedidos: texto limpio y recortado, consola e isla en la misma cola, la consola solo pregunta cuando toca;
  3. bucle_texto (agente_minimo, extraído con ast): el texto de la isla va por el mismo camino que el de la consola
     (atender_con_memoria), y "reanudar" / "salir" funcionan igual;
  4. modo voz (escuchar/esperar_disparo de voz.py, extraídas con ast): un pedido escrito entra sin audio ni
     Whisper, y la confirmación por voz no se come los pedidos de la isla;
  5. teclado: se niega a escribir con la isla al frente (bloqueo, sin pulsar nada) y el ejecutor no llega a pedir
     confirmación, ni con el modo sin confirmación.
La parte de la isla (foco, Enter/Esc/clic fuera, botones) se prueba en C:\\asistente-ui: src-tauri/src/foco.rs y
scripts/probar-campo.mjs.
Uso: .venv\\Scripts\\python probar_campo_isla.py
"""
import ast
import asyncio
import json
import queue
import sys
import tempfile
import threading
import time
import types
from pathlib import Path

import websockets

import herramientas_grupo4 as g4
import pedidos
import ui_isla

BASE = Path(__file__).parent
resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


# ---------- 1. servidor ----------

def pruebas_servidor():
    tmp = Path(tempfile.mkdtemp())
    recibidos = []
    s = ui_isla.ServidorIsla(puerto=8797, ruta_conexion=tmp / "ui.json")
    s.al_pedido = recibidos.append
    s.iniciar()
    origen = {"Origin": "http://tauri.localhost"}

    async def cliente(mensajes, token):
        async with websockets.connect("ws://127.0.0.1:8797", additional_headers=origen) as ws:
            if token is not None:
                await ws.send(json.dumps({"tipo": "hola", "token": token, "version": 1}))
            for m in mensajes:
                await ws.send(json.dumps(m))
            await asyncio.sleep(0.3)

    def correr(mensajes, token):
        try:
            asyncio.run(cliente(mensajes, token))
        except websockets.ConnectionClosed:
            pass

    correr([{"tipo": "pedido", "texto": "abre la calculadora"}], s.token)
    ok("servidor: el pedido de la isla llega a al_pedido", recibidos == ["abre la calculadora"], recibidos)
    recibidos.clear()
    correr([{"tipo": "pedido", "texto": "abre regedit"}], "token-falso" * 4)
    ok("servidor: con un token incorrecto, nada", not recibidos, recibidos)
    correr([], None)
    ok("servidor: sin saludo, nada", not recibidos)
    s.cerrar()


# ---------- 2. cola ----------

def pruebas_cola():
    ok("cola: espacios de más se normalizan", pedidos.limpiar("  sube   el volumen \n") == "sube el volumen")
    ok("cola: vacío o no texto, se descarta", pedidos.limpiar("   ") is None and pedidos.limpiar(42) is None
       and pedidos.limpiar(None) is None)
    ok("cola: recortado a 2000 caracteres", len(pedidos.limpiar("x" * 5000)) == pedidos.MAX_PEDIDO)

    entradas = queue.Queue()
    leidas = []

    def leer(_prompt):
        texto = entradas.get()
        if texto is EOFError:
            raise EOFError
        leidas.append(texto)
        return texto

    c = pedidos.ColaPedidos(leer=leer).iniciar_consola()
    entradas.put("hola")
    time.sleep(0.2)
    ok("cola: la consola no pregunta hasta que el bucle está listo", not leidas)
    c.listo()
    ok("cola: pedido de la consola", c.siguiente(timeout=2) == ("consola", "hola"))
    c.desde_isla("abre spotify")
    c.desde_isla("   ")
    ok("cola: pedido de la isla, en la misma cola", c.siguiente(timeout=2) == ("isla", "abre spotify"))
    ok("cola: un texto vacío de la isla no entra", c.siguiente(timeout=0.4) is None)
    c.listo()
    entradas.put(EOFError)
    ok("cola: cerrar la consola termina", c.siguiente(timeout=2) == ("fin", None))
    v = pedidos.ColaPedidos()
    v.desde_isla("baja el volumen")
    ok("cola (voz): pedido_isla lo entrega y luego no hay más", v.pedido_isla() == "baja el volumen"
       and v.pedido_isla() is None)


# ---------- 3. bucle de texto ----------

def cargar_bucle(atendidos, reanudados):
    arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
    nodo = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "bucle_texto")
    ns = {"print": lambda *a, **k: None,
          "atender_con_memoria": lambda pedido, historial, planificador: atendidos.append(pedido) or f"hecho: {pedido}",
          "emergencia": types.SimpleNamespace(reanudar=lambda: reanudados.append(True))}
    exec(compile(ast.Module(body=[nodo], type_ignores=[]), "agente_minimo.py", "exec"), ns)
    return ns["bucle_texto"]


class ColaFalsa:
    def __init__(self, items):
        self.items = list(items)

    def listo(self):
        pass

    def siguiente(self, timeout=None):
        return self.items.pop(0) if self.items else ("fin", None)


def pruebas_bucle():
    atendidos, reanudados = [], []
    bucle = cargar_bucle(atendidos, reanudados)
    bucle(ColaFalsa([("consola", "abre la calculadora"), ("isla", "abre la calculadora"), ("isla", "reanudar"),
                     ("isla", "  "), ("isla", "salir"), ("consola", "no debería llegar")]), [{}], None)
    ok("bucle: el texto de la isla va por atender_con_memoria, igual que la consola",
       atendidos == ["abre la calculadora", "abre la calculadora"], atendidos)
    ok("bucle: 'reanudar' desde la isla reanuda", reanudados == [True])
    ok("bucle: 'salir' termina (lo que viene después no se atiende)", "no debería llegar" not in atendidos)
    fuente = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
    ok("agente: el servidor de la isla manda sus pedidos a la cola", "_isla.al_pedido = cola_pedidos.desde_isla" in fuente)
    ok("agente: el modo texto usa bucle_texto", "bucle_texto(cola_pedidos, historial, planificador)" in fuente)


# ---------- 4. modo voz ----------

def pruebas_voz():
    import probar_palabra_activacion as ppa
    ns, escucha, transcriptor, _ = ppa.cargar_voz_sin_modelo(None, "no debería transcribirse", None)
    ns["a"].cola_pedidos.desde_isla("pon el volumen al 30")

    class Atajo:
        pulsado = threading.Event()

    audio, datos, texto, _ = ns["escuchar"](Atajo(), None, transcriptor)
    ok("voz: un pedido escrito en la isla entra sin audio ni transcripción", audio is None and
       texto == "pon el volumen al 30" and datos.get("disparo") == "isla", str(datos))
    ns["a"].cola_pedidos.desde_isla("abre spotify")
    ok("voz: la confirmación por voz (esperar_disparo sin isla) no se come los pedidos de la isla",
       ns["esperar_disparo"](Atajo(), 0.3) is None and ns["a"].cola_pedidos.pedido_isla() == "abre spotify")
    fuente = (BASE / "voz.py").read_text(encoding="utf-8")
    ok("voz: el pedido de la isla sigue por atender_con_memoria (voz=True), como lo dicho",
       "respuesta = a.atender_con_memoria(texto, historial, planificador, voz=True)" in fuente)


# ---------- 5. teclado ----------

def pruebas_teclado():
    enviados = []
    guardado = g4.isla_al_frente, g4._enviar, g4._pegar, g4.estado_despues
    g4._enviar = lambda *a, **k: enviados.append(a or k)
    g4._pegar = lambda texto: enviados.append(texto) or False
    g4.estado_despues = lambda: {}
    try:
        g4.isla_al_frente = lambda: True
        r1 = g4.teclado("escribir", texto="abre regedit")
        r2 = g4.teclado("atajo", teclas=["ctrl", "v"])
        r3 = g4.teclado("tecla", teclas=["enter"])
        ok("teclado: con la isla al frente se niega a escribir (bloqueo)", r1.get("bloqueado") and "isla" in r1["error"], r1)
        ok("teclado: tampoco pulsa atajos ni teclas en la isla", r2.get("bloqueado") and r3.get("bloqueado"))
        ok("teclado: no se envió ninguna pulsación", not enviados, enviados)
        _, error = g4.planificar_teclado_ventana()
        ok("teclado: el planificador también lo bloquea (antes de pedir confirmación)", error and error["bloqueado"])
        g4.isla_al_frente = lambda: False
        ok("teclado: con otra ventana al frente, sí escribe", g4.teclado("escribir", texto="hola").get("ok")
           and enviados == ["hola"], enviados)
        # la detección real: el proceso de la ventana al frente es asistente-ui.exe
        guardado_frente, guardado_isla = g4.win32gui.GetForegroundWindow, g4.es_de_la_isla
        g4.win32gui.GetForegroundWindow = lambda: 4242
        g4.es_de_la_isla = lambda hwnd: hwnd == 4242
        g4.isla_al_frente = guardado[0]
        ok("teclado: isla_al_frente reconoce la ventana de la isla", g4.isla_al_frente())
        g4.win32gui.GetForegroundWindow, g4.es_de_la_isla = guardado_frente, guardado_isla
    finally:
        g4.isla_al_frente, g4._enviar, g4._pegar, g4.estado_despues = guardado

    import probar_modo_directo as pmd
    for modo in (False, True):
        ns = pmd.cargar_ejecutor()
        ns["PLANIFICADORES"]["teclado"] = lambda args: (None, {"ok": False, "bloqueado": True, "error": "isla"})
        ns["_modos"]["sin_confirmacion"] = modo
        ns["_tarea"].update(pedido="escribe abre regedit en la isla", herramientas=[], movidos=0)
        r = ns["ejecutar"]("teclado", {"accion": "escribir", "texto": "abre regedit"})
        ok(f"ejecutor ({'modo sin confirmación' if modo else 'normal'}): bloqueado sin preguntar ni escribir",
           r.get("bloqueado") and not ns["preguntas"] and not ns["llamadas"])
    fuente = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
    ok("agente: teclado tiene planificador de ventana",
       '"teclado": lambda args: herramientas_grupo4.planificar_teclado_ventana()' in fuente)


if __name__ == "__main__":
    for parte in (pruebas_servidor, pruebas_cola, pruebas_bucle, pruebas_voz, pruebas_teclado):
        print(f"\n== {parte.__name__} ==", flush=True)
        parte()
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
