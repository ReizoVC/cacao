"""
Fase 7: conexión con la isla (C:\\asistente-ui) y confirmaciones con entrada física (diseno_fase7.md §4 y §6).

Servidor WebSocket (el agente es el servidor):
  - solo en 127.0.0.1:8765;
  - token por sesión: 32 bytes aleatorios que el agente escribe al arrancar en %LOCALAPPDATA%\\Asistente\\ui.json
    (carpeta del usuario). La isla lo lee con un comando de Tauri (leer_conexion) y lo manda en su primer mensaje;
    si no coincide, se cierra la conexión (4001). El archivo se borra al salir;
  - Origin: solo el del webview de Tauri (http://tauri.localhost, https://tauri.localhost) y, en desarrollo,
    http://localhost:1420. Cualquier otro (una página web abierta en el navegador) recibe 403 en el handshake;
  - una sola isla a la vez (4002 para la segunda);
  - protocolo versión PROTOCOLO en «hola» (4003 si es otra); un JSON que no es un objeto se ignora.

Música (protocolo v3): {"tipo": "musica", "reproduciendo": bool} dice si Windows reproduce algo. Solo se guarda un
booleano exacto en self.musica (None: desconocido) y es informativo: nunca relaja un freno (la confirmación por voz
sigue usando confirmacion_voz.otro_audio_sonando).

Pedidos escritos: {"tipo": "pedido", "texto"} del campo de texto de la isla (solo se puede escribir en él tras un
clic físico) van a al_pedido, que los pone en la misma cola que la consola (pedidos.py).

Confirmar.pedir(): "sí" solo con Enter físico o con Permitir en la isla tras un clic físico dentro de ella
(entrada_fisica.py); "no" con Esc físico, Denegar (también con clic físico), 30 s sin respuesta o el atajo de
emergencia. Sin isla conectada, solo Enter/Esc.

zonas_isla(): dónde está la isla en la pantalla, para que la herramienta mouse no pueda hacer clic dentro.
"""
import asyncio
import atexit
import ctypes
import hmac
import json
import os
import secrets
import threading
import time
import uuid
from ctypes import wintypes
from pathlib import Path

import websockets
from websockets.asyncio.server import serve

from entrada_fisica import EntradaFisica

PUERTO = 8765
# versión de C:\asistente-ui\docs\protocolo.md; la isla la manda en «hola» y otra versión se rechaza (4003)
PROTOCOLO = 3
PROCESO_ISLA = "asistente-ui.exe"
ORIGENES = ["http://tauri.localhost", "https://tauri.localhost", "http://localhost:1420"]
RUTA_CONEXION = Path(os.environ.get("LOCALAPPDATA", ".")) / "Asistente" / "ui.json"
user32 = ctypes.windll.user32


def ventanas_isla():
    """hwnd de las ventanas de primer nivel del proceso de la isla."""
    import psutil
    pids = {p.pid for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == PROCESO_ISLA}
    encontradas = []
    if not pids:
        return encontradas

    def revisar(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            izq, arriba, der, abajo = rect_ventana(hwnd)
            if der - izq >= 100 and abajo - arriba >= 4:  # Tauri tiene además ventanitas de 16x16 sin contenido
                encontradas.append(hwnd)
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(revisar), 0)
    return encontradas


