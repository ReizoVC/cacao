"""
Fase 4: pasa las frases de pruebas.json por el agente (loop completo de agente_minimo.py con herramientas
SIMULADAS de benchmark_gramatica.py) y reporta el % de acierto de herramienta.
Uso: .venv\\Scripts\\python evaluar_pruebas.py [semilla ...]   (por defecto 11 22 33)
Variables de entorno opcionales: TIPOS=directa,ambigua,... (solo esos tipos), SALIDA=archivo.json y
SOLO_FASE3=1 (solo las 4 herramientas de la Fase 3, para comparar).
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import benchmark_gramatica as b  # carga el modelo con LlamaRapida y las herramientas simuladas

BASE = Path(__file__).parent
PRUEBAS = json.loads((BASE / "pruebas.json").read_text(encoding="utf-8"))["pruebas"]
if os.environ.get("TIPOS"):
    PRUEBAS = [p for p in PRUEBAS if p["tipo"] in os.environ["TIPOS"].split(",")]
SEMILLAS = [int(s) for s in sys.argv[1:]] or [11, 22, 33]
MODO = "topk"  # el mismo muestreo que usa agente_minimo.py


# pasos de verificación razonables antes de actuar: mirar la pantalla o las ventanas antes de un atajo o un
# clic, y consultar la memoria antes de abrir algo que puede ser un alias
VERIFICACION = {"teclado": {"ver_pantalla", "listar_ventanas", "enfocar_ventana"},
                "mouse": {"ver_pantalla", "listar_ventanas"},
                "abrir_app": {"consultar_memoria", "listar_apps"},
                "listar_apps": {"consultar_memoria"}}


def primer_paso_ok(esperado, usadas, estricto=False):
    if not usadas:
        return False
    if usadas[0] in esperado:
        return True
    # buscar el nombre exacto con listar_apps antes de abrir también cuenta como acierto
    if "abrir_app" in esperado and usadas[:2] == ["listar_apps", "abrir_app"]:
        return True
    if estricto:
        return False
    # se saltan los pasos de verificación que tienen sentido antes de alguna de las herramientas esperadas
    permitidos = set().union(*(VERIFICACION.get(e, set()) for e in esperado))
    resto = list(usadas)
    while resto and resto[0] in permitidos and resto[0] not in esperado:
        resto.pop(0)
    return bool(resto) and resto[0] in esperado


def evaluar(prueba, semilla):
    r = b.correr(MODO, semilla, prueba["frase"])
    esperado = prueba["esperado"] if isinstance(prueba["esperado"], list) else [prueba["esperado"]]
    usadas = r["herramientas"]
    primera_ok = primer_paso_ok(esperado, usadas)
    primera_estricta = primer_paso_ok(esperado, usadas, estricto=True)
    requiere_ok = all(h in usadas for h in prueba.get("requiere", []))
    return {**prueba, "semilla": semilla, "usadas": usadas, "argumentos": r["argumentos"],
            "primera_ok": primera_ok, "primera_estricta": primera_estricta, "tarea_ok": primera_ok and requiere_ok and r["error"] is None,
            "json_ok": r["json_ok"], "error": r["error"], "respuesta": r["respuesta"],
            "tiempo": r.get("t_total", 0), "tokens": r.get("tokens", 0), "planes": r.get("planes", [])}


def pct(lista, clave):
    return 100 * sum(x[clave] for x in lista) / len(lista) if lista else 0


if __name__ == "__main__":
    b.correr(MODO, 1, "hola")  # calentamiento
    resultados = []
    for semilla in SEMILLAS:
        for p in PRUEBAS:
            r = evaluar(p, semilla)
            resultados.append(r)
            marca = "OK " if r["primera_ok"] else "MAL"
            print(f"{marca} s{semilla} #{p['id']:2} {p['frase'][:40]:40} {r['usadas']} "
                  f"{'' if r['tarea_ok'] else '(tarea incompleta)'} {r['error'] or ''}", flush=True)
    (BASE / os.environ.get("SALIDA", "resultados_pruebas.json")).write_text(
        json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nAcierto de herramienta (primer paso): {pct(resultados, 'primera_ok'):.1f}%  "
          f"(estricto, sin pasos de verificación: {pct(resultados, 'primera_estricta'):.1f}%)")
    print(f"Tarea completa (primer paso + herramientas requeridas, sin error): {pct(resultados, 'tarea_ok'):.1f}%")
    print(f"JSON válido: {pct(resultados, 'json_ok'):.1f}%")
    por_tipo = defaultdict(list)
    for r in resultados:
        por_tipo[r["tipo"]].append(r)
    for tipo, rs in por_tipo.items():
        print(f"  {tipo:13} herramienta {pct(rs, 'primera_ok'):5.1f}%  tarea {pct(rs, 'tarea_ok'):5.1f}%  (n={len(rs)})")
