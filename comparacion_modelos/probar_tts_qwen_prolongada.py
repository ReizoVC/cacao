"""
Prueba prolongada de la voz Qwen3-TTS de producción (tts_qwen.py + modelos/qwen3-tts/), en el banco: sin Cacao, sin
altavoz (el audio no se reproduce) y sin el LLM.

Comprueba los hashes y la guardia de juegos como Cacao, arranca el servidor por la misma tubería (tts_qwen.ProcesoTTS)
y sintetiza respuestas variadas durante --minutos (por defecto 30), partidas y normalizadas como en voz. Por cada
respuesta: tiempos por trozo, primer audio y huecos de la voz por trozos (simulada: cada trozo suena en cuanto está
listo y terminó el anterior). Cada 30 s: VRAM (toda la GPU) y RAM del servidor. Un fallo (caída, error, cuelgue o
lentitud con el tiempo máximo de tts_qwen) se anota y el servidor se rearranca, como en Cacao.
También mide aparte, 5 veces cada una, las frases #6 y #9 de la fase A (una oración larga: se parte por comas).

Uso: .venv\\Scripts\\python comparacion_modelos\\probar_tts_qwen_prolongada.py [--minutos 30]
Salida: comparacion_modelos/datos/tts_prolongada/<fecha>.json (ignorado por Git). No sobrescribe.
"""
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import psutil  # noqa: E402

import tts_qwen as tq  # noqa: E402

SALIDA = ROOT / "comparacion_modelos" / "datos" / "tts_prolongada"
FRASE_6 = "Tienes tres ventanas abiertas: el navegador, el bloc de notas y la terminal."
FRASE_9 = "En la carpeta de descargas hay doce archivos; el más reciente es un documento PDF de esta mañana."
APPS = ["Spotify", "la calculadora", "el bloc de notas", "Google Chrome", "Discord", "el explorador", "Steam", "Word"]
PLANTILLAS = [
    "Listo, puse el volumen al {n}%.",
    "Listo, abrí {app}.",
    "Hecho.",
    "El volumen está al {n} por ciento.",
    "No encontré {app}. ¿Quieres que busque otra parecida?",
    "Tienes {k} ventanas abiertas: {app}, {app2} y la terminal.",
    "Pausé el registro de hábitos. Cuando quieras, dime que lo reanude.",
    "No pude cerrar {app} porque tiene cambios sin guardar. ¿Quieres que lo intente de nuevo?",
    "En la carpeta de descargas hay {n} archivos; el más reciente es un documento de esta mañana.",
    "Buenos días. Son las {h}:{m:02d} y tienes {k} recordatorios pendientes.",
    "Encontré {k} resultados sobre el clima de esta semana. El primero dice que lloverá el miércoles y que el fin de "
    "semana estará despejado.",
    "Abrí {app} y puse el volumen al {n} por ciento. Si quieres, también puedo dejar la música sonando mientras "
    "trabajas, o avisarte cuando termine la descarga.",
    "Revisé la carpeta. Hay {n} archivos. El más grande ocupa {g},{d} GB. ¿Quieres que lo mueva a otra carpeta?",
    "Encontré tres resultados. El primero habla de {app}. El segundo es de hace {k} días. El tercero no parece "
    "útil. ¿Abro el primero?",
]


def respuesta(rnd):
    app, app2 = rnd.sample(APPS, 2)
    i = rnd.randrange(len(PLANTILLAS))
    return i, PLANTILLAS[i].format(n=rnd.randint(0, 100), app=app, app2=app2, k=rnd.randint(2, 9),
                                         h=rnd.randint(1, 12), m=rnd.choice([0, 15, 30, 45, 5]), g=rnd.randint(1, 9),
                                         d=rnd.randint(1, 9))


def vram():
    s = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
    return int(s.strip().splitlines()[0].split(",")[1])


def decir(proceso, texto):
    """Sintetiza los trozos en orden (como LocutorQwen) y simula la reproducción. FalloTTS sube."""
    listo, inicio, fin, huecos, trozos = 0.0, None, 0.0, [], []
    for trozo in tq.partir(texto):
        t = time.perf_counter()
        audio = proceso.sintetizar(tq.normalizar_texto(trozo), tq.tiempo_maximo(trozo))
        s, dur = time.perf_counter() - t, len(audio) / proceso.tasa
        trozos.append({"caracteres": len(trozo), "sintesis_s": round(s, 3), "audio_s": round(dur, 3)})
        listo += s
        if inicio is None:
            inicio, fin = listo, listo + dur
        else:
            huecos.append(round(max(0.0, listo - fin), 3))
            fin = max(fin, listo) + dur
    return {"primer_audio_s": round(inicio, 3), "huecos_s": huecos, "trozos": trozos}


