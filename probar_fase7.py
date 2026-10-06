"""
Pruebas de la Fase 7 (isla). Sin modelo y sin tocar nada de Reizo.
  A. Simulación: confirmaciones con eventos de teclado y mouse simulados (físicos e inyectados), tiempo máximo de
     30 s, guarda de la herramienta mouse y el servidor WebSocket (token incorrecto, Origin distinto, segunda isla).
  B. Isla real (asistente-ui.exe), solo si no hay un juego activo: que no salga en listar_ventanas ni en ver_pantalla,
     que no tome el foco y que el agente no pueda hacer clic, enfocarla, cerrarla ni inspeccionarla. Se cierra al
     terminar; los sonidos van apagados durante la prueba.
Uso: .venv\\Scripts\\python probar_fase7.py [A] [B]
"""
import asyncio
import base64
import ctypes
import io
import json
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

import websockets

import entrada_fisica as ef
import herramientas_grupo1 as g1
import herramientas_grupo4 as g4
import ui_isla

BASE = Path(__file__).parent
EXE = Path(r"C:\asistente-ui\windows\target\release\asistente-ui.exe")
resultados = []
ZONA = (100, 0, 500, 200)  # isla simulada en la pantalla


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


# ---------- A. simulación ----------

class EntradaSimulada(ef.EntradaFisica):
    """La lógica real de entrada_fisica, sin instalar hooks: las pruebas le pasan los eventos."""

    def iniciar(self):
        EntradaSimulada.ultima = self
        return True

    def cerrar(self):
        pass


class ServidorFalso:
    def __init__(self):
        self.enviados, self.al_decidir, self.conectada = [], None, True

    def zonas_isla(self):
        return [ZONA]

    def enviar(self, m):
        self.enviados.append(m)
        return True


def confirmar_con(eventos, servidor=None, timeout_s=5):
    """Lanza Confirmar.pedir y, en paralelo, aplica 'eventos' (funciones que reciben la entrada simulada)."""
    c = ui_isla.Confirmar(servidor, timeout_s, entrada=lambda zonas, al: EntradaSimulada(zonas, al),
                          avisar=lambda *_: None)
    res = {}
    hilo = threading.Thread(target=lambda: res.update(si=c.pedir("teclado", "Escribir hola", "prueba")))
    hilo.start()
    time.sleep(0.2)
    for evento in eventos:
        evento(EntradaSimulada.ultima)
        time.sleep(0.1)
    hilo.join(timeout_s + 2)
    return res.get("si"), c.ultima


def tecla(vk, inyectada):
    return lambda e: e.procesar_tecla(vk, ef.WM_KEYDOWN, ef.LLKHF_INJECTED if inyectada else 0)


def clic(x, y, inyectado):
    def hacer(e):
        f = ef.LLMHF_INJECTED if inyectado else 0
        e.procesar_clic(ef.WM_LBUTTONDOWN, x, y, f)
        e.procesar_clic(ef.WM_LBUTTONUP, x, y, f)
    return hacer


def decision(servidor, si, id_=None):
    def hacer(_):
        ident = id_ or next(m["id"] for m in reversed(servidor.enviados) if m["tipo"] == "confirmar")
        servidor.al_decidir(ident, si)
    return hacer


