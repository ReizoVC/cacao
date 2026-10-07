"""
Palabra de activación "Cacao" (local, en la CPU).

Detector: las características de openWakeWord (melspectrograma + embeddings de speech_embedding de Google, modelos
ONNX que trae el paquete) y encima un clasificador pequeño entrenado con voces sintéticas de Piper
(entrenar_cacao.py -> modelos/cacao/cacao.npz). Cada 80 ms entra un trozo de audio y sale una probabilidad; hay
detección si supera el umbral en 'paciencia' tramas seguidas.

Privacidad: el audio pasa por memoria (un búfer circular de unos segundos) y se descarta; nada se guarda ni se
transcribe hasta detectar la palabra. Mientras Cacao habla (Piper) la detección se ignora.
"""
import queue
import threading
import time
from collections import deque
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent
RUTA_MODELO = BASE / "modelos" / "cacao" / "cacao.npz"
TASA = 16000
TROZO = 1280            # 80 ms: lo que consume openWakeWord por trama
TRAMAS = 16             # 1,28 s de características por decisión (lo que ve el clasificador)
TRAMA_VAD = 480         # 30 ms para medir si hay voz al grabar tras la palabra


# Cómo escribe Whisper la palabra (sin tildes ni mayúsculas). La segunda etapa: tras una detección, la orden se
# transcribe igualmente; si no empieza con la palabra, era una activación falsa y se descarta sin guardar nada.
FORMAS = {"cacao", "kakao", "cacau", "cakao", "kakau", "cacaos"}


def _normalizar(texto):
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^\w]+", " ", t).split()


def es_la_palabra(palabra):
    from rapidfuzz import fuzz
    # palabras cortas solo exactas: "caca" se parece un 89 % a "cacao" y no es la palabra
    return palabra in FORMAS or (len(palabra) >= 5 and fuzz.ratio(palabra, "cacao") >= 80)


# lo único que puede ir antes de la palabra: un saludo o llamada ("Oye, Cacao", "Hola Cacao"). "Entonces el cacao
# se produce..." (un video) no es una llamada: la palabra no va tras un artículo ni en medio de una frase.
LLAMADAS = {"oye", "oiga", "hola", "ey", "hey", "eh", "a", "ah", "oh"}


def empieza_con_la_palabra(texto):
    """True si la transcripción empieza con "Cacao", o con una o dos llamadas y "Cacao" ("Oye, Cacao, ...")."""
    palabras = _normalizar(texto)
    for i, p in enumerate(palabras[:3]):
        if es_la_palabra(p):
            return all(q in LLAMADAS for q in palabras[:i])
    return False


def quitar_palabra(texto):
    """'Cacao, sube el volumen.' -> 'sube el volumen.'; 'Oye, Kakao, pon música' -> 'pon música'."""
    import re
    partes = re.split(r"(\s+)", (texto or "").strip())
    palabras = [i for i, p in enumerate(partes) if p.strip()]
    for k, i in enumerate(palabras[:3]):
        limpia = _normalizar(partes[i])
        if limpia and es_la_palabra(limpia[0]):
            return "".join(partes[palabras[k + 1]:]).lstrip(" ,.;:") if k + 1 < len(palabras) else ""
    return (texto or "").strip()


# ---------- contador diario (sin audio ni texto) ----------

RUTA_CONTADOR = Path(__file__).parent / "contador_cacao.json"
ETAPAS = ("primera_etapa", "segunda_etapa", "pedido")
_cerrojo_contador = threading.Lock()


def contar(etapa, ruta=None, hoy=None):
    """Suma 1 a la etapa del día: primera_etapa (el detector se activó), segunda_etapa (Whisper oyó "Cacao" al
    principio) o pedido (llegó una orden al agente). Solo números por día: nada de audio ni de texto."""
    import json
    ruta = Path(ruta or RUTA_CONTADOR)
    dia = (hoy or time.strftime("%Y-%m-%d"))
    with _cerrojo_contador:
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
        except ValueError:
            datos = {}
        fila = datos.setdefault(dia, {e: 0 for e in ETAPAS})
        fila[etapa] = fila.get(etapa, 0) + 1
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def relu(x):
    return np.maximum(x, 0)


