"""
Micrófono y atajo de pulsar para hablar (sin cargar el modelo; lo usan voz.py y grabar_frases.py).

- Microfono: flujo de entrada abierto todo el tiempo (abrirlo al pulsar perdía ~200 ms de voz); solo guarda lo
  que llega mientras se graba. Entrega int16 mono a 16 kHz.
- AtajoHablar: registra el atajo con RegisterHotKey para que la app que está al frente NO lo reciba (en VS Code,
  ctrl+espacio abriría las sugerencias) y avisa al pulsarlo; soltar se detecta leyendo el estado de las teclas.
"""
import ctypes
import threading
import time
from ctypes import wintypes

import numpy as np
import sounddevice as sd

TASA = 16000
WM_HOTKEY, WM_QUIT, PM_NOREMOVE = 0x0312, 0x0012, 0x0000
MODIFICADORES = {"ctrl": (0x2, 0x11), "control": (0x2, 0x11), "alt": (0x1, 0x12), "shift": (0x4, 0x10),
                 "win": (0x8, 0x5B)}
TECLAS = {"espacio": 0x20, "space": 0x20}
MOD_NOREPEAT = 0x4000
ID_ATAJO = 2

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def parsear(atajo):
    """'ctrl+espacio' -> (modificadores para RegisterHotKey, [códigos virtuales de todas las teclas])."""
    mods, vks = 0, []
    for parte in atajo.lower().replace(" ", "").split("+"):
        if parte in MODIFICADORES:
            mods |= MODIFICADORES[parte][0]
            vks.append(MODIFICADORES[parte][1])
        elif parte in TECLAS:
            vks.append(TECLAS[parte])
        elif len(parte) == 1 and parte.isalnum():
            vks.append(ord(parte.upper()))
        else:
            raise ValueError(f"Tecla no admitida en el atajo: {parte!r}")
    return mods, vks


class AtajoHablar:
    def __init__(self, atajo="ctrl+espacio"):
        self.atajo = atajo
        self.mods, self.vks = parsear(atajo)
        self.pulsado = threading.Event()
        self.registrado = None
        self._id_hilo = None
        self._listo = threading.Event()

    def iniciar(self):
        threading.Thread(target=self._escuchar, name="atajo-hablar", daemon=True).start()
        self._listo.wait(5)
        return self.registrado

    def _escuchar(self):
        self._id_hilo = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)
        self.registrado = bool(user32.RegisterHotKey(None, ID_ATAJO, self.mods | MOD_NOREPEAT, self.vks[-1]))
        self._listo.set()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam == ID_ATAJO:
                self.pulsado.set()
        if self.registrado:
            user32.UnregisterHotKey(None, ID_ATAJO)

    def sigue_pulsado(self):
        return all(user32.GetAsyncKeyState(vk) & 0x8000 for vk in self.vks)

    def esperar(self, timeout=None):
        """Bloquea hasta que se pulse el atajo. Devuelve False si venció el timeout."""
        if timeout is None:
            while not self.pulsado.wait(0.25):  # a trozos: un wait sin límite no deja pasar Ctrl+C en Windows
                pass
            ok = True
        else:
            ok = self.pulsado.wait(timeout)
        self.pulsado.clear()
        return ok

    def cerrar(self):
        if self._id_hilo is not None:
            user32.PostThreadMessageW(self._id_hilo, WM_QUIT, 0, 0)