def pruebas_confirmacion():
    si, u = confirmar_con([tecla(ef.VK_RETURN, True)], timeout_s=1)
    ok("Enter inyectado: se ignora (y la confirmación vence en no)", si is False and u["teclas_inyectadas"] == 1, u["via"])
    si, u = confirmar_con([tecla(ef.VK_RETURN, True), tecla(ef.VK_RETURN, False)])
    ok("Enter físico tras uno inyectado: sí", si is True and u["via"] == "teclado físico", u["via"])
    si, u = confirmar_con([tecla(ef.VK_ESCAPE, False)])
    ok("Esc físico: no", si is False and u["via"] == "teclado físico")
    e = ef.EntradaFisica()
    ok("Enter y Esc se consumen mientras se espera; otras teclas no",
       e.procesar_tecla(ef.VK_RETURN, ef.WM_KEYDOWN, 0) and e.procesar_tecla(ef.VK_ESCAPE, ef.WM_KEYDOWN, 0x10)
       and not e.procesar_tecla(0x41, ef.WM_KEYDOWN, 0))

    s = ServidorFalso()
    si, u = confirmar_con([clic(300, 50, True), decision(s, True)], s, timeout_s=1)
    rechazos = [m for m in s.enviados if m["tipo"] == "decision_rechazada"]
    ok("botón de la isla tras un clic inyectado: se rechaza", si is False and rechazos and u["clics_inyectados"] >= 1,
       rechazos[0]["motivo"] if rechazos else "")
    s = ServidorFalso()
    si, u = confirmar_con([clic(300, 50, False), decision(s, True)], s)
    ok("botón de la isla tras un clic físico: sí", si is True and u["via"].startswith("botón"), u["via"])
    s = ServidorFalso()
    si, u = confirmar_con([clic(800, 600, False), decision(s, True)], s, timeout_s=1)
    ok("clic físico fuera de la isla + decisión: se rechaza", si is False
       and any(m["tipo"] == "decision_rechazada" for m in s.enviados))
    s = ServidorFalso()
    si, u = confirmar_con([clic(300, 50, False), clic(300, 50, True), decision(s, True)], s, timeout_s=1)
    ok("si el último clic en la isla fue inyectado, no vale aunque antes hubiera uno físico", si is False)
    s = ServidorFalso()
    si, u = confirmar_con([clic(300, 50, False), decision(s, True, id_="viejo"), decision(s, False)], s)
    ok("decisión con un id viejo: se ignora; la buena (Denegar) vale", si is False and u["via"].startswith("botón"))
    ok("la isla recibe 'confirmar' y luego 'cancelar'", [m["tipo"] for m in s.enviados][0] == "confirmar"
       and s.enviados[-1]["tipo"] == "cancelar")

    t0 = time.monotonic()
    c = ui_isla.Confirmar(None, 30, entrada=lambda zonas, al: EntradaSimulada(zonas, al))
    si = c.pedir("teclado", "Escribir hola")
    duracion = time.monotonic() - t0
    ok("sin respuesta en 30 s: no", si is False and 29.9 <= duracion < 31.5 and "30 s" in c.ultima["via"],
       f"{duracion:.1f} s, {c.ultima['via']}")

    real = ef.EntradaFisica()
    instalados = real.iniciar()
    real.cerrar()
    ok("hooks reales de teclado y mouse: se instalan y se quitan", instalados and not real._hooks)


def pruebas_mouse():
    original = g4.zonas_isla
    g4.zonas_isla = lambda: [ZONA]
    try:
        captura = {"ancho": 1920, "alto": 1080, "origen": (0, 0), "escala": 1.0, "momento": time.time()}
        plan, error = g4.planificar_mouse("clic", 300, 50, captura=captura)
        ok("mouse: clic dentro de la isla, bloqueado", plan is None and error.get("bloqueado"), error and error["error"])
        plan, error = g4.planificar_mouse("doble_clic", 499, 199, captura=captura)
        ok("mouse: doble clic en el borde de la isla, bloqueado", plan is None and error.get("bloqueado"))
        plan, error = g4.planificar_mouse("clic", 900, 500, captura=captura)
        ok("mouse: clic fuera de la isla, permitido (solo el plan, no se hace)", plan is not None, str(plan))
    finally:
        g4.zonas_isla = original


async def _ws(puerto, token, origen):
    cabeceras = {"Origin": origen} if origen else {}
    try:
        async with websockets.connect(f"ws://127.0.0.1:{puerto}", additional_headers=cabeceras) as ws:
            await ws.send(json.dumps({"tipo": "hola", "token": token}))
            try:
                await asyncio.wait_for(ws.recv(), timeout=1)
            except asyncio.TimeoutError:
                return "abierta", ws
            except websockets.ConnectionClosed as e:
                return f"cerrada {e.rcvd.code if e.rcvd else ''}", None
    except websockets.InvalidStatus as e:
        return f"http {e.response.status_code}", None
    except websockets.ConnectionClosed as e:
        return f"cerrada {e.rcvd.code if e.rcvd else ''}", None
    return "cerrada", None


