"""
Graba el sonido de la habitación mientras Reizo pone música o videos que dicen "cacao" en los altavoces, para medir
después las activaciones falsas de los detectores con el mismo audio (evaluar_fondo_cacao.py). Guiado en voz alta;
Reizo no debe decir "Cacao" durante la grabación. Guarda voz_pruebas/cacao_real/fondo_<tipo>.wav (no va a git).

Uso: .venv\\Scripts\\python grabar_fondo_cacao.py [minutos_musica=3] [minutos_videos=4]
"""
import sys
import time

from grabar_cacao import CARPETA, Guia
from microfono import Microfono
from transcripcion import a_wav


def tramo(guia, mic, tipo, minutos, indicacion):
    guia.decir(f"{indicacion} Tienes quince segundos para ponerlo. No digas Cacao mientras grabo.")
    time.sleep(15)
    guia.decir(f"Grabando {minutos} minutos.")
    fin = time.perf_counter() + minutos * 60
    audio, _, _ = mic.grabar_hasta(lambda: time.perf_counter() < fin)
    (CARPETA / f"fondo_{tipo}.wav").write_bytes(a_wav(audio))
    print(f"fondo_{tipo}.wav: {len(audio) / 16000 / 60:.1f} min", flush=True)
    guia.decir("Listo, ya puedes pararlo.")


if __name__ == "__main__":
    musica = float(sys.argv[1]) if len(sys.argv) > 1 else 3
    videos = float(sys.argv[2]) if len(sys.argv) > 2 else 4
    CARPETA.mkdir(parents=True, exist_ok=True)
    guia, mic = Guia(), Microfono()
    tramo(guia, mic, "musica", musica, "Pon música en los altavoces, a volumen normal.")
    time.sleep(5)
    tramo(guia, mic, "videos", videos, "Pon videos que digan cacao, por ejemplo de chocolate o de cacao, en los altavoces.")
    guia.decir("Terminamos esta parte.")
    mic.cerrar()