def main():
    minutos = float(sys.argv[sys.argv.index("--minutos") + 1]) if "--minutos" in sys.argv else 30.0
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / f"{time.strftime('%Y-%m-%d_%H%M')}.json"
    if destino.exists():
        raise SystemExit(f"{destino} ya existe: no lo sobrescribo.")
    fallo = tq.verificar_hashes()
    if fallo:
        raise SystemExit(f"Hashes: {fallo}")
    from guardia_juego import exigir_gpu_libre
    exigir_gpu_libre("Qwen3-TTS")
    r = {"fecha": time.strftime("%Y-%m-%d %H:%M"), "minutos": minutos, "vram_antes_mib": vram(), "fallos": [],
         "muestras": [], "respuestas": []}

    def arrancar():
        t = time.perf_counter()
        p = tq.ProcesoTTS(tq.comando())
        r.setdefault("arranques_s", []).append(round(time.perf_counter() - t, 2))
        return p

    proceso = arrancar()
    r["vram_cargado_mib"] = vram()
    largas = {}
    for nombre, frase in (("frase_6", FRASE_6), ("frase_9", FRASE_9)):
        largas[nombre] = {"trozos": tq.partir(frase), "medidas": [decir(proceso, frase) for _ in range(5)]}
    r["frases_6_y_9"] = largas
    rnd = random.Random(42)
    inicio, ultima_muestra = time.monotonic(), 0.0
    while time.monotonic() - inicio < minutos * 60:
        plantilla, texto = respuesta(rnd)
        try:
            fila = decir(proceso, texto)
            r["respuestas"].append({"plantilla": plantilla,
                                    **{k: fila[k] for k in ("primer_audio_s", "huecos_s")},
                                    "sintesis_s": round(sum(t["sintesis_s"] for t in fila["trozos"]), 3),
                                    "audio_s": round(sum(t["audio_s"] for t in fila["trozos"]), 3)})
        except tq.FalloTTS as e:
            r["fallos"].append({"t_min": round((time.monotonic() - inicio) / 60, 2), "motivo": str(e)})
            print(f"FALLO: {e}; rearranco", flush=True)
            proceso.matar()
            proceso = arrancar()
        if time.monotonic() - ultima_muestra >= 30:
            ultima_muestra = time.monotonic()
            try:
                rss = psutil.Process(proceso.proc.pid).memory_info().rss
            except psutil.Error:
                rss = 0
            r["muestras"].append({"t_min": round((time.monotonic() - inicio) / 60, 2), "vram_mib": vram(),
                                  "ram_servidor_mb": round(rss / 2**20), "respuestas": len(r["respuestas"])})
            m = r["muestras"][-1]
            print(f"{m['t_min']:5.1f} min: {m['respuestas']} respuestas, VRAM {m['vram_mib']} MiB, "
                  f"RAM {m['ram_servidor_mb']} MB, fallos {len(r['fallos'])}", flush=True)
    proceso.cerrar()
    filas = r["respuestas"]
    primeros = sorted(f["primer_audio_s"] for f in filas)
    vrams = [m["vram_mib"] for m in r["muestras"]]
    rams = [m["ram_servidor_mb"] for m in r["muestras"]]
    r["resumen"] = {
        "respuestas": len(filas), "fallos": len(r["fallos"]),
        "rtf_total": round(sum(f["sintesis_s"] for f in filas) / sum(f["audio_s"] for f in filas), 3),
        "primer_audio_mediana_s": primeros[len(primeros) // 2], "primer_audio_p95_s":
            primeros[int(len(primeros) * 0.95)], "primer_audio_max_s": primeros[-1],
        "respuestas_con_hueco": sum(1 for f in filas if any(h > 0 for h in f["huecos_s"])),
        "hueco_max_s": max((h for f in filas for h in f["huecos_s"]), default=0.0),
        "vram_min_max_mib": [min(vrams), max(vrams)], "ram_servidor_primera_ultima_mb": [rams[0], rams[-1]],
        "ram_servidor_max_mb": max(rams),
        "frases_6_y_9_primer_audio_s": {k: [m["primer_audio_s"] for m in v["medidas"]] for k, v in largas.items()},
    }
    destino.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r["resumen"], ensure_ascii=False, indent=1))
    print(f"Guardado en {destino}")


if __name__ == "__main__":
    main()
