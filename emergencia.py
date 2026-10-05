"""
Atajo de emergencia (limites.atajo_emergencia de herramientas.json, por defecto ctrl+alt+shift+q).

Un hilo registra el atajo global con RegisterHotKey y espera mensajes WM_HOTKEY. Al pulsarlo se activa un
evento; el agente lo comprueba:
  - en cada token que genera el modelo (LlamaRapida llama a llm.interrumpir desde el muestreador),
  - antes de pedir la acción y antes de ejecutar cada herramienta,
  - dentro de las herramientas largas (teclado escribe carácter a carácter).
Si está activo, se lanza Detenido y atender() corta la tarea.

Una pulsación deja el agente DETENIDO: corta la tarea en curso y rechaza todas las siguientes hasta que Reizo
lo reanude (escribiendo 'reanudar'). Ninguna pulsación se descarta: el evento solo se borra con reanudar().
"""
import ctypes
import threading
import time
from ctypes import wintypes

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
PM_NOREMOVE = 0x0000
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
MODIFICADORES = {"ctrl": MOD_CONTROL, "control": MOD_CONTROL, "alt": MOD_ALT, "shift": MOD_SHIFT, "win": MOD_WIN}
ID_ATAJO = 1

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class Detenido(Exception):
    """El usuario pulsó el atajo de emergencia."""


def _parsear(atajo):
    mods, tecla = 0, None
    for parte in atajo.lower().replace(" ", "").split("+"):
        if parte in MODIFICADORES:
            mods |= MODIFICADORES[parte]
        elif len(parte) == 1 and parte.isalnum():
            tecla = ord(parte.upper())
        else:
            raise ValueError(f"Tecla no admitida en el atajo: {parte!r}")
    if tecla is None:
        raise ValueError(f"El atajo {atajo!r} no tiene tecla principal")
    return mods, tecla


class Emergencia:
    def __init__(self, atajo="ctrl+alt+shift+q"):
        self.atajo = atajo
        self.evento = threading.Event()  # activo = agente detenido
        self.pulsaciones = 0
        self.momento = None  # perf_counter de la última pulsación (para medir cuánto tarda en cortar)
        self.registrado = None  # True/False cuando el hilo intentó registrar el atajo
        self._id_hilo = None
        self._listo = threading.Event()
        self._hilo = None

    def iniciar(self):
        """Arranca el hilo del atajo. Devuelve False si Windows no dejó registrarlo (otro programa lo usa)."""
        if self._hilo is None:
            self._hilo = threading.Thread(target=self._escuchar, name="atajo-emergencia", daemon=True)
            self._hilo.start()
            self._listo.wait(5)
        return self.registrado

    def _escuchar(self):
        self._id_hilo = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)  # crea la cola antes de avisar que está listo
        mods, tecla = _parsear(self.atajo)
        self.registrado = bool(user32.RegisterHotKey(None, ID_ATAJO, mods | MOD_NOREPEAT, tecla))
        self._listo.set()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam == ID_ATAJO:
                self.pulsaciones += 1
                self.momento = time.perf_counter()
                self.evento.set()
                print(f"\n[emergencia] {self.atajo}: agente detenido; escribe 'reanudar' para seguir.", flush=True)
        if self.registrado:
            user32.UnregisterHotKey(None, ID_ATAJO)

    def simular_atajo(self):
        """Para pruebas: envía al hilo el mismo WM_HOTKEY que manda Windows, sin tocar el teclado."""
        return bool(user32.PostThreadMessageW(self._id_hilo, WM_HOTKEY, ID_ATAJO, 0))

    def comprobar(self):
        if self.evento.is_set():
            raise Detenido(f"Detenido con el atajo de emergencia ({self.atajo}).")

    def detenido(self):
        return self.evento.is_set()

    def reanudar(self):
        """Solo por decisión explícita de Reizo: el agente vuelve a aceptar tareas."""
        self.evento.clear()

    def cerrar(self):
        if self._id_hilo is not None:
            user32.PostThreadMessageW(self._id_hilo, WM_QUIT, 0, 0)
            self._hilo.join(2)
