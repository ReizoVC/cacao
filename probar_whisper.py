"""
Transcribe WAV con faster-whisper "small" en la GPU, para comparar con el audio nativo de Gemma
(probar_audio_nativo.py). Uso: .venv\\Scripts\\python probar_whisper.py a.wav [b.wav ...]
-> resultados_whisper.json
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
# cuBLAS y cuDNN vienen en las ruedas nvidia-* de pip; CTranslate2 los busca en el PATH de DLL
for paquete in ("cublas", "cudnn"):
    carpeta = BASE / ".venv" / "Lib" / "site-packages" / "nvidia" / paquete / "bin"
    if carpeta.is_dir():
        os.add_dll_directory(str(carpeta))
        os.environ["PATH"] = str(carpeta) + os.pathsep + os.environ["PATH"]

from faster_whisper import WhisperModel  # noqa: E402


def vram_mb():
    salida = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                            capture_output=True, text=True).stdout
    return int(salida.strip().splitlines()[0])


if __name__ == "__main__":
    vram_inicial = vram_mb()
    t = time.perf_counter()
    modelo = WhisperModel("small", device="cuda", compute_type="float16")
    carga = time.perf_counter() - t
    vram_modelo = vram_mb()
    filas = []
    for ruta in sys.argv[1:]:
        t = time.perf_counter()
        segmentos, _ = modelo.transcribe(ruta, language="es", beam_size=5, vad_filter=False,
                                          initial_prompt=os.environ.get("PISTA") or None)
        texto = " ".join(s.text.strip() for s in segmentos)
        filas.append({"archivo": Path(ruta).name, "transcripcion": texto,
                      "segundos": round(time.perf_counter() - t, 2), "vram_mb": vram_mb()})
        print(json.dumps(filas[-1], ensure_ascii=False), flush=True)
    resumen = {"carga_s": round(carga, 1), "vram_antes_mb": vram_inicial, "vram_con_modelo_mb": vram_modelo,
               "vram_whisper_mb": max(f["vram_mb"] for f in filas) - vram_inicial if filas else None, "filas": filas}
    print(json.dumps({k: v for k, v in resumen.items() if k != "filas"}))
    (BASE / f"resultados_whisper{'_pista' if os.environ.get('PISTA') else ''}.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
