"""
Graba muestras reales de la palabra "Cacao" con la voz de Reizo, guiado en voz alta (Piper, por los altavoces): cada
toma anuncia qué variante decir, suena un pitido y se graban VENTANA_S segundos, sin tocar el teclado (así puede
alejarse del micrófono). Guarda WAV de 16 kHz en voz_pruebas/cacao_real/ (no va a git) y un indice.json con la
categoría de cada toma. Las tomas casi sin voz se repiten.

Categorías: positivos (normal, bajo, alto, rápido, lento, pregunta, lejos, con ruido de fondo), "de corrido" (Cacao
y una orden) y negativos parecidos (palabras que se parecen a Cacao, dichas por él).

Uso: .venv\\Scripts\\python grabar_cacao.py [--solo categoria]   (sin el modelo; Piper y el micrófono)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from microfono import TASA, Microfono, analizar_audio
from transcripcion import a_wav

BASE = Path(__file__).parent
CARPETA = BASE / "voz_pruebas" / "cacao_real"
VENTANA_S = 2.5
VOZ_MIN_S = 0.15

PLAN = [  # (categoría, cuántas, indicación)
    ("normal", 8, "Di Cacao, normal, cerca del micrófono."),
    ("bajo", 5, "Di Cacao en voz baja."),
    ("alto", 5, "Di Cacao en voz alta, como llamando a alguien."),
    ("rapido", 4, "Di Cacao rápido."),
    ("lento", 4, "Di Cacao despacio."),
    ("pregunta", 3, "Di Cacao como preguntando."),
    ("lejos", 6, "Aléjate uno o dos metros del micrófono y di Cacao."),
    ("ruido", 6, "Con música o un video de fondo, di Cacao."),
    ("de_corrido", 6, "Di Cacao y una orden, de corrido. Por ejemplo: Cacao, sube el volumen."),
    ("parecida", 10, None),
]
PARECIDAS = ["caso", "Macao", "cacahuate", "Caracas", "caca", "ocaso", "cacería", "caos", "acá", "Picasso"]


class Guia:
    def __init__(self):
        self.voz = PiperVoice.load(str(BASE / "modelos" / "piper" / "es_MX-claude-high.onnx"))

    def decir(self, texto):
        audio = np.concatenate([np.frombuffer(t.audio_int16_bytes, dtype=np.int16) for t in self.voz.synthesize(texto)])
        sd.play(audio, self.voz.config.sample_rate)
        sd.wait()

    def pitido(self):
        t = np.arange(int(0.12 * 44100)) / 44100
        sd.play((0.25 * np.sin(2 * np.pi * 880 * t)).astype(np.float32), 44100)
        sd.wait()


def grabar(mic, segundos):
    fin = time.perf_counter() + segundos
    audio, _, _ = mic.grabar_hasta(lambda: time.perf_counter() < fin)
    return audio


def main():
    solo = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    CARPETA.mkdir(parents=True, exist_ok=True)
    indice_ruta = CARPETA / "indice.json"
    indice = json.loads(indice_ruta.read_text(encoding="utf-8")) if indice_ruta.exists() else []
    guia, mic = Guia(), Microfono()
    print(f"Micrófono: {mic.nombre}", flush=True)
    guia.decir("Vamos a grabar muestras de mi nombre. Después de cada pitido tienes dos segundos y medio.")
    for categoria, cuantas, indicacion in PLAN:
        if solo and categoria != solo:
            continue
        if categoria == "lejos":
            guia.decir("Ahora aléjate uno o dos metros. Tienes cinco segundos.")
            time.sleep(5)
        if categoria == "ruido":
            guia.decir("Pon música o un video en los altavoces, a volumen normal. Tienes diez segundos.")
            time.sleep(10)
        if categoria == "parecida":
            guia.decir("Ahora no digas Cacao: repite la palabra que te diga.")
        n = 1
        intentos = 0
        while n <= cuantas and intentos < cuantas * 3:
            intentos += 1
            texto = indicacion or f"Di: {PARECIDAS[n - 1]}."
            guia.decir(f"{n}. {texto}")
            time.sleep(0.25)
            guia.pitido()
            audio = grabar(mic, VENTANA_S)
            datos = analizar_audio(audio)
            if datos["voz_s"] < VOZ_MIN_S:
                print(f"  {categoria} {n}: casi sin voz ({datos['voz_s']} s, pico {datos['pico']}); se repite", flush=True)
                guia.decir("No te oí bien. Otra vez.")
                continue
            nombre = f"{categoria}_{len([x for x in indice if x['categoria'] == categoria]) + 1:02d}.wav"
            (CARPETA / nombre).write_bytes(a_wav(audio))
            indice.append({"archivo": nombre, "categoria": categoria,
                           "texto": PARECIDAS[n - 1] if categoria == "parecida" else "cacao",
                           "hora": time.strftime("%Y-%m-%d %H:%M:%S"), **datos})
            indice_ruta.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {nombre}: voz {datos['voz_s']} s, pico {datos['pico']}", flush=True)
            n += 1
        if categoria == "lejos":
            guia.decir("Ya puedes volver.")
        if categoria == "ruido":
            guia.decir("Ya puedes quitar la música.")
    guia.decir("Listo, terminamos. Gracias.")
    mic.cerrar()
    print(f"Total: {len(indice)} tomas en {CARPETA}", flush=True)


if __name__ == "__main__":
    main()