class ModeloCacao:
    """Clasificador sobre 16 tramas de embeddings (16 x 96): MLP de una capa oculta, en numpy."""

    def __init__(self, ruta=RUTA_MODELO):
        d = np.load(ruta)
        self.capas = [(d[f"W{i}"], d[f"b{i}"]) for i in range(1, 10) if f"W{i}" in d]
        self.media, self.escala = d["media"], d["escala"]
        self.umbral = float(d["umbral"])
        self.paciencia = int(d["paciencia"]) if "paciencia" in d else 2

    def probabilidad(self, x):
        """x: (n, 16, 96) o (16, 96) -> probabilidades (n,)."""
        x = np.asarray(x, dtype=np.float32).reshape(-1, TRAMAS * 96)
        h = (x - self.media) / self.escala
        for i, (w, b) in enumerate(self.capas):
            h = h @ w + b
            if i < len(self.capas) - 1:
                h = relu(h)
        return 1 / (1 + np.exp(-h[:, 0]))


class Detector:
    """Entra audio int16 a 16 kHz (cualquier tamaño); procesar() devuelve las probabilidades de las tramas nuevas
    y detectado() si hubo detección (umbral en 'paciencia' tramas seguidas)."""

    def __init__(self, modelo=None, umbral=None, paciencia=None):
        from openwakeword.utils import AudioFeatures
        self.modelo = modelo or ModeloCacao()
        self.umbral = umbral if umbral is not None else self.modelo.umbral
        self.paciencia = paciencia if paciencia is not None else self.modelo.paciencia
        self.features = AudioFeatures(inference_framework="onnx", ncpu=1)
        self._resto = np.zeros(0, dtype=np.int16)
        self._racha = 0
        self.ultima = 0.0

    def reiniciar(self):
        self.features.reset()
        self._resto = np.zeros(0, dtype=np.int16)
        self._racha = 0

    def procesar(self, audio):
        """Devuelve True si en este audio se completó una detección."""
        audio = np.concatenate([self._resto, np.asarray(audio, dtype=np.int16)])
        detectado = False
        n = len(audio) // TROZO * TROZO
        for i in range(0, n, TROZO):
            self.features(audio[i:i + TROZO])
            p = float(self.modelo.probabilidad(self.features.get_features(TRAMAS)[0])[0])
            self.ultima = p
            self._racha = self._racha + 1 if p >= self.umbral else 0
            if self._racha >= self.paciencia:
                detectado = True
                self._racha = -1000  # una sola detección por palabra (el que llama reinicia)
        self._resto = audio[n:]
        return detectado


