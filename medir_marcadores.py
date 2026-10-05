"""
Mide en cuántas de 10 frases de volumen el modelo usa un marcador ({volumen_actual}, ...) en mensaje_final.
Herramientas SIMULADAS. Uso: .venv\\Scripts\\python medir_marcadores.py [etiqueta]
"""
import json
import re
import sys
from pathlib import Path

import benchmark_gramatica as b

FRASES = [
    "sube el volumen un poco",
    "baja el volumen",
    "pon el volumen al 30",
    "sube el volumen 20",
    "baja un poco el volumen",
    "pon el volumen al máximo",
    "silencia el volumen",
    "quita el silencio",
    "¿a cuánto está el volumen?",
    "bájale 15 al volumen",
]
SEMILLAS = [11, 22, 33]

if __name__ == "__main__":
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "actual"
    b.correr("topk", 1, "hola")
    filas = []
    for s in SEMILLAS:
        for f in FRASES:
            r = b.correr("topk", s, f)
            primera = json.loads(b.med["salidas"][0]) if b.med.get("salidas") else {}
            mf = primera.get("mensaje_final") or ""
            filas.append({"semilla": s, "frase": f, "herramientas": r["herramientas"],
                          "argumentos": r["argumentos"], "mensaje_final": mf,
                          "usa_marcador": bool(re.search(r"\{\w+\}", mf)), "respuesta": r["respuesta"],
                          "volumen_final": b.estado["volumen"], "json_ok": r["json_ok"], "error": r["error"]})
            print(f"s{s} {f[:28]:28} marcador={filas[-1]['usa_marcador']!s:5} mf={mf!r} -> {r['respuesta']!r}",
                  flush=True)
    Path(__file__).with_name(f"resultados_marcadores_{etiqueta}.json").write_text(
        json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
    for s in SEMILLAS:
        n = sum(x["usa_marcador"] for x in filas if x["semilla"] == s)
        print(f"semilla {s}: {n}/10 con marcador")
    print(f"total: {sum(x['usa_marcador'] for x in filas)}/{len(filas)}")
