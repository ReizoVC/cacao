"""
Carga config.json y crea el modelo. Lo usan agente_minimo.py y los scripts de prueba, para que todos
carguen el mismo archivo con los mismos parámetros.
"""
import json
from pathlib import Path

import llama_cpp

from muestreo_gramatica import LlamaRapida

BASE = Path(__file__).parent
TIPOS_KV = {"f16": llama_cpp.GGML_TYPE_F16, "q8_0": llama_cpp.GGML_TYPE_Q8_0, "q4_0": llama_cpp.GGML_TYPE_Q4_0}


def cargar_config():
    config = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    for clave in ("modelo", "mmproj"):
        if config.get(clave):
            ruta = Path(config[clave])
            config[clave] = ruta if ruta.is_absolute() else BASE / ruta
            if not config[clave].is_file():
                raise FileNotFoundError(f"config.json: no existe {clave} = {config[clave]}")
    return config


def crear_llm(config):
    # caché KV cuantizada para ahorrar VRAM; llama.cpp exige flash attention para cuantizar la caché V.
    # LlamaRapida aplica la gramática después de top_k (~26 ms/token en vez de ~125; ver resultados_latencia.md).
    # OJO: sobrescribe Llama._init_sampler, método interno de llama-cpp-python 0.3.36; puede romperse al
    # actualizar. Si falla, pon "modo_gramatica": null en config.json para volver al muestreo original.
    return LlamaRapida(model_path=str(config["modelo"]), n_gpu_layers=config["n_gpu_layers"],
                       n_ctx=config["n_ctx"], flash_attn=config["flash_attn"],
                       type_k=TIPOS_KV[config["type_k"]], type_v=TIPOS_KV[config["type_v"]],
                       use_mmap=config.get("use_mmap", True), verbose=False,
                       modo_gramatica=config["modo_gramatica"])
