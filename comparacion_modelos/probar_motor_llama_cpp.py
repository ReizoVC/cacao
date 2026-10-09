"""Pruebas de compatibilidad del llama-server aislado; no ejecuta herramientas reales."""

from __future__ import annotations

import argparse
import base64
import http.client
import json
from pathlib import Path
import time

from llama_server_cliente import ClienteLlamaServer


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ACCION = {
    "type": "object",
    "properties": {
        "pensamiento": {"type": "string", "maxLength": 120},
        "herramienta": {
            "type": "string",
            "enum": ["volumen", "abrir_app", "listar_apps", "buscar_web", "finalizar"],
        },
        "argumentos": {"type": "object"},
        "mensaje_final": {"type": "string"},
    },
    "required": ["pensamiento", "herramienta", "argumentos"],
}
CASOS = [
    ("pon el volumen al 30", "volumen"),
    ("abre la calculadora", "abrir_app"),
    ("¿qué apps de música tengo?", "listar_apps"),
    ("busca en la web el clima de Lima", "buscar_web"),
    ("hola, ¿cómo estás?", "finalizar"),
]
SISTEMA = """Te llamas Cacao y eres un asistente de escritorio. Responde SOLO con JSON.
Herramientas: volumen cambia el volumen; abrir_app abre una app; listar_apps consulta apps instaladas;
buscar_web busca información en la web; finalizar conversa sin actuar.
Devuelve pensamiento, herramienta y argumentos. No afirmes que una acción ya ocurrió."""


def contenido(respuesta):
    return respuesta["choices"][0]["message"]["content"]


def probar_cancelacion(puerto, modelo):
    cuerpo = json.dumps(
        {
            "model": modelo,
            "messages": [{"role": "user", "content": "Escribe una historia muy larga de 3000 palabras."}],
            "max_tokens": 2048,
            "stream": True,
            "reasoning_format": "deepseek",
            "reasoning_budget": 0,
        }
    ).encode("utf-8")
    conexion = http.client.HTTPConnection("127.0.0.1", puerto, timeout=20)
    conexion.request("POST", "/v1/chat/completions", body=cuerpo, headers={"Content-Type": "application/json"})
    respuesta = conexion.getresponse()
    recibio = False
    limite = time.monotonic() + 15
    while time.monotonic() < limite:
        linea = respuesta.readline()
        if not linea:
            break
        if linea.startswith(b"data: ") and linea.strip() != b"data: [DONE]":
            recibio = True
            break
    conexion.close()  # equivale a cancelar una generación en curso desde Cacao
    return recibio


def probar_vision(cliente):
    esquema = {
        "type": "object",
        "properties": {"box_2d": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0, "maximum": 1000},
            "minItems": 4,
            "maxItems": 4,
        }},
        "required": ["box_2d"],
        "additionalProperties": False,
    }
    salidas = []
    for tarea in json.loads((ROOT / "comparacion_modelos/vision.json").read_text(encoding="utf-8")):
        ruta = ROOT / "comparacion_modelos/capturas" / tarea["imagen"]
        imagen = base64.b64encode(ruta.read_bytes()).decode("ascii")
        prompt = (f"Localiza {tarea['objetivo']}. Devuelve un objeto JSON con "
                  "box_2d: [y_min, x_min, y_max, x_max], la caja del botón. "
                  "Coordenadas normalizadas de 0 a 1000 respecto a toda la imagen. Sin explicación.")
        respuesta = cliente.chat(
            [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + imagen}},
                {"type": "text", "text": prompt},
            ]}],
            response_format={"type": "json_object", "schema": esquema},
            temperature=0.3,
            top_k=64,
            top_p=0.95,
            max_tokens=128,
            seed=11,
        )
        objeto = json.loads(contenido(respuesta))
        ymin, xmin, ymax, xmax = objeto["box_2d"]
        from PIL import Image
        with Image.open(ruta) as original:
            ancho, alto = original.size
        punto = {"x": (xmin + xmax) * ancho / 2000, "y": (ymin + ymax) * alto / 2000}
        x0, y0, x1, y1 = tarea["rect"]
        salidas.append({
            "id": tarea["id"],
            "json_valido": ymin <= ymax and xmin <= xmax,
            "acierto": x0 <= punto["x"] <= x1 and y0 <= punto["y"] <= y1,
            "punto": punto,
        })
    return salidas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--puerto", type=int, default=18081)
    parser.add_argument("--vision", action="store_true")
    parser.add_argument("--salida")
    args = parser.parse_args()
    cliente = ClienteLlamaServer(f"http://127.0.0.1:{args.puerto}", "cacao-pruebas")
    modelos = cliente.modelos()
    identificador = modelos.get("data", modelos.get("models"))[0].get("id", modelos.get("models", [{}])[0].get("name"))
    cliente.modelo = identificador

    informe = {"salud": cliente.salud(), "modelos": modelos, "acciones": []}
    for frase, esperada in CASOS:
        inicio = time.perf_counter()
        respuesta = cliente.chat(
            [{"role": "system", "content": SISTEMA}, {"role": "user", "content": frase}],
            response_format={"type": "json_object", "schema": SCHEMA_ACCION},
            temperature=0.3,
            top_k=64,
            top_p=0.95,
            max_tokens=256,
            seed=11,
        )
        texto = contenido(respuesta)
        accion = json.loads(texto)
        informe["acciones"].append({
            "frase": frase,
            "esperada": esperada,
            "obtenida": accion["herramienta"],
            "json_valido": all(k in accion for k in SCHEMA_ACCION["required"]),
            "correcta": accion["herramienta"] == esperada,
            "segundos": round(time.perf_counter() - inicio, 3),
            "tokens_por_segundo": respuesta.get("timings", {}).get("predicted_per_second"),
        })

    informe["cancelacion_stream"] = probar_cancelacion(args.puerto, identificador)
    time.sleep(0.5)
    inicio = time.perf_counter()
    informe["respuesta_tras_cancelar"] = cliente.salud() == {"status": "ok"}
    informe["salud_tras_cancelar_ms"] = round((time.perf_counter() - inicio) * 1000, 1)
    if args.vision:
        informe["vision"] = probar_vision(cliente)
    informe["ok"] = (
        all(c["json_valido"] and c["correcta"] for c in informe["acciones"])
        and informe["cancelacion_stream"]
        and informe["respuesta_tras_cancelar"]
        and (not args.vision or all(v["json_valido"] for v in informe["vision"]))
    )
    salida = json.dumps(informe, ensure_ascii=False, indent=2)
    if args.salida:
        Path(args.salida).write_text(salida, encoding="utf-8")
    print(salida)
    raise SystemExit(0 if informe["ok"] else 1)


if __name__ == "__main__":
    main()