def pruebas_websocket():
    ruta = BASE / "ui_prueba.json"
    s = ui_isla.ServidorIsla(puerto=8766, ruta_conexion=ruta).iniciar()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    ok("ui.json con puerto y token de 32 bytes", datos["puerto"] == 8766 and len(datos["token"]) >= 40)
    tauri = "http://tauri.localhost"
    r, _ = asyncio.run(_ws(8766, "token-falso", tauri))
    ok("WebSocket: token incorrecto, cerrada", r == "cerrada 4001", r)
    r, _ = asyncio.run(_ws(8766, datos["token"], "http://pagina-maliciosa.example"))
    ok("WebSocket: Origin distinto, rechazada en el handshake", r == "http 403", r)
    r, _ = asyncio.run(_ws(8766, datos["token"], None))
    ok("WebSocket: sin Origin, rechazada", r == "http 403", r)

    async def isla_y_segunda():
        cab = {"Origin": tauri}
        async with websockets.connect("ws://127.0.0.1:8766", additional_headers=cab) as isla:
            await isla.send(json.dumps({"tipo": "hola", "token": datos["token"]}))
            await asyncio.sleep(0.3)
            conectada = s.conectada
            recibidas = []
            s.al_decidir = lambda i, si: recibidas.append((i, si))
            await isla.send(json.dumps({"tipo": "decision", "id": "abc", "si": True}))
            await isla.send(json.dumps({"tipo": "rect", "x": 240, "y": 0, "ancho": 240, "alto": 36, "escala": 1.25}))
            await asyncio.sleep(0.3)
            rect = dict(s.rect) if s.rect else None
            segunda = await _ws(8766, datos["token"], tauri)
            return conectada, recibidas, segunda[0], rect

    conectada, recibidas, segunda, rect = asyncio.run(isla_y_segunda())
    ok("WebSocket: token y Origin correctos, conectada", conectada)
    ok("WebSocket: la decisión de la isla llega al agente", recibidas == [("abc", True)])
    ok("WebSocket: la forma de la isla llega al agente", rect and rect["escala"] == 1.25, str(rect))
    ok("WebSocket: una segunda isla, rechazada", segunda == "cerrada 4002", segunda)
    s.cerrar()
    ok("al cerrar, ui.json se borra", not ruta.exists())


# ---------- B. isla real ----------

def pruebas_rechazo():
    """Un "no" de Reizo termina la tarea: el modelo (falso) intenta cerrar otra ventana y no llega a pedirlo."""
    import agente_minimo as a
    pasos = iter([{"pensamiento": "cierro la primera", "herramienta": "cerrar_app", "argumentos": {"id_ventana": 1}},
                  {"pensamiento": "rechazado; pruebo con la otra", "herramienta": "cerrar_app",
                   "argumentos": {"id_ventana": 2}},
                  {"pensamiento": "listo", "herramienta": "finalizar", "argumentos": {"mensaje": "cerré", "exito": True}}])
    preguntas, cerradas = [], []
    guardado = a.pedir_accion, a.confirmar, a.PLANIFICADORES, a.IMPLEMENTACIONES["cerrar_app"], a.notificar
    a.pedir_accion = lambda _h: next(pasos)
    a.confirmar = lambda *x, **k: preguntas.append(x) or False
    a.PLANIFICADORES = {}
    a.IMPLEMENTACIONES["cerrar_app"] = lambda **k: cerradas.append(k) or {"ok": True}
    a.notificar = lambda *x, **k: None
    try:
        respuesta = a.atender("cierra la calculadora", [{"role": "system", "content": ""}])
    finally:
        a.pedir_accion, a.confirmar, a.PLANIFICADORES, a.IMPLEMENTACIONES["cerrar_app"], a.notificar = guardado
    ok("rechazo: tras Denegar no intenta otra ventana", len(preguntas) == 1 and not cerradas,
       f"{len(preguntas)} preguntas, {len(cerradas)} cierres")
    ok("rechazo: responde que no lo hizo", respuesta.startswith("No lo hice"), respuesta)


