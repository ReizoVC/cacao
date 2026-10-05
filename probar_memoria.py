"""
Prueba de la memoria (Fase 5, grupo 3) con herramientas simuladas y una base aparte (memoria_prueba.db):
  control:  sesión sin memorias  -> "abre el editor"
  sesión 1: "cuando digo el editor me refiero a VS Code" -> debe llamar a recordar
  sesión 2: historial nuevo, prompt reconstruido con las memorias -> "abre el editor" debe abrir Visual Studio Code
Uso: .venv\\Scripts\\python probar_memoria.py
"""
import json
from pathlib import Path

import benchmark_gramatica as b
import memoria

SEMILLAS = [11, 22, 33]
FRASE_GUARDAR = "cuando digo el editor me refiero a VS Code"
FRASE_USAR = "abre el editor"
APP_ESPERADA = "Visual Studio Code"


def apps_abiertas(r):
    # la abrir_app simulada es determinista: se repite con los mismos argumentos para saber qué abrió
    abiertas = []
    for nombre, args in zip(r["herramientas"], r["argumentos"]):
        if nombre == "abrir_app":
            res = b.abrir_app_sim(**args)
            if res.get("ok"):
                abiertas.append(res["app_abierta"])
    return abiertas


def resumen(r):
    return {"herramientas": r["herramientas"], "argumentos": r["argumentos"], "respuesta": r["respuesta"],
            "apps_abiertas": apps_abiertas(r), "json_ok": r["json_ok"], "error": r["error"]}


if __name__ == "__main__":
    b.correr("topk", 1, "hola")
    filas = []
    for s in SEMILLAS:
        memoria.RUTA.unlink(missing_ok=True)
        control = resumen(b.correr("topk", s, FRASE_USAR))
        sesion1 = resumen(b.correr("topk", s, FRASE_GUARDAR))
        guardadas = memoria.consultar_memoria("")
        en_prompt = memoria.memorias_para_prompt()
        sesion2 = resumen(b.correr("topk", s, FRASE_USAR))
        fila = {"semilla": s, "control": control, "sesion1": sesion1, "guardadas": guardadas,
                "en_prompt": en_prompt, "sesion2": sesion2,
                "guardo": "recordar" in sesion1["herramientas"] and bool(en_prompt),
                "uso": APP_ESPERADA in sesion2["apps_abiertas"]}
        filas.append(fila)
        print(f"s{s} control: {control['herramientas']} abrió {control['apps_abiertas']} -> {control['respuesta']!r}")
        print(f"s{s} sesión 1: {sesion1['herramientas']} {sesion1['argumentos']} -> {sesion1['respuesta']!r}")
        print(f"s{s} en el prompt: {en_prompt}")
        print(f"s{s} sesión 2: {sesion2['herramientas']} {sesion2['argumentos']} abrió {sesion2['apps_abiertas']} "
              f"-> {sesion2['respuesta']!r}", flush=True)
    memoria.RUTA.unlink(missing_ok=True)
    Path(__file__).with_name("resultados_memoria.json").write_text(
        json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nguardó y pasó al prompt: {sum(f['guardo'] for f in filas)}/{len(filas)}; "
          f"usó la memoria (abrió {APP_ESPERADA}): {sum(f['uso'] for f in filas)}/{len(filas)}")