class Microfono:
    def __init__(self, dispositivo=None):
        self.grabando = False
        self.bloques = []
        self.tasa = TASA
        self.oyentes = []  # funciones(bloque) que reciben todo el audio (la palabra de activación); solo memoria
        try:
            self.flujo = sd.InputStream(samplerate=TASA, channels=1, dtype="int16", device=dispositivo,
                                        callback=self._recibir)
        except sd.PortAudioError:  # el dispositivo no admite 16 kHz: se graba a su tasa y se remuestrea
            self.tasa = int(sd.query_devices(dispositivo, kind="input")["default_samplerate"])
            self.flujo = sd.InputStream(samplerate=self.tasa, channels=1, dtype="int16", device=dispositivo,
                                        callback=self._recibir)
        self.nombre = sd.query_devices(self.flujo.device, kind="input")["name"]
        self.flujo.start()

    def _recibir(self, datos, *_):
        if self.grabando:
            self.bloques.append(datos.copy())
        for oyente in self.oyentes:
            oyente(datos.copy())

    def grabar_hasta(self, sigue):
        """Graba mientras sigue() sea verdadero. Devuelve (audio int16 a 16 kHz, segundos pulsado, momento de
        soltar en perf_counter)."""
        self.bloques = []
        self.grabando = True
        inicio = time.perf_counter()
        while sigue():
            time.sleep(0.01)
        soltado = time.perf_counter()
        time.sleep(0.15)  # no cortar la última sílaba al soltar
        self.grabando = False
        audio = np.concatenate(self.bloques)[:, 0] if self.bloques else np.zeros(0, dtype=np.int16)
        if self.tasa != TASA and len(audio):
            x = np.linspace(0, len(audio) - 1, int(len(audio) * TASA / self.tasa))
            audio = np.interp(x, np.arange(len(audio)), audio).astype(np.int16)
        return audio, soltado - inicio, soltado

    def cerrar(self):
        self.flujo.close()


# ---------- frenos y confirmación (modo voz) ----------

TRAMA = 480  # 30 ms a 16 kHz
UMBRAL_VOZ = 400  # RMS de una trama con voz (int16); el silencio del G435 da ~20-200


def analizar_audio(audio):
    """Pico y segundos con voz (tramas de 30 ms con RMS por encima del umbral)."""
    audio = np.asarray(audio, dtype=np.int16)
    if not len(audio):
        return {"pico": 0, "voz_s": 0.0, "duracion_s": 0.0}
    n = len(audio) // TRAMA
    tramas = audio[:n * TRAMA].astype(np.float32).reshape(n, TRAMA) if n else np.zeros((0, TRAMA))
    rms = np.sqrt((tramas ** 2).mean(axis=1)) if n else np.zeros(0)
    return {"pico": int(np.abs(audio).max()), "voz_s": round(float((rms > UMBRAL_VOZ).sum()) * TRAMA / TASA, 2),
            "duracion_s": round(len(audio) / TASA, 2)}


VK_RETURN, VK_ESCAPE = 0x0D, 0x1B
ID_SI, ID_NO = 10, 11


def confirmar_teclado(timeout=30.0, cancelar=None):
    """Espera Enter (sí) o Esc (no) desde cualquier ventana. Las teclas se registran como atajos solo mientras se
    espera, así no llegan a la app que está al frente. Devuelve True, False, o None si venció el tiempo.
    `cancelar()` se consulta cada 50 ms (por ejemplo, para el atajo de emergencia)."""
    msg = wintypes.MSG()
    user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)  # crea la cola de mensajes del hilo
    si = user32.RegisterHotKey(None, ID_SI, MOD_NOREPEAT, VK_RETURN)
    no = user32.RegisterHotKey(None, ID_NO, MOD_NOREPEAT, VK_ESCAPE)
    try:
        if not (si and no):  # otro programa los tiene registrados: se leen sin bloquearlos
            fin = time.perf_counter() + timeout
            while time.perf_counter() < fin:
                if cancelar and cancelar():
                    return False
                if user32.GetAsyncKeyState(VK_RETURN) & 0x8000:
                    return True
                if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                    return False
                time.sleep(0.02)
            return None
        fin = time.perf_counter() + timeout
        while time.perf_counter() < fin:
            if cancelar and cancelar():
                return False
            while user32.PeekMessageW(ctypes.byref(msg), None, WM_HOTKEY, WM_HOTKEY, 1):  # PM_REMOVE
                if msg.wParam in (ID_SI, ID_NO):
                    return msg.wParam == ID_SI
            time.sleep(0.05)
        return None
    finally:
        if si:
            user32.UnregisterHotKey(None, ID_SI)
        if no:
            user32.UnregisterHotKey(None, ID_NO)
