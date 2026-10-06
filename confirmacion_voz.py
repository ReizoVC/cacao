"""
Confirmación por voz: la frase "confirmo la instrucción", dicha en una grabación aparte DESPUÉS de la pregunta
(pulsando Ctrl+Espacio o diciendo "Cacao"). Enter, Esc y los botones de la isla siguen valiendo; "sí" solo no vale.

Frenos (todos tienen que pasar):
  - la frase, con tolerancia a pequeñas variaciones (tildes, signos, "confirmó", "instrucciones"); una negación,
    palabras de más o una frase distinta no valen;
  - voz real: al menos MIN_VOZ_S de voz en la grabación (Whisper inventa frases sobre silencio o ruido) y las
    palabras tienen que caber en esos segundos;
  - nada más sonando: si otra app reproduce audio durante la grabación (un video que diga la frase), no vale;
  - con Ctrl+Espacio, la tecla Espacio tiene que ser física (las teclas del agente llegan inyectadas);
  - la palabra de activación sola nunca confirma: solo abre la grabación.
Un "no" sigue siendo Esc, Denegar o 30 s sin respuesta.
"""
import re
import threading
import time
import unicodedata

from rapidfuzz import fuzz

FRASE = "confirmo la instruccion"
MIN_VOZ_S = 0.5
MIN_PARECIDO = 85
NEGACIONES = {"no", "nunca", "jamas", "cancela", "cancelar", "cancelo", "espera", "niego", "deniego"}
PALABRAS_ACTIVACION = ("oye cacao", "cacao")


def normalizar(texto):
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^\w]+", " ", t).split())


def sin_activacion(texto):
    """Quita la palabra de activación del principio ("Cacao, confirmo la instrucción")."""
    t = normalizar(texto)
    for p in PALABRAS_ACTIVACION:
        if t == p:
            return ""
        if t.startswith(p + " "):
            return t[len(p) + 1:]
    return t


def es_frase(texto):
    """(True, parecido) si el texto es "confirmo la instrucción" con variaciones pequeñas."""
    t = sin_activacion(texto)
    palabras = t.split()
    if not palabras or NEGACIONES & set(palabras):
        return False, 0
    if len(palabras) > len(FRASE.split()) + 1:  # "confirmo la instrucción de borrar todo" no vale
        return False, 0
    parecido = fuzz.ratio(t, FRASE)
    return parecido >= MIN_PARECIDO, parecido


def evaluar(texto, voz_s, otro_audio=False, tecla_fisica=True, por_activacion=False):
    """None si la grabación confirma; si no, el motivo (para la consola y el registro)."""
    if por_activacion and not sin_activacion(texto):
        return "solo dijiste la palabra de activación: eso no confirma nada"
    if not tecla_fisica:
        return "Ctrl+Espacio no fue físico"
    if otro_audio:
        return "había otro audio sonando (un video o música podría decir la frase)"
    if voz_s < MIN_VOZ_S:
        return f"casi sin voz ({voz_s} s): Whisper pudo inventar la frase"
    from transcripcion import transcripcion_plausible
    if not transcripcion_plausible(texto, voz_s):
        return "demasiadas palabras para la voz que hubo"
    bien, parecido = es_frase(texto)
    if not bien:
        return f"no es la frase de confirmación ({parecido:.0f} % de parecido)"
    return None


# ---------- el oyente (corre en un hilo mientras se espera una confirmación) ----------

def otro_audio_sonando():
    """True si otra app (no este proceso: Piper y el pitido son nuestros) está sonando ahora."""
    try:
        from deteccion import SistemaWindows
        return any(pico > 0.01 for _, _, pico in SistemaWindows(None).audio())
    except Exception:
        return True  # sin poder mirarlo, la voz no confirma (quedan Enter y la isla)


class VigiaAudio:
    """Mira cada 0,15 s, mientras se graba, si otra app suena."""

    def __init__(self, mirar=otro_audio_sonando):
        self.mirar, self.sonando, self._fin = mirar, False, threading.Event()
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    def _bucle(self):
        while not self._fin.is_set():
            self.sonando = self.sonando or self.mirar()
            self._fin.wait(0.15)

    def parar(self):
        self._fin.set()
        self._hilo.join(1)
        return self.sonando


class Oyente:
    """Cada grabación hecha tras la pregunta se transcribe y, si pasa evaluar(), confirma.
    disparos(segundos) -> 'atajo' (Ctrl+Espacio), ('activacion', audio) (la palabra "Cacao" con lo que vino
    después) o None. Por defecto solo el atajo. El hilo del bucle está esperando la confirmación, así que el
    micrófono y Whisper están libres."""

    def __init__(self, atajo, microfono, transcriptor, min_voz_s=0.15, disparos=None, mirar_audio=otro_audio_sonando,
                 anotar=print):
        from microfono import analizar_audio
        from transcripcion import a_wav
        self.atajo, self.microfono, self.transcriptor = atajo, microfono, transcriptor
        self.min_voz_s, self.mirar_audio, self.anotar = min_voz_s, mirar_audio, anotar
        self.disparos = disparos or (lambda s: "atajo" if atajo.esperar(s) else None)
        self.analizar, self.a_wav = analizar_audio, a_wav
        self.intentos = []  # (texto, motivo o None), para el registro y las pruebas

    def escuchar(self, aceptar, hecho, entrada):
        while not hecho.is_set():
            disparo = self.disparos(0.1)
            if disparo is None or hecho.is_set():
                continue
            vigia = VigiaAudio(self.mirar_audio)
            if disparo == "atajo":
                tecla_fisica = entrada.espacio_fisico_reciente()
                limite = time.perf_counter() + 8
                audio, _, _ = self.microfono.grabar_hasta(
                    lambda: self.atajo.sigue_pulsado() and not hecho.is_set() and time.perf_counter() < limite)
            else:  # ("activacion", audio): la grabación tras "Cacao" ya está hecha
                tecla_fisica, audio = True, disparo[1]
            otro_audio = vigia.parar()
            if hecho.is_set():
                return
            analisis = self.analizar(audio)
            texto = self.transcriptor.transcribir(self.a_wav(audio)) if analisis["voz_s"] >= self.min_voz_s else ""
            motivo = evaluar(texto, analisis["voz_s"], otro_audio, tecla_fisica,
                             por_activacion=disparo != "atajo")
            self.intentos.append((texto, motivo))
            self.anotar(f"  [confirmación por voz] «{texto}»: {'vale' if motivo is None else 'no vale, ' + motivo}")
            if motivo is None:
                aceptar("voz: «confirmo la instrucción»")
                return
