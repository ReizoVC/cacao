"""
Pruebas sin micrófono ni modelo de la confirmación por voz (confirmacion_voz.py):
  1. la frase "confirmo la instrucción" con variaciones pequeñas vale; "sí", negaciones y frases distintas no;
  2. frenos: transcripción inventada (casi sin voz), otro audio sonando, Ctrl+Espacio inyectado, solo "Cacao";
  3. de punta a punta con ui_isla.Confirmar: la frase confirma, "sí" no (vence el tiempo), y Esc sigue valiendo.
Uso: .venv\\Scripts\\python probar_confirmacion_voz.py
"""
import sys
import threading
import time

import numpy as np

import confirmacion_voz as cv
from microfono import TASA
from ui_isla import Confirmar

resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


def voz(segundos, silencio=0.3):
    """Audio con 'segundos' de tono fuerte (cuenta como voz) entre silencios."""
    t = np.arange(int(TASA * segundos)) / TASA
    tono = (6000 * np.sin(2 * np.pi * 220 * t)).astype(np.int16)
    pausa = np.zeros(int(TASA * silencio), dtype=np.int16)
    return np.concatenate([pausa, tono, pausa])


def pruebas_frase():
    for texto in ("Confirmo la instrucción.", "confirmo la instruccion", "Confirmó la instrucción", "Confirmo, la instrucción.",
                  "Cacao, confirmo la instrucción.", "Oye Cacao, confirmo la instrucción", "Confirmo las instrucción",
                  "confirmo la instrucciones", "Confirma la instrucción."):
        bien, parecido = cv.es_frase(texto)
        ok(f"vale: «{texto}»", bien, f"{parecido:.0f} %")
    for texto in ("Sí.", "sí, confirmo", "Confirmo.", "No confirmo la instrucción.", "La instrucción.",
                  "confirmo la instrucción de borrar todo", "Cacao.", "Cancela la instrucción", "Confirmar",
                  "Gracias por ver el video.", ""):
        bien, parecido = cv.es_frase(texto)
        ok(f"no vale: «{texto}»", not bien, f"{parecido:.0f} %")


def pruebas_frenos():
    ok("frase con voz suficiente: confirma", cv.evaluar("Confirmo la instrucción.", 1.2) is None)
    m = cv.evaluar("Confirmo la instrucción.", 0.2)
    ok("transcripción inventada (0,2 s de voz): no confirma", m and "voz" in m, m)
    m = cv.evaluar("Confirmo la instrucción.", 0.0)
    ok("transcripción inventada sobre silencio: no confirma", m is not None, m)
    m = cv.evaluar("Confirmo la instrucción.", 1.2, otro_audio=True)
    ok("otro audio sonando (un video con la frase): no confirma", m and "audio" in m, m)
    m = cv.evaluar("Confirmo la instrucción.", 1.2, tecla_fisica=False)
    ok("Ctrl+Espacio inyectado: no confirma", m and "físico" in m, m)
    m = cv.evaluar("Cacao.", 0.6, por_activacion=True)
    ok("solo la palabra de activación: no confirma", m and "activación" in m, m)
    m = cv.evaluar("Sí.", 0.6)
    ok("«sí» solo: no confirma", m is not None, m)


class AtajoFalso:
    def __init__(self):
        self.pulsar = threading.Event()

    def esperar(self, segundos):
        r = self.pulsar.wait(segundos)
        self.pulsar.clear()
        return r

    def sigue_pulsado(self):
        return False


class MicFalso:
    def __init__(self, audio):
        self.audio = audio

    def grabar_hasta(self, sigue):
        return self.audio, 1.0, time.perf_counter()


class TranscriptorFalso:
    def __init__(self, texto):
        self.texto = texto

    def transcribir(self, _wav):
        return self.texto


class EntradaFalsa:
    def __init__(self, al_teclear, espacio_fisico=True):
        self.al_teclear, self.espacio_fisico = al_teclear, espacio_fisico
        self.teclas_inyectadas = self.clics_inyectados = 0

    def iniciar(self):
        return True

    def cerrar(self):
        pass

    def clic_fisico_reciente(self, _desde):
        return False

    def espacio_fisico_reciente(self, _s=1.5):
        return self.espacio_fisico


def confirmar_con(texto, audio, espacio_fisico=True, otro_audio=False, esc=False, timeout_s=2):
    atajo = AtajoFalso()
    oyente = cv.Oyente(atajo, MicFalso(audio), TranscriptorFalso(texto), mirar_audio=lambda: otro_audio,
                       anotar=lambda *_: None)
    entradas = []

    def crear(_zonas, al_teclear):
        e = EntradaFalsa(al_teclear, espacio_fisico)
        entradas.append(e)
        return e

    c = Confirmar(None, timeout_s=timeout_s, entrada=crear, avisar=lambda *_: None)
    threading.Timer(0.3, atajo.pulsar.set).start()  # Reizo pulsa Ctrl+Espacio tras la pregunta
    if esc:
        threading.Timer(0.6, lambda: entradas[0].al_teclear(False)).start()
    t0 = time.monotonic()
    si = c.pedir("teclado", "Ejecutar teclado", extra=oyente.escuchar)
    return si, c.ultima["via"], time.monotonic() - t0, oyente.intentos


def pruebas_de_punta_a_punta():
    si, via, _, intentos = confirmar_con("Confirmo la instrucción.", voz(1.2))
    ok("Confirmar: la frase confirma por voz", si and via.startswith("voz"), f"{via}, {intentos}")
    si, via, dur, _ = confirmar_con("Sí.", voz(0.5))
    ok("Confirmar: «sí» no confirma y vence el tiempo (= no)", not si and "sin respuesta" in via, f"{via}, {dur:.1f} s")
    si, via, _, _ = confirmar_con("Confirmo la instrucción.", voz(0.2))
    ok("Confirmar: transcripción inventada con 0,2 s de voz no confirma", not si, via)
    si, via, _, _ = confirmar_con("Confirmo la instrucción.", voz(1.2), espacio_fisico=False)
    ok("Confirmar: Ctrl+Espacio inyectado no confirma", not si, via)
    si, via, _, _ = confirmar_con("Confirmo la instrucción.", voz(1.2), otro_audio=True)
    ok("Confirmar: con un video sonando no confirma", not si, via)
    si, via, _, _ = confirmar_con("Gracias.", voz(0.6), esc=True)
    ok("Confirmar: Esc físico sigue diciendo que no", not si and via == "teclado físico", via)


if __name__ == "__main__":
    for parte in (pruebas_frase, pruebas_frenos, pruebas_de_punta_a_punta):
        print(f"\n== {parte.__name__} ==")
        parte()
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
