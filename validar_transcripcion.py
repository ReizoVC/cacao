"""
Valida la transcripción nativa de Gemma (sin pista) con las grabaciones de voz_pruebas/validacion_<n>.wav y las
referencias de voz_pruebas/validacion.json. Solo transcribe: no ejecuta nada.
Aplica los mismos frenos que voz.py (silencio antes de transcribir; palabras por segundo de voz después) y, para
ver qué habría pasado sin frenos, transcribe también las pulsaciones que el freno de silencio descarta.
Uso: .venv\\Scripts\\python validar_transcripcion.py   -> resultados_validacion_voz.json
"""
import json
import re
import sys
import time
import unicodedata
import wave
from pathlib import Path

import numpy as np

import modelo
from microfono import analizar_audio
from transcripcion import TranscriptorNativo, TranscriptorWhisper, contar_palabras, transcripcion_plausible
from vision import ManejadorVision

BASE = Path(__file__).parent
CARPETA = BASE / "voz_pruebas"
MIN_VOZ_S = 0.25  # igual que voz.py: menos voz que esto es una pulsación en silencio


def palabras(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("%", " por ciento").replace("vs code", "visual studio code")
    return re.findall(r"\w+", t)


def distancia(a, b):
    """Distancia de edición entre listas de palabras (sustituciones + inserciones + borrados)."""
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        anterior, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            anterior, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, anterior + (x != y))
    return d[len(b)]


NUMEROS = {"20": "veinte", "30": "treinta", "50": "cincuenta"}

if __name__ == "__main__":
    referencias = json.loads((CARPETA / "validacion.json").read_text(encoding="utf-8"))
    motor = sys.argv[1] if len(sys.argv) > 1 else "gemma"
    if motor == "whisper":
        transcriptor = TranscriptorWhisper(sys.argv[2] if len(sys.argv) > 2 else "small",
                                           tipo=sys.argv[3] if len(sys.argv) > 3 else "float16")
        motor = "_".join(["whisper"] + sys.argv[2:4])
        transcriptor.transcribir((CARPETA / "validacion_1.wav").read_bytes())  # calentamiento (kernels de CUDA)
    else:
        config = modelo.cargar_config()
        transcriptor = TranscriptorNativo(modelo.crear_llm(config), ManejadorVision(config["mmproj"]))
    filas = []
    for r in referencias:
        ruta = CARPETA / f"validacion_{r['n']}.wav"
        if not ruta.exists():
            continue
        with wave.open(str(ruta)) as w:
            audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        analisis = analizar_audio(audio)
        t = time.perf_counter()
        texto = transcriptor.transcribir(ruta.read_bytes())
        segundos = time.perf_counter() - t
        ref = [NUMEROS.get(p, p) for p in palabras(r["referencia"])]
        hip = [NUMEROS.get(p, p) for p in palabras(texto)]
        silencio = analisis["voz_s"] < MIN_VOZ_S
        plausible = transcripcion_plausible(texto, analisis["voz_s"])
        filas.append({**r, **analisis, "transcripcion": texto, "segundos": round(segundos, 2),
                      "errores": distancia(ref, hip), "palabras_ref": len(ref), "palabras_transcritas": contar_palabras(texto),
                      "freno": "silencio" if silencio else ("palabras" if not plausible else None),
                      "pasaria_al_agente": not silencio and plausible and bool(texto)})
        f = filas[-1]
        print(f"{f['n']:>2} [{f['freno'] or 'pasa'}] voz {f['voz_s']} s | ref: {r['referencia'] or '(' + r['nota'] + ')'}"
              f"\n   -> {texto!r}  errores {f['errores']}/{f['palabras_ref']}  ({f['segundos']} s)", flush=True)
    con_voz = [f for f in filas if f["referencia"]]
    total_ref = sum(f["palabras_ref"] for f in con_voz)
    resumen = {"grabaciones": len(filas), "wer_%": round(100 * sum(f["errores"] for f in con_voz) / max(total_ref, 1), 1),
               "frenadas": [f["n"] for f in filas if f["freno"]],
               "sin_voz_que_pasarian": [f["n"] for f in filas if not f["referencia"] and f["pasaria_al_agente"]]}
    print(json.dumps(resumen, ensure_ascii=False))
    (BASE / f"resultados_validacion_voz_{motor}.json").write_text(
        json.dumps({"resumen": resumen, "filas": filas}, ensure_ascii=False, indent=1), encoding="utf-8")
