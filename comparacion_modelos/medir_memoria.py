"""
Memoria máxima liberable sin perder calidad (pedido del 2026-10-11): VRAM al cargar y pico de un arranque de voz con el
modelo activo de config.json (perfiles), sin micrófono, sin isla, sin wiki y con herramientas simuladas.

Cada variante corre en su propio proceso y solo cambia opciones que no tocan el prompt, el esquema ni el contexto
(no se miden contexto menor, KV a 4 bits ni Whisper más pequeño):
  base        swa_full por defecto, caché KV f16, sin flash attention, use_mmap=true (valores de llama-cpp-python)
  swa_false   base + swa_full=false
  flash       base + flash attention (KV f16)
  kv8         base + flash attention + caché KV q8_0 (cuantizar la V exige flash)
  sin_mmap    base + use_mmap=false
  todas       swa_full=false + flash + KV q8_0 + use_mmap=false (= el perfil de producción de Qwen)
Pasos de cada variante, como voz.preparar(): cargar_modelo(); Whisper de config.json (faster-whisper en la GPU);
calentamiento (prompt de voz con "hola", silencio a Whisper, Piper); luego, con el pico muestreado cada 0,25 s, un
pedido simulado ("pon el volumen al 30") y una captura SINTÉTICA por ver_pantalla (la ruta multimodal de
pedir_accion, presupuesto 560 como _presupuesto_imagen); no captura la pantalla real.

Uso: .venv\\Scripts\\python comparacion_modelos\\medir_memoria.py [--perfil gemma|qwen9b] [variantes...]
--perfil: el perfil de config.json que se mide, sea cual sea modelo_activo (por defecto, el activo).
Salida: comparacion_modelos/datos/memoria/<fecha>.json (ignorado por Git). No sobrescribe.
"""
import base64
import gc
import io
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SALIDA = ROOT / "comparacion_modelos" / "datos" / "memoria"
BASE = {"swa_full": None, "type_k": "f16", "type_v": "f16", "flash_attn": False, "use_mmap": True}
VARIANTES = {
    "base": {},
    "swa_false": {"swa_full": False},
    "flash": {"flash_attn": True},
    "kv8": {"flash_attn": True, "type_k": "q8_0", "type_v": "q8_0"},
    "sin_mmap": {"use_mmap": False},
    "todas": {"swa_full": False, "flash_attn": True, "type_k": "q8_0", "type_v": "q8_0", "use_mmap": False},
}
PEDIDO = "pon el volumen al 30"


def gpu():
    s = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, check=True).stdout
    total, usada = (int(v) for v in s.strip().split(","))
    return total, usada


