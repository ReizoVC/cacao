"""Adaptador de llama-server a la superficie que usa el benchmark de Cacao."""

from __future__ import annotations

import http.client
import json
from types import SimpleNamespace
from urllib.parse import urlsplit


class _Contexto:
    def __init__(self, backend):
        self.backend = backend

    def kv_cache_clear(self):
        self.backend.clear_cache()


class LlamaServerBackend:
    """Implementa el subconjunto de Llama usado por benchmark_gramatica.py."""

    es_servidor = True
    version = "llama.cpp b11429"

    def __init__(self, url: str, modelo: str, timeout=130):
        parsed = urlsplit(url)
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
            raise ValueError("El motor de pruebas debe usar HTTP local en 127.0.0.1.")
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.modelo = modelo
        self.timeout = timeout
        self.seed = 0
        self.interrumpir = lambda: None
        self.modo_gramatica = None
        self.ultimo_muestreador = SimpleNamespace(respaldos=0)
        self._ctx = _Contexto(self)
        self.metadata = {"general.architecture": "servidor"}

    def set_seed(self, seed):
        self.seed = int(seed)

    def reset(self):
        return None

    def clear_cache(self):
        conexion = http.client.HTTPConnection(self.host, self.port, timeout=10)
        conexion.request("POST", "/slots/0?action=erase", body=b"{}",
                         headers={"Content-Type": "application/json"})
        respuesta = conexion.getresponse()
        detalle = respuesta.read().decode("utf-8", "replace")
        conexion.close()
        if respuesta.status != 200:
            raise RuntimeError(f"No se pudo limpiar la caché del slot: HTTP {respuesta.status}: {detalle}")

    def close(self):
        return None

    # benchmark_gramatica envuelve estos métodos, pero el servidor hace el
    # muestreo fuera del proceso Python y por eso nunca los llama.
    def eval(self, _tokens):
        return None

    def sample(self, *_args, **_kwargs):
        raise RuntimeError("El muestreo directo no existe con llama-server.")

    def create_chat_completion(self, **kwargs):
        payload = {
            **kwargs,
            "model": self.modelo,
            "seed": self.seed,
            "stream": True,
            "stream_options": {"include_usage": True},
            # Reutiliza el historial dentro de una tarea; kv_cache_clear borra el
            # slot antes de la tarea siguiente para mantener el protocolo justo.
            "cache_prompt": True,
            # Qwen y Gemma deben devolver la acción, sin una cadena extensa.
            # deepseek hace que el parser retire los marcadores de canal de Gemma.
            "reasoning_format": "deepseek",
            "reasoning_budget": 0,
        }
        conexion = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        cuerpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        conexion.request(
            "POST", "/v1/chat/completions", body=cuerpo,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        respuesta = conexion.getresponse()
        if respuesta.status != 200:
            detalle = respuesta.read().decode("utf-8", "replace")
            conexion.close()
            raise RuntimeError(f"llama-server HTTP {respuesta.status}: {detalle}")

        contenido = []
        uso = None
        creado = None
        identificador = None
        huella = None
        fin = None
        timings = None
        try:
            while True:
                self.interrumpir()
                linea = respuesta.readline()
                if not linea:
                    break
                if not linea.startswith(b"data: "):
                    continue
                dato = linea[6:].strip()
                if dato == b"[DONE]":
                    break
                bloque = json.loads(dato.decode("utf-8"))
                creado = bloque.get("created", creado)
                identificador = bloque.get("id", identificador)
                huella = bloque.get("system_fingerprint", huella)
                uso = bloque.get("usage") or uso
                timings = bloque.get("timings") or timings
                for opcion in bloque.get("choices", []):
                    delta = opcion.get("delta", {})
                    if delta.get("content") is not None:
                        contenido.append(delta["content"])
                    fin = opcion.get("finish_reason") or fin
        finally:
            conexion.close()
        texto = "".join(contenido)
        if not texto:
            raise RuntimeError("llama-server devolvió una respuesta vacía.")
        return {
            "id": identificador,
            "object": "chat.completion",
            "created": creado,
            "model": self.modelo,
            "system_fingerprint": huella,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": texto},
                         "finish_reason": fin or "stop"}],
            "usage": uso or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "timings": timings or {},
        }
