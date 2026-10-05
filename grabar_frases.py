"""
Graba frases de prueba con pulsar para hablar: mantén ctrl+espacio mientras hablas y suelta al terminar.
Guarda WAV de 16 kHz, mono, 16 bits en voz_pruebas/frase_<n>.wav (los .wav no van a git).
Uso: .venv\\Scripts\\python grabar_frases.py [cantidad=3] [prefijo=frase] [--todo]
--todo guarda también las pulsaciones en silencio o muy cortas (para validar los frenos de voz.py).
"""
import sys
import time
from pathlib import Path

import numpy as np

from microfono import TASA, AtajoHablar, Microfono
from transcripcion import a_wav

CARPETA = Path(__file__).parent / "voz_pruebas"
MINIMO_S = 0.6  # pulsaciones más cortas se descartan (toque accidental)
PICO_MINIMO = 300  # por debajo es silencio: micrófono silenciado o equivocado

if __name__ == "__main__":
    guardar_todo = "--todo" in sys.argv
    args = [x for x in sys.argv[1:] if x != "--todo"]
    cantidad = int(args[0]) if args else 3
    prefijo = args[1] if len(args) > 1 else "frase"
    CARPETA.mkdir(exist_ok=True)
    microfono, atajo = Microfono(), AtajoHablar("ctrl+espacio")
    print(f"Micrófono: {microfono.nombre}. Atajo registrado: {atajo.iniciar()}", flush=True)
    n = 1
    while n <= cantidad:
        print(f"Frase {n}: mantén ctrl+espacio y habla...", flush=True)
        atajo.esperar()
        audio, pulsada, _ = microfono.grabar_hasta(atajo.sigue_pulsado)
        nivel = int(np.abs(audio).max()) if len(audio) else 0
        if not guardar_todo and (pulsada < MINIMO_S or nivel < PICO_MINIMO):
            motivo = "pulsación muy corta" if pulsada < MINIMO_S else "solo silencio (¿micrófono silenciado?)"
            print(f"Frase {n} descartada: {motivo}; tecla {pulsada:.2f} s, pico {nivel}/32767. Repítela.", flush=True)
            continue
        ruta = CARPETA / f"{prefijo}_{n}.wav"
        ruta.write_bytes(a_wav(audio))
        print(f"Frase {n} guardada: {len(audio) / TASA:.1f} s, pico {nivel}/32767 -> {ruta.name}", flush=True)
        n += 1
        time.sleep(0.3)