def pruebas_isla_real():
    import guardia_juego
    juego = guardia_juego.juego_abierto()
    if juego:
        ok(f"isla real: no se abre porque {juego} está activo", True)
        return
    if not EXE.is_file():
        ok("isla real: falta asistente-ui.exe", False)
        return
    ajustes = Path(os.environ["APPDATA"]) / "Asistente" / "settings.json"
    previo = ajustes.read_text(encoding="utf-8") if ajustes.exists() else None
    ajustes.parent.mkdir(parents=True, exist_ok=True)
    ajustes.write_text(json.dumps({"soundEnabled": False, "soundVolume": 0.12, "autoCloseInterval": 15,
                                   "absenceInterval": 180, "screen": "primary", "autostart": False,
                                   "permitirCaptura": False}), encoding="utf-8")
    s = ui_isla.ServidorIsla().iniciar()
    frente_antes = ctypes.windll.user32.GetForegroundWindow()
    proceso = subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
    try:
        limite = time.monotonic() + 30
        while not (s.conectada and s.rect) and time.monotonic() < limite:
            time.sleep(0.2)
        ok("isla real: arranca y se conecta al agente con el token", s.conectada, f"rect {s.rect}")
        ventanas = ui_isla.ventanas_isla()
        hwnd = ventanas[0] if ventanas else None
        ok("isla real: tiene su ventana", hwnd is not None)
        if hwnd is None:
            return
        afinidad = wintypes.DWORD()
        ctypes.windll.user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(afinidad))
        ok("isla real: excluida de capturas (WDA_EXCLUDEFROMCAPTURE)", afinidad.value == 0x11, hex(afinidad.value))
        estilo = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ok("isla real: no se activa ni sale en Alt-Tab (NOACTIVATE + TOOLWINDOW)",
           estilo & 0x08000000 and estilo & 0x80, hex(estilo & 0xFFFFFFFF))
        procesos = [v["proceso"].lower() for v in g1.listar_ventanas()]
        ok("isla real: no sale en listar_ventanas", "asistente-ui.exe" not in procesos)
        # una confirmación abre la tarjeta en la isla: no debe quitar el foco a la ventana activa
        s.enviar({"tipo": "confirmar", "id": "prueba", "herramienta": "teclado", "resumen": "Prueba", "motivo": "prueba"})
        time.sleep(1.5)
        frente = ctypes.windll.user32.GetForegroundWindow()
        ok("isla real: mostrar la tarjeta no toma el foco", frente != hwnd and frente == frente_antes or frente != hwnd,
           f"antes {frente_antes}, ahora {frente}")
        s.enviar({"tipo": "cancelar", "id": "prueba"})

        import vision
        vision.zonas_isla = s.zonas_isla
        data_url, info = vision.capturar("completa")
        from PIL import Image
        imagen = Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1])))
        izq, arr, der, aba = s.zonas_isla()[0]
        e, (ox, oy) = info["escala"], info["origen"]
        caja = (int((izq - ox) * e) + 2, int((arr - oy) * e) + 2, int((der - ox) * e) - 2, int((aba - oy) * e) - 2)
        recorte = imagen.crop(caja).convert("L")
        ok("isla real: tapada en ver_pantalla (zona en negro)", max(recorte.getdata()) <= 40,
           f"zona {caja}, brillo máximo {max(recorte.getdata())}")
        del imagen

        captura = {"ancho": 4000, "alto": 3000, "origen": (0, 0), "escala": 1.0, "momento": time.time()}
        g4.zonas_isla = s.zonas_isla
        cx, cy = (izq + der) // 2, (arr + aba) // 2
        plan, error = g4.planificar_mouse("clic", cx, cy, captura=captura)
        ok("isla real: mouse en el centro de la isla, bloqueado", error and error.get("bloqueado"), error and error["error"])
        plan, error = g4.planificar_mouse("clic", control="Permitir", id_ventana=hwnd)
        ok("isla real: clic por control en la isla, bloqueado", error and error.get("bloqueado"))
        r = g1.enfocar_ventana(hwnd)
        ok("isla real: enfocar_ventana, bloqueado", r.get("bloqueado"), r.get("error"))
        plan, error = g4.planificar_cierre(proceso="asistente-ui")
        ok("isla real: cerrar_app, bloqueado", error and error.get("bloqueado"))
        controles = g4.listar_controles(hwnd)
        ok("isla real: listar_controles, bloqueado", isinstance(controles, dict) and controles.get("bloqueado"))
    finally:
        proceso.terminate()
        proceso.wait(10)
        s.cerrar()
        if previo is None:
            ajustes.unlink(missing_ok=True)
        else:
            ajustes.write_text(previo, encoding="utf-8")
        time.sleep(1)
        ok("isla real: cerrada al terminar (sin procesos ni ui.json)", not ui_isla.ventanas_isla()
           and proceso.poll() is not None and not ui_isla.RUTA_CONEXION.exists())


if __name__ == "__main__":
    partes = sys.argv[1:] or ["A", "B"]
    if "A" in partes:
        print("== A. simulación ==")
        pruebas_confirmacion()
        pruebas_mouse()
        pruebas_websocket()
        pruebas_rechazo()
    if "B" in partes:
        print("\n== B. isla real ==")
        pruebas_isla_real()
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
