"""
Compara caso a caso dos corridas de probar_swa_cache.py (datos/swa_cache/<nombre>.json): mismas herramientas, mismos
argumentos y misma respuesta. Solo compara los casos (id, semilla) que están en las dos.
Uso: .venv\\Scripts\\python comparacion_modelos\\comparar_corridas.py <nombre_a> <nombre_b> [--guardar destino.json]
"""
import json
import sys
from pathlib import Path

DATOS = Path(__file__).resolve().parent / "datos" / "swa_cache"


def cargar(nombre):
    return {(int(f["id"]), int(f["semilla"])): f for f in
            json.loads((DATOS / f"{nombre}.json").read_text(encoding="utf-8"))["filas"]}


def comparar(a, b):
    fa, fb = cargar(a), cargar(b)
    comunes = sorted(set(fa) & set(fb))
    diferencias = []
    for k in comunes:
        x, y = fa[k], fb[k]
        campos = [c for c in ("usadas", "argumentos", "respuesta") if x.get(c) != y.get(c)]
        if campos:
            diferencias.append({"id": k[0], "semilla": k[1], "campos": campos, "frase": x["frase"],
                                a: {"usadas": x["usadas"], "tarea_ok": x["tarea_ok"], "respuesta": str(x["respuesta"])[:160]},
                                b: {"usadas": y["usadas"], "tarea_ok": y["tarea_ok"], "respuesta": str(y["respuesta"])[:160]}})
    return {"a": a, "b": b, "casos_comunes": len(comunes), "identicos": len(comunes) - len(diferencias),
            "diferencias": diferencias}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    r = comparar(sys.argv[1], sys.argv[2])
    print(f"{r['a']} frente a {r['b']}: {r['identicos']}/{r['casos_comunes']} casos idénticos")
    for d in r["diferencias"]:
        print(json.dumps(d, ensure_ascii=False)[:700])
    if "--guardar" in sys.argv:
        Path(sys.argv[sys.argv.index("--guardar") + 1]).write_text(json.dumps(r, ensure_ascii=False, indent=1),
                                                                   encoding="utf-8")
