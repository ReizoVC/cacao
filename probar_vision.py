"""
Prueba real de ver_pantalla: solo captura la pantalla y la lee (no usa mouse ni teclado).
Mide VRAM (nvidia-smi) y tiempos por captura con el presupuesto indicado (por defecto 280).
Uso: .venv\\Scripts\\python probar_vision.py [presupuesto ...] [--guardar carpeta]
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from modelo import cargar_config, crear_llm
from vision import ManejadorVision, capturar

PREGUNTA = "Describe en español, en 3 o 4 frases, qué hay en esta captura de pantalla: ventanas, apps y texto visible."


def vram_mib():
    salida = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                            capture_output=True, text=True).stdout
    return int(salida.strip().splitlines()[0])


if __name__ == "__main__":
    args = sys.argv[1:]
    guardar = None
    if "--guardar" in args:
        i = args.index("--guardar")
        guardar = Path(args[i + 1])
        del args[i:i + 2]
    presupuestos = [int(a) for a in args] or [280]

    medidas = {"vram_inicial": vram_mib()}
    config = cargar_config()
    llm = crear_llm(config)
    medidas["vram_modelo"] = vram_mib()
    vision = ManejadorVision(config["mmproj"])
    resultados = []
    for presupuesto in presupuestos:
        for repeticion in range(2):  # la primera incluye cargar el mmproj si cambió el presupuesto
            vision.fijar_presupuesto(presupuesto)
            t0 = time.perf_counter()
            data_url, info = capturar("completa")
            t1 = time.perf_counter()
            r = vision(llama=llm, messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": PREGUNTA}]}],
                temperature=0.3, top_p=0.95, top_k=64, max_tokens=200)
            t2 = time.perf_counter()
            fila = {"presupuesto": presupuesto, "repeticion": repeticion + 1,
                    "captura_s": round(t1 - t0, 3), "modelo_s": round(t2 - t1, 2), "total_s": round(t2 - t0, 2),
                    "prompt_tokens": r["usage"]["prompt_tokens"], "tokens_generados": r["usage"]["completion_tokens"],
                    "imagen": f"{info['ancho']}x{info['alto']}", "vram_mib": vram_mib(),
                    "descripcion": r["choices"][0]["message"]["content"]}
            resultados.append(fila)
            print(json.dumps(fila, ensure_ascii=False), flush=True)
            if guardar and repeticion == 0:
                import base64
                (guardar / f"captura_{presupuesto}.jpg").write_bytes(base64.b64decode(data_url.split(",")[1]))
    # tokens que ocupa solo el texto, para restarlos y saber cuántos usa la imagen
    medidas["tokens_texto"] = len(llm.tokenize(PREGUNTA.encode("utf-8"), add_bos=False))
    medidas["resultados"] = resultados
    Path(__file__).with_name("resultados_vision.json").write_text(
        json.dumps(medidas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in medidas.items() if k != "resultados"}))
