"""
Carga config.json y crea el modelo. Lo usan agente_minimo.py y los scripts de prueba, para que todos
carguen el mismo archivo con los mismos parámetros.
"""
import ctypes
import faulthandler
import json
import sys
import time
from pathlib import Path

import llama_cpp

from muestreo_gramatica import LlamaRapida

BASE = Path(__file__).parent
TIPOS_KV = {"f16": llama_cpp.GGML_TYPE_F16, "q8_0": llama_cpp.GGML_TYPE_Q8_0, "q4_0": llama_cpp.GGML_TYPE_Q4_0}

# ---------- errores de llama.cpp / CUDA ----------
# ggml usa ERROR=4 y CONT=5 (continuación), pero llama-cpp-python 0.3.36 (_logger.py) aún asume ERROR=3 y trata el 4
# como depuración: con verbose=False los errores (p. ej. el motivo de un "CUDA error") no se veían. Este callback
# los muestra y los guarda en errores_llama.log; faulthandler añade la pila de Python si llama.cpp aborta.
GGML_ERROR, GGML_CONT = 4, 5
REGISTRO_ERRORES = BASE / "errores_llama.log"
_ultimo_nivel = 0
_archivo_errores = open(REGISTRO_ERRORES, "a", encoding="utf-8", buffering=1)
faulthandler.enable(file=_archivo_errores)


@llama_cpp.llama_log_callback
def _log_llama(nivel, texto, _datos):
    global _ultimo_nivel
    if nivel != GGML_CONT:
        _ultimo_nivel = nivel
    if _ultimo_nivel == GGML_ERROR:
        t = texto.decode("utf-8", "replace")
        print(t, end="", file=sys.stderr, flush=True)
        _archivo_errores.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {' '.join(sys.argv)}: {t}")


llama_cpp.llama_log_set(_log_llama, ctypes.c_void_p(0))


def cargar_config():
    config = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    for clave in ("modelo", "mmproj"):
        if config.get(clave):
            ruta = Path(config[clave])
            config[clave] = ruta if ruta.is_absolute() else BASE / ruta
            if not config[clave].is_file():
                raise FileNotFoundError(f"config.json: no existe {clave} = {config[clave]}")
    return config


def crear_llm(config, esperar_juego=False, comprobar_juego=True):
    # con un juego activo no se carga nada en la GPU: las pruebas terminan con un aviso, el agente espera.
    # comprobar_juego=False: la recarga del modo juego, que ya decidió con su detector (y con "ya terminé")
    if comprobar_juego:
        from guardia_juego import exigir_gpu_libre
        exigir_gpu_libre("Gemma", esperar=esperar_juego)
    # caché KV cuantizada para ahorrar VRAM; llama.cpp exige flash attention para cuantizar la caché V.
    # LlamaRapida aplica la gramática después de top_k (~26 ms/token en vez de ~125; ver resultados_latencia.md).
    # OJO: sobrescribe Llama._init_sampler, método interno de llama-cpp-python 0.3.36; puede romperse al
    # actualizar. Si falla, pon "modo_gramatica": null en config.json para volver al muestreo original.
    return LlamaRapida(model_path=str(config["modelo"]), n_gpu_layers=config["n_gpu_layers"],
                       n_ctx=config["n_ctx"], flash_attn=config["flash_attn"],
                       type_k=TIPOS_KV[config["type_k"]], type_v=TIPOS_KV[config["type_v"]],
                       use_mmap=config.get("use_mmap", True), verbose=False,
                       modo_gramatica=config["modo_gramatica"])
