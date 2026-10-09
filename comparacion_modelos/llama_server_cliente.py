"""Cliente mínimo para el llama-server aislado de las comparaciones de Cacao."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ErrorServidor(RuntimeError):
    pass


class ClienteLlamaServer:
    def __init__(self, url="http://127.0.0.1:18081", modelo="cacao-pruebas", timeout=120):
        self.url = url.rstrip("/")
        self.modelo = modelo
        self.timeout = timeout

    def _solicitar(self, metodo, ruta, datos=None, timeout=None):
        cuerpo = None if datos is None else json.dumps(datos, ensure_ascii=False).encode("utf-8")
        req = Request(
            self.url + ruta,
            data=cuerpo,
            method=metodo,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urlopen(req, timeout=timeout or self.timeout) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            detalle = getattr(exc, "read", lambda: b"")().decode("utf-8", "replace")
            raise ErrorServidor(f"{metodo} {ruta}: {exc}; {detalle}") from exc

    def salud(self):
        return self._solicitar("GET", "/health", timeout=5)

    def modelos(self):
        return self._solicitar("GET", "/v1/models", timeout=5)

    def chat(self, messages, *, response_format=None, **opciones):
        datos = {
            "model": self.modelo,
            "messages": messages,
            # Gemma 4 puede emitir marcadores de canal aun con --reasoning off. El
            # parser del servidor los retira con deepseek y presupuesto cero.
            "reasoning_format": "deepseek",
            "reasoning_budget": 0,
            **opciones,
        }
        if response_format is not None:
            datos["response_format"] = response_format
        return self._solicitar("POST", "/v1/chat/completions", datos)