def a_16k(audio, tasa):
    if tasa == TASA:
        return np.asarray(audio, dtype=np.int16)
    from scipy.signal import resample_poly
    from math import gcd
    g = gcd(int(tasa), TASA)
    y = resample_poly(np.asarray(audio, dtype=np.float32), TASA // g, int(tasa) // g)
    return np.clip(y, -32768, 32767).astype(np.int16)


class Grabacion:
    """Tras la palabra: búfer previo (para no cortar "Cacao, sube el volumen" dicho de corrido) y luego graba hasta
    un silencio o max_s. Si tras la palabra no empieza a hablar en espera_s, termina con lo que hay."""

    def __init__(self, previo, umbral_voz, espera_s=4.0, silencio_s=0.9, max_s=30.0):
        self.partes = [previo]
        self.umbral_voz, self.espera_s, self.silencio_s, self.max_s = umbral_voz, espera_s, silencio_s, max_s
        self.t = 0.0          # segundos grabados después de la detección
        self.hablo = False    # empezó a hablar después de la palabra
        self.silencio = 0.0
        self.terminada = False

    def agregar(self, audio):
        self.partes.append(audio)
        for i in range(0, len(audio) - TRAMA_VAD + 1, TRAMA_VAD):
            trama = audio[i:i + TRAMA_VAD].astype(np.float32)
            voz = np.sqrt((trama ** 2).mean()) > self.umbral_voz
            self.t += TRAMA_VAD / TASA
            if voz:
                self.hablo, self.silencio = True, 0.0
            else:
                self.silencio += TRAMA_VAD / TASA
        if (self.hablo and self.silencio >= self.silencio_s) or (not self.hablo and self.t >= self.espera_s) \
                or self.t >= self.max_s:
            self.terminada = True
        return self.terminada

    def audio(self):
        return np.concatenate(self.partes) if self.partes else np.zeros(0, dtype=np.int16)


class Escucha:
    """Hilo que escucha "Cacao" en el micrófono mientras activa() sea True.
    - El micrófono le pasa cada bloque (Microfono.oyentes); aquí se pasa a 16 kHz y se procesa en otro hilo.
    - Se ignora mientras ignorar() sea True (Cacao hablando, Ctrl+Espacio pulsado) y hasta 0,6 s después.
    - Al detectar: al_detectar() (la isla muestra "escuchando"), graba con el búfer previo y deja en self.cola
      ('activacion', audio, otro_audio) para quien esté esperando (el bucle o una confirmación pendiente)."""

    def __init__(self, tasa_mic, activa, ignorar=lambda: False, al_detectar=lambda: None, detector=None,
                 umbral_voz=500, previo_s=1.6, mirar_audio=None, anotar=print):
        self.tasa_mic, self.activa, self.ignorar, self.al_detectar = tasa_mic, activa, ignorar, al_detectar
        self.detector = detector or Detector()
        self.umbral_voz, self.anotar = umbral_voz, anotar
        self.mirar_audio = mirar_audio
        self.previo = deque(maxlen=int(previo_s * TASA / TROZO) + 1)  # trozos de 80 ms
        self.cola = queue.Queue()
        self._entrada = queue.Queue(maxsize=400)
        self._grabando = None
        self._ignorado_hasta = 0.0
        self._fin = threading.Event()
        self.detecciones = 0
        self._hilo = threading.Thread(target=self._bucle, name="escucha-cacao", daemon=True)
        self._hilo.start()

    def recibir(self, bloque):
        """Lo llama el callback del micrófono (rápido: solo encola)."""
        try:
            self._entrada.put_nowait(bloque)
        except queue.Full:
            pass

    def cerrar(self):
        self._fin.set()

    def _bucle(self):
        resto = np.zeros(0, dtype=np.int16)
        while not self._fin.is_set():
            try:
                bloque = self._entrada.get(timeout=0.2)
            except queue.Empty:
                continue
            audio = a_16k(bloque.reshape(-1), self.tasa_mic)
            if self._grabando is not None:
                if self._grabando.agregar(audio):
                    self._entregar()
                continue
            if not self.activa():
                self.previo.clear()
                resto = np.zeros(0, dtype=np.int16)
                continue
            ahora = time.monotonic()
            if self.ignorar():
                self._ignorado_hasta = ahora + 0.6
            audio = np.concatenate([resto, audio])
            n = len(audio) // TROZO * TROZO
            resto = audio[n:]
            for i in range(0, n, TROZO):
                trozo = audio[i:i + TROZO]
                self.previo.append(trozo)
                if ahora < self._ignorado_hasta:
                    self.detector.reiniciar()
                    continue
                if self.detector.procesar(trozo):
                    self._detectado()
                    break

    def _detectado(self):
        self.detecciones += 1
        try:
            contar("primera_etapa")
        except OSError:
            pass
        self.anotar("  [Cacao] palabra de activación detectada")
        self.al_detectar()
        self._vigia = None
        if self.mirar_audio:
            from confirmacion_voz import VigiaAudio
            self._vigia = VigiaAudio(self.mirar_audio)
        self._grabando = Grabacion(np.concatenate(list(self.previo)) if self.previo else np.zeros(0, np.int16),
                                   self.umbral_voz)
        self.previo.clear()

    def _entregar(self):
        g, self._grabando = self._grabando, None
        otro_audio = self._vigia.parar() if self._vigia else False
        self.detector.reiniciar()
        self.cola.put(("activacion", g.audio(), otro_audio))
