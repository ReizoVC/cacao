"""
Recalifica, sin modelo, una 65 × 3 de probar_swa_cache.py hecha antes de que el banco anotara las herramientas del
camino rápido (benchmark_gramatica solo anotaba las que elegía el modelo, así que esos casos salían con usadas = [] y
contaban como fallidos aunque la acción se hizo y se verificó).

Para cada fila con usadas == [] cuya respuesta es uno de los textos fijos del camino rápido, pone la herramienta que
da camino_rapido.reconocer(frase) y vuelve a aplicar el criterio de evaluar_pruebas.py (primer_paso_ok y 'requiere',
copiados con ast para no cargar el modelo). No toca los datos crudos: escribe recalificado_<nombre>.json.
Uso: .venv\\Scripts\\python comparacion_modelos\\recalificar_camino_rapido.py <nombre> [<nombre>...]
     (p. ej. gemma65x3rapido_C qwen65x3rapido_A, en comparacion_modelos/datos/swa_cache/)
"""
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATOS = ROOT / "comparacion_modelos" / "datos" / "swa_cache"
sys.path.insert(0, str(ROOT))
import camino_rapido  # noqa: E402

TEXTOS = ("Listo, puse el volumen al ", "Listo, silencié el sonido.", "Listo, volví a activar el sonido",
          "El volumen está al ", "Listo, abrí ", "Listo, pausé el registro", "Listo, reanudé el registro")
arbol = ast.parse((ROOT / "evaluar_pruebas.py").read_text(encoding="utf-8"))
ns = {}
exec(compile(ast.Module(body=[n for n in arbol.body if (isinstance(n, ast.FunctionDef) and n.name == "primer_paso_ok")
                              or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "VERIFICACION"
                                                                    for t in n.targets))],
                        type_ignores=[]), "evaluar_pruebas.py", "exec"), ns)
PRUEBAS = {p["id"]: p for p in json.loads((ROOT / "pruebas.json").read_text(encoding="utf-8"))["pruebas"]}


def recalificar(nombre):
    datos = json.loads((DATOS / f"{nombre}.json").read_text(encoding="utf-8"))
    cambiadas, por_semilla = [], {}
    for fila in datos["filas"]:
        usadas = fila["usadas"]
        if not usadas and str(fila.get("respuesta") or "").startswith(TEXTOS):
            rapido = camino_rapido.reconocer(fila["frase"], lambda nombre_app: True)
            if rapido:
                usadas = [rapido[0]]
                prueba = PRUEBAS[int(fila["id"])]
                esperado = prueba["esperado"] if isinstance(prueba["esperado"], list) else [prueba["esperado"]]
                ok = (ns["primer_paso_ok"](esperado, usadas) and all(h in usadas for h in prueba.get("requiere", []))
                      and fila["error"] is None)
                cambiadas.append({"id": fila["id"], "semilla": fila["semilla"], "herramienta": rapido[0],
                                  "tarea_ok_antes": fila["tarea_ok"], "tarea_ok": ok})
                fila = {**fila, "usadas": usadas, "tarea_ok": ok}
        s = str(fila["semilla"])
        por_semilla[s] = por_semilla.get(s, 0) + (str(fila["tarea_ok"]) == "True")
    resultado = {"nombre": nombre, "por_semilla": por_semilla, "total": sum(por_semilla.values()),
                 "filas_recalificadas": len(cambiadas), "recalificadas_ok": sum(c["tarea_ok"] for c in cambiadas),
                 "detalle": cambiadas}
    (DATOS / f"recalificado_{nombre}.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1),
                                                       encoding="utf-8")
    print(json.dumps({k: v for k, v in resultado.items() if k != "detalle"}, ensure_ascii=False))


if __name__ == "__main__":
    for nombre in sys.argv[1:]:
        recalificar(nombre)
