"""
Activaciones falsas con audio real de la habitación (grabar_fondo_cacao.py: música y videos que dicen "cacao"), para
uno o más detectores y umbrales. Primera etapa: el detector (CPU). Segunda etapa, como en voz.py: Whisper transcribe
lo que se grabaría tras la activación (1,6 s de búfer previo + 2,5 s) y solo cuenta si empieza con "Cacao".
Whisper usa la GPU: no se carga con un juego activo (guardia_juego).

Uso: .venv\\Scripts\\python evaluar_fondo_cacao.py modelo.npz[:umbral] [otro.npz:umbral ...] [--sin-whisper]
"""
import json
import sys
from pathlib import Path

import numpy as np

import palabra_activacion as pa
from entrenar_cacao import detecciones, leer_wav

CARPETA = Path(__file__).parent / "voz_pruebas" / "cacao_real"


def main():
    modelos = [a for a in sys.argv[1:] if not a.startswith("--")]
    audios = {p.stem.removeprefix("fondo_"): leer_wav(p) for p in sorted(CARPETA.glob("fondo_*.wav"))}
    transcriptor = None
    if "--sin-whisper" not in sys.argv:
        from transcripcion import TranscriptorWhisper, a_wav
        transcriptor = TranscriptorWhisper("large-v3-turbo", tipo="int8_float16")
    resultado = {}
    for m in modelos:
        ruta, _, umbral = m.partition(":")
        modelo = pa.ModeloCacao(ruta)
        umbral = float(umbral) if umbral else modelo.umbral
        clave = f"{Path(ruta).stem}@{umbral}"
        resultado[clave] = {}
        for tipo, audio in audios.items():
            momentos = detecciones(modelo, audio, umbral, modelo.paciencia)
            pasan = []
            for t in momentos:
                i = int(t * pa.TASA)
                trozo = audio[max(0, i - int(1.6 * pa.TASA)): i + int(2.5 * pa.TASA)]
                texto = transcriptor.transcribir(a_wav(trozo)) if transcriptor else ""
                if transcriptor and pa.empieza_con_la_palabra(texto):
                    pasan.append({"segundo": round(t, 1), "texto": texto})
            resultado[clave][tipo] = {"minutos": round(len(audio) / pa.TASA / 60, 1), "primera_etapa": len(momentos),
                                      "segundos": [round(t, 1) for t in momentos],
                                      "pasan_segunda_etapa": len(pasan) if transcriptor else None,
                                      "detalle_segunda": pasan}
        print(clave, json.dumps(resultado[clave], ensure_ascii=False), flush=True)
    (Path(__file__).parent / "resultados_cacao_fondo_real.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