def rect_ventana(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


class ServidorIsla:
    def __init__(self, puerto=PUERTO, ruta_conexion=RUTA_CONEXION, origenes=ORIGENES, anotar=lambda *_: None):
        self.puerto, self.ruta_conexion, self.origenes, self.anotar = puerto, Path(ruta_conexion), origenes, anotar
        self.token = None
        self.cliente = None
        self.rect = None          # forma de la isla que manda el webview (px CSS de la ventana) y su escala
        self.musica = None        # True/False si Windows reproduce algo (protocolo v3); None: desconocido. Informativo
        self.al_decidir = None    # función(id, si) que pone Confirmar
        self.al_cambiar_modo = None  # función(modo, fisico, origen): solo el agente cambia sus modos
        self.al_conectar = None   # función() al conectarse la isla (el agente le manda sus modos)
        self.al_pedido = None     # función(texto) con lo escrito en el campo de la isla (pedidos.ColaPedidos)
        self.al_salir = None      # función() de «Salir de Cacao» en la bandeja (la isla ya comprobó el clic físico)
        self.al_ver_terminal = None  # función() de «Ver terminal» en la bandeja
        self.rechazos = []        # (motivo) de conexiones rechazadas, para las pruebas y el registro
        self._loop = None
        self._hilo = None
        self._listo = threading.Event()
        self._parar = None

    # ----- ciclo de vida -----

    def iniciar(self):
        self.token = secrets.token_urlsafe(32)
        self.ruta_conexion.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_conexion.write_text(json.dumps({"puerto": self.puerto, "token": self.token}), encoding="utf-8")
        atexit.register(self.ruta_conexion.unlink, missing_ok=True)  # también si el agente sale con un error
        self._hilo = threading.Thread(target=self._correr, name="servidor-isla", daemon=True)
        self._hilo.start()
        self._listo.wait(5)
        return self

    def cerrar(self):
        if self._loop and self._parar:
            self._loop.call_soon_threadsafe(self._parar.set)
            self._hilo.join(5)
        self.ruta_conexion.unlink(missing_ok=True)

    def _correr(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._servir())

    async def _servir(self):
        self._parar = asyncio.Event()
        async with serve(self._atender, "127.0.0.1", self.puerto, origins=self.origenes,
                         process_request=self._revisar_origen):
            self._listo.set()
            await self._parar.wait()

    def _revisar_origen(self, conexion, peticion):
        origen = peticion.headers.get("Origin")
        if origen not in self.origenes:
            self.rechazos.append(f"origin {origen}")
            return conexion.respond(403, "Origen no permitido\n")
        return None

    # ----- conexión -----

    async def _atender(self, ws):
        try:
            hola = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        except (asyncio.TimeoutError, ValueError, websockets.ConnectionClosed):
            self.rechazos.append("sin hola")
            await ws.close(4001, "sin token")
            return
        if not isinstance(hola, dict):
            self.rechazos.append("sin hola")
            await ws.close(4001, "sin token")
            return
        if hola.get("tipo") != "hola" or not hmac.compare_digest(str(hola.get("token", "")), self.token):
            self.rechazos.append("token")
            await ws.close(4001, "token incorrecto")
            return
        if hola.get("version") != PROTOCOLO:  # después del token: a quien no lo tiene no se le dice la versión
            self.rechazos.append(f"version {hola.get('version')!r}")
            await ws.close(4003, f"versión de protocolo distinta: espero {PROTOCOLO}")
            return
        if self.cliente is not None:
            self.rechazos.append("segunda isla")
            await ws.close(4002, "ya hay una isla conectada")
            return
        self.cliente = ws
        self.anotar("[isla] conectada")
        if self.al_conectar:
            self.al_conectar()
        try:
            async for crudo in ws:
                try:
                    m = json.loads(crudo)
                except ValueError:
                    continue
                if not isinstance(m, dict):  # un JSON que no es un objeto se ignora (antes cerraba con 1011)
                    continue
                if m.get("tipo") == "decision" and self.al_decidir:
                    self.al_decidir(str(m.get("id")), bool(m.get("si")))
                elif m.get("tipo") == "modo" and self.al_cambiar_modo:
                    # 'fisico' lo calcula la isla con su hook de mouse (LLMHF_INJECTED); sin él no vale
                    self.al_cambiar_modo(str(m.get("modo")), m.get("fisico") is True,
                                         "bandeja" if m.get("origen") == "bandeja" else "isla")
                elif m.get("tipo") == "pedido" and self.al_pedido:
                    self.al_pedido(m.get("texto"))
                elif m.get("tipo") == "salir" and self.al_salir:
                    self.al_salir()
                elif m.get("tipo") == "ver_terminal" and self.al_ver_terminal:
                    self.al_ver_terminal()
                elif m.get("tipo") == "rect":
                    try:
                        self.rect = {k: float(m.get(k, 0)) for k in ("x", "y", "ancho", "alto", "escala")}
                    except (TypeError, ValueError):
                        continue  # un rect con valores que no son números se ignora; queda la forma anterior
                elif m.get("tipo") == "musica":
                    # solo un booleano exacto («true», 1 o null se ignoran); nada más del mensaje se lee ni se guarda
                    if isinstance(m.get("reproduciendo"), bool):
                        self.musica = m["reproduciendo"]
        except websockets.ConnectionClosed:
            pass
        finally:
            if self.cliente is ws:
                self.cliente = None
                self.rect = None
                self.musica = None
                self.anotar("[isla] desconectada")

    @property
    def conectada(self):
        return self.cliente is not None

    def enviar(self, mensaje):
        if self.cliente is None or self._loop is None:
            return False
        asyncio.run_coroutine_threadsafe(self.cliente.send(json.dumps(mensaje, ensure_ascii=False)), self._loop)
        return True

    def estado(self, nombre, detalle=""):
        self.enviar({"tipo": "estado", "estado": nombre, "detalle": detalle[:120]})

    # ----- dónde está la isla -----

    def zonas_isla(self, ventanas=ventanas_isla):
        """[(izq, arriba, der, abajo)] en píxeles de pantalla: la forma de la isla si el webview la mandó (con 14 px
        de margen, como su hit-test), o la ventana entera si no."""
        zonas = []
        for hwnd in ventanas():
            izq, arriba, der, abajo = rect_ventana(hwnd)
            if self.rect:
                e, m = self.rect["escala"], 14
                zonas.append((izq + int((self.rect["x"] - m) * e), arriba + int((self.rect["y"] - m) * e),
                              izq + int((self.rect["x"] + self.rect["ancho"] + m) * e),
                              arriba + int((self.rect["y"] + self.rect["alto"] + m) * e)))
            else:
                zonas.append((izq, arriba, der, abajo))
        return zonas


class Confirmar:
    """Una confirmación cada vez. servidor puede ser None (sin isla: solo Enter/Esc físicos)."""

    def __init__(self, servidor=None, timeout_s=30, cancelar=lambda: False, entrada=None, avisar=print):
        self.servidor, self.timeout_s, self.cancelar, self.avisar = servidor, timeout_s, cancelar, avisar
        self._crear_entrada = entrada or (lambda zonas, al_teclear: EntradaFisica(zonas, al_teclear))
        self.ultima = None  # {'id', 'resultado', 'via'} para el registro y las pruebas

    def pedir(self, herramienta, resumen, motivo=None, comando=None, extra=None):
        """extra(aceptar, hecho, entrada): otra vía de "sí" que corre en un hilo mientras se espera (la frase de
        voz en voz.py). aceptar(via) confirma; hecho es el Event que marca el final."""
        ident = uuid.uuid4().hex[:12]
        hecho = threading.Event()
        res = {"si": False, "via": "sin respuesta"}
        inicio = time.monotonic()

        def resolver(si, via):
            if not hecho.is_set():
                res.update(si=si, via=via)
                hecho.set()

        zonas = (lambda: self.servidor.zonas_isla()) if self.servidor else (lambda: [])
        entrada = self._crear_entrada(zonas, lambda si: resolver(si, "teclado físico"))

        def al_decidir(id_, si):
            if id_ != ident or hecho.is_set():
                return  # una decisión vieja o repetida no vale
            if entrada.clic_fisico_reciente(inicio):
                resolver(si, "botón de la isla (clic físico)")
                return
            self.servidor.enviar({"tipo": "decision_rechazada", "id": ident,
                                  "motivo": "No lo acepto: el clic no fue físico. Pulsa tú el botón."})
            self.avisar("  [confirmación] decisión de la isla rechazada: el clic no fue físico")

        if self.servidor:
            self.servidor.al_decidir = al_decidir
            self.servidor.enviar({"tipo": "confirmar", "id": ident, "herramienta": herramienta, "resumen": resumen,
                                  "motivo": motivo, "comando": comando})
        entrada.iniciar()
        if extra:
            threading.Thread(target=extra, args=(lambda via: resolver(True, via), hecho, entrada),
                             name="confirmar-por-voz", daemon=True).start()
        try:
            limite = inicio + self.timeout_s
            while not hecho.wait(0.05):
                if self.cancelar():
                    resolver(False, "atajo de emergencia")
                elif time.monotonic() >= limite:
                    resolver(False, f"sin respuesta en {self.timeout_s} s")
        finally:
            entrada.cerrar()
            if self.servidor:
                self.servidor.al_decidir = None
                self.servidor.enviar({"tipo": "cancelar", "id": ident})
        self.ultima = {"id": ident, "resultado": res["si"], "via": res["via"],
                       "teclas_inyectadas": entrada.teclas_inyectadas, "clics_inyectados": entrada.clics_inyectados}
        return res["si"]
