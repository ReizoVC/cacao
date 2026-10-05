"""
Transcribe WAV con el audio NATIVO de Gemma 4 12B: el mmproj-F16 trae codificador de audio (clip.has_audio_encoder,
proyector gemma4ua) y libmtmd de llama-cpp-python 0.3.36 reconoce WAV/FLAC/MP3 en mtmd_helper_bitmap_init_from_buf.
El handler multimodal solo acepta partes "image_url", así que el audio va como data URL en una de ellas; libmtmd
detecta por los bytes que es audio.
Uso: .venv\\Scripts\\python probar_audio_nativo.py a.wav [b.wav ...]   -> resultados_audio_nativo.json
"""
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import modelo
from vision import ManejadorVision

BASE = Path(__file__).parent
INSTRUCCION = ("Transcribe literalmente lo que se dice en este audio, en español. Responde solo con la "
               "transcripción, sin comillas ni comentarios.")
if os.environ.get("PISTA"):  # vocabulario esperado, igual que initial_prompt en probar_whisper.py
    INSTRUCCION += f" Suelen ser órdenes como estas: {os.environ['PISTA']}"


def vram_mb():
    salida = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                            capture_output=True, text=True).stdout
    return int(salida.strip().splitlines()[0])


def transcribir(llm, handler, ruta):
    datos = base64.b64encode(Path(ruta).read_bytes()).decode()
    mensajes = [{"role": "user", "content": [
        {"type": "text", "text": INSTRUCCION},
        {"type": "image_url", "image_url": {"url": f"data:audio/wav;base64,{datos}"}}]}]
    t = time.perf_counter()
    r = handler(llama=llm, messages=mensajes, temperature=0.0, max_tokens=120)
    return r["choices"][0]["message"]["content"].strip(), time.perf_counter() - t


if __name__ == "__main__":
    vram_inicial = vram_mb()
    config = modelo.cargar_config()
    llm = modelo.crear_llm(config)
    vram_modelo = vram_mb()
    handler = ManejadorVision(config["mmproj"])
    filas = []
    for ruta in sys.argv[1:]:
        texto, segundos = transcribir(llm, handler, ruta)
        filas.append({"archivo": Path(ruta).name, "transcripcion": texto, "segundos": round(segundos, 2),
                      "vram_mb": vram_mb()})
        print(json.dumps(filas[-1], ensure_ascii=False), flush=True)
    resumen = {"vram_antes_mb": vram_inicial, "vram_con_modelo_mb": vram_modelo,
               "vram_extra_audio_mb": max(f["vram_mb"] for f in filas) - vram_modelo if filas else None,
               "filas": filas}
    print(json.dumps({k: v for k, v in resumen.items() if k != "filas"}))
    (BASE / f"resultados_audio_nativo{'_pista' if os.environ.get('PISTA') else ''}.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1),
                                                       encoding="utf-8")