class Pico(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.pico, self.parar = 0, threading.Event()

    def run(self):
        while not self.parar.is_set():
            self.pico = max(self.pico, gpu()[1])
            time.sleep(0.25)


def captura_sintetica():
    from PIL import Image, ImageDraw
    imagen = Image.new("RGB", (1920, 1080), (240, 240, 240))
    d = ImageDraw.Draw(imagen)
    d.rectangle([0, 0, 1920, 40], fill=(30, 30, 30))
    d.rectangle([200, 200, 900, 700], outline=(0, 0, 0), width=3)
    d.rectangle([600, 620, 760, 670], fill=(0, 120, 215))
    d.text((630, 635), "Aceptar", fill=(255, 255, 255))
    d.text((220, 220), "Sin título: Bloc de notas", fill=(0, 0, 0))
    datos = io.BytesIO()
    imagen.save(datos, format="PNG")
    return "data:image/png;base64," + base64.b64encode(datos.getvalue()).decode()


def hijo(nombre):
    os.environ.update(SIN_REALES="1", CONFIRMAR="s")
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    import psutil

    import modelo
    perfil = os.environ.get("_PERFIL_HIJO")
    if perfil:  # el perfil pedido, sin tocar config.json
        _aplicar = modelo.aplicar_perfil
        modelo.aplicar_perfil = lambda config: _aplicar({**config, "modelo_activo": perfil})
    _cargar = modelo.cargar_config
    opciones = {**BASE, **VARIANTES[nombre]}

    def cargar_config():
        config = {**_cargar(), **opciones}
        if config["swa_full"] is None:
            config.pop("swa_full")
        return config

    modelo.cargar_config = cargar_config
    fila = {"variante": nombre, "opciones": opciones}
    total, fila["vram_base_mib"] = gpu()
    fila["vram_total_mib"] = total
    import agente_minimo as a

    # como el banco: ni memoria.db ni la wiki personal entran en el prompt (rutas temporales que no existen)
    import tempfile
    temporal = Path(tempfile.mkdtemp(prefix="cacao_medir_memoria_"))
    a.memoria.RUTA, a.wiki.VAULT = temporal / "memoria.db", temporal / "wiki"
    for herramienta in list(a.IMPLEMENTACIONES):
        a.IMPLEMENTACIONES[herramienta] = (lambda n: lambda **args: (
            {"ok": True, "volumen_actual": args.get("cantidad", 50), "silenciado": False} if n == "volumen"
            else {"ok": True, "simulado": True}))(herramienta)
    a.confirmar = lambda *args, **kwargs: False
    fila["modelo_activo"], fila["modelo"] = a.CONFIG.get("modelo_activo"), Path(a.CONFIG["modelo"]).name
    t = time.perf_counter()
    a.cargar_modelo()
    fila["carga_modelo_s"] = round(time.perf_counter() - t, 1)
    gc.collect()
    fila["vram_modelo_mib"] = gpu()[1]
    import voz
    t = time.perf_counter()
    transcriptor = voz.crear_transcriptor()
    fila["carga_whisper_s"] = round(time.perf_counter() - t, 1)
    fila["vram_modelo_whisper_mib"] = gpu()[1]
    ruta_voz = Path(voz.CONFIG_VOZ["piper_voz"])
    locutor = voz.Locutor(ruta_voz if ruta_voz.is_absolute() else ROOT / ruta_voz, voz.CONFIG_VOZ["velocidad"])
    historial = [{"role": "system", "content": a.prompt_sistema(voz=True)}]
    a.llm.create_chat_completion(messages=historial + [{"role": "user", "content": "hola"}], max_tokens=1)
    silencio = voz.a_wav(voz.np.zeros(voz.TASA // 2, dtype=voz.np.int16))
    transcriptor.transcribir(silencio)
    list(locutor.voz.synthesize("hola"))
    fila["vram_calentado_mib"] = gpu()[1]
    pico = Pico()
    pico.start()
    t = time.perf_counter()
    fila["respuesta_pedido"] = a.atender(PEDIDO, historial)
    fila["pedido_s"] = round(time.perf_counter() - t, 1)
    fila["vram_tras_pedido_mib"] = gpu()[1]
    t = time.perf_counter()
    try:
        accion = a.pedir_accion(historial + [{"role": "user", "content": [
            {"type": "text", "text": "Resultado de ver_pantalla: captura de la ventana activa."},
            {"type": "image_url", "image_url": {"url": captura_sintetica()}}]}])
        fila["vision_herramienta"] = accion.get("herramienta")
    except Exception as e:  # se informa: la VRAM medida hasta aquí sigue valiendo
        fila["vision_error"] = f"{type(e).__name__}: {e}"
    fila["vision_s"] = round(time.perf_counter() - t, 1)
    fila["vram_tras_vision_mib"] = gpu()[1]
    transcriptor.transcribir(silencio)
    pico.parar.set()
    pico.join()
    fila["vram_pico_mib"] = pico.pico
    fila["libre_en_pico_mib"] = total - pico.pico
    m = psutil.Process().memory_info()
    fila["ram_working_set_mb"], fila["ram_privada_mb"] = round(m.rss / 2**20), round(m.private / 2**20)
    print("FILA " + json.dumps(fila, ensure_ascii=False), flush=True)


def main():
    if os.environ.get("_VARIANTE_HIJO"):
        return hijo(os.environ["_VARIANTE_HIJO"])
    argumentos = sys.argv[1:]
    perfil = ""
    if "--perfil" in argumentos:
        i = argumentos.index("--perfil")
        perfil = argumentos[i + 1]
        del argumentos[i:i + 2]
    pedidas = argumentos or list(VARIANTES)
    desconocidas = [v for v in pedidas if v not in VARIANTES]
    if desconocidas:
        raise SystemExit(f"Variantes desconocidas: {desconocidas}. Opciones: {list(VARIANTES)}")
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / f"{time.strftime('%Y-%m-%d_%H%M')}.json"
    if destino.exists():
        raise SystemExit(f"{destino} ya existe: no lo sobrescribo.")
    filas = []
    for nombre in pedidas:
        r = subprocess.run([sys.executable, __file__], env={**os.environ, "_VARIANTE_HIJO": nombre, "_PERFIL_HIJO": perfil,
                                                           "PYTHONIOENCODING": "utf-8"},
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        lineas = [l for l in r.stdout.splitlines() if l.startswith("FILA ")]
        fila = json.loads(lineas[-1][5:]) if lineas else {"variante": nombre, "error": (r.stderr or r.stdout)[-1500:]}
        filas.append(fila)
        print(json.dumps({k: v for k, v in fila.items() if k != "respuesta_pedido"}, ensure_ascii=False), flush=True)
        destino.write_text(json.dumps({"fecha": time.strftime("%Y-%m-%d"), "filas": filas}, ensure_ascii=False,
                                      indent=1), encoding="utf-8")
    print(f"Guardado en {destino}")


if __name__ == "__main__":
    main()
