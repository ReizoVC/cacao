"""
Escucha de seguimiento: después de responder, Cacao sigue oyendo unos segundos (8 por defecto) sin necesitar la
palabra "Cacao". Si Reizo habla, se graba hasta un silencio y entra como un pedido normal, con los mismos frenos
(voz.filtrar: silencio, palabras de más, frases que Whisper inventa) y las mismas confirmaciones. Si no, termina.

- No se abre si otra app está sonando (un video o una llamada podrían dar órdenes), y se cierra si otra app empieza a
  sonar antes de que hable. Si suena mientras graba, la grabación se marca y voz.py la descarta.
- Voz = 4 tramas seguidas de 30 ms por encima del umbral (un clic o una tecla no bastan); se guarda medio segundo
  de antes para no cortar la primera sílaba.
- Se ignoran los primeros 0,4 s: la cola de la voz de Cacao que aún suena en los altavoces.
- Privacidad: como la palabra de activación, el audio pasa por memoria y se descarta si nadie habla.

voz.py lo abre al terminar de hablar (si el modo «seguimiento» y la escucha de «Cacao» están activos) y recoge de
self.cola ('seguimiento', audio, otro_audio) o ('fin', motivo).
"""
import queue
import threading
import time
from collections import deque

import numpy as np

from palabra_activacion import TASA, TRAMA_VAD, Grabacion, a_16k

PREVIO_S = 0.5
RETRASO_S = 0.4
TRAMAS_VOZ = 4  # 120 ms seguidos con voz


class Seguimiento:
    def __init__(self, tasa_mic, umbral_voz, mirar_audio=None, al_empezar=lambda: None, reloj=time.monotonic,
                 hilo=True, silencio_s=0.9, max_s=30.0):
        self.tasa_mic, self.umbral_voz, self.al_empezar, self.reloj = tasa_mic, umbral_voz, al_empezar, reloj
        self.mirar_audio = mirar_audio
        self.silencio_s, self.max_s = silencio_s, max_s
        self.cola = queue.Queue()
        self._cerrojo = threading.Lock()
        self._abierta = False
        self._entrada = queue.Queue(maxsize=400)
        self._fin = threading.Event()
        if hilo:
            threading.Thread(target=self._bucle, name="escucha-seguimiento", daemon=True).start()

    @property
    def abierta(self):
        return self._abierta

    def abrir(self, segundos, retraso_s=RETRASO_S):
        """Empieza a escuchar. False (y no se abre) si otra app está sonando."""
        if self.mirar_audio and self.mirar_audio():
            return False
        with self._cerrojo:
            ahora = self.reloj()
            self._desde, self._hasta = ahora + retraso_s, ahora + retraso_s + segundos
            self._previo = deque(maxlen=int(PREVIO_S * TASA / TRAMA_VAD) + 1)
            self._resto = np.zeros(0, dtype=np.int16)
            self._seguidas = 0
            self._grabacion = None
            self._vigia = None
            if self.mirar_audio:
                from confirmacion_voz import VigiaAudio
                self._vigia = VigiaAudio(self.mirar_audio)
            self._abierta = True
        return True

    def cerrar(self, motivo=None):
        """Termina sin entregar nada (otro disparo, Ctrl+Espacio, un pedido escrito). Con 'motivo', avisa en la cola."""
        with self._cerrojo:
            self._terminar()
            if motivo:
                self.cola.put(("fin", motivo))

    def _terminar(self):
        self._abierta = False
        self._grabacion = None
        otro = self._vigia.parar() if self._vigia else False
        self._vigia = None
        return otro

    # ----- audio -----

    def recibir(self, bloque):
        """Lo llama el callback del micrófono (rápido: solo encola, y solo con la escucha abierta)."""
        if self._abierta:
            try:
                self._entrada.put_nowait(bloque)
            except queue.Full:
                pass

    def _bucle(self):
        while not self._fin.is_set():
            try:
                bloque = self._entrada.get(timeout=0.1)
            except queue.Empty:
                self.procesar(None)  # vence el tiempo aunque no llegue audio
                continue
            self.procesar(a_16k(bloque.reshape(-1), self.tasa_mic))

    def procesar(self, audio):
        """Audio a 16 kHz (o None para solo mirar el reloj). Las pruebas lo llaman directamente."""
        with self._cerrojo:
            if not self._abierta:
                return
            ahora = self.reloj()
            if self._grabacion is not None:
                if audio is not None and self._grabacion.agregar(audio):
                    grabado = self._grabacion.audio()
                    otro = self._terminar()
                    self.cola.put(("seguimiento", grabado, otro))
                return
            if self._vigia and self._vigia.sonando:
                self._terminar()
                self.cola.put(("fin", "otro_audio"))
                return
            if ahora >= self._hasta:
                self._terminar()
                self.cola.put(("fin", "tiempo"))
                return
            if audio is None or ahora < self._desde:
                return
            audio = np.concatenate([self._resto, np.asarray(audio, dtype=np.int16)])
            n = len(audio) // TRAMA_VAD * TRAMA_VAD
            self._resto = audio[n:]
            for i in range(0, n, TRAMA_VAD):
                trama = audio[i:i + TRAMA_VAD]
                self._previo.append(trama)
                voz = np.sqrt((trama.astype(np.float32) ** 2).mean()) > self.umbral_voz
                self._seguidas = self._seguidas + 1 if voz else 0
                if self._seguidas >= TRAMAS_VOZ:
                    # habla: graba desde medio segundo antes hasta un silencio (como tras la palabra "Cacao")
                    g = Grabacion(np.concatenate(list(self._previo)), self.umbral_voz, silencio_s=self.silencio_s,
                                  max_s=self.max_s)
                    g.hablo = True
                    resto = audio[i + TRAMA_VAD:]
                    self._grabacion = g
                    self._previo.clear()
                    threading.Thread(target=self.al_empezar, daemon=True).start()
                    if len(resto) and g.agregar(resto):
                        grabado = g.audio()
                        otro = self._terminar()
                        self.cola.put(("seguimiento", grabado, otro))
                    return

    def apagar(self):
        self._fin.set()
