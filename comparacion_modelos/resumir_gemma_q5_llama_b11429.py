"""Resume la referencia completa de Gemma Q5 ejecutada con llama-server b11429."""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "comparacion_modelos"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from integracion import complete_round2
from resumir_ronda3 import claims_without_evidence, distinct_actions


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    nuevo = read(HERE / "datos/llama_cpp_b11429/ronda3/gemma_q5.json")
    anterior = read(HERE / "resumen_ronda3.json")["summaries"]["gemma_q5"]
    casos = read(ROOT / "pruebas.json")["pruebas"]
    por_id = {caso["id"]: caso for caso in casos}
    filas = nuevo["cases"]
    assert nuevo["complete"] and len(filas) == 195 and len(nuevo["conversation"]) == 10
    assert {(r["id"], r["semilla"]) for r in filas} == {
        (i, semilla) for i in range(1, 66) for semilla in (11, 22, 33)
    }
    referencia = read(HERE / "datos/ronda3/gemma_q5.json")
    assert nuevo["prompt_sha256"] == referencia["prompt_sha256"]
    assert nuevo["integration"]["schema_sha256"] == referencia["integration"]["schema_sha256"]

    latencias = sorted(r["first_action_s"] for r in filas if r["first_action_s"] is not None)
    salidas = [salida for r in filas for salida in r["outputs"]]
    predichos = sum(o.get("timings", {}).get("predicted_n", 0) for o in salidas)
    decode_s = sum(o.get("timings", {}).get("predicted_ms", 0) for o in salidas) / 1000
    prompt_n = sum(o.get("timings", {}).get("prompt_n", 0) for o in salidas)
    prompt_s = sum(o.get("timings", {}).get("prompt_ms", 0) for o in salidas) / 1000
    falsos = [(r["id"], r["semilla"], claims_without_evidence(r)) for r in filas
              if claims_without_evidence(r)]
    distintos = [(r["id"], r["semilla"], distinct_actions(r, por_id[r["id"]])) for r in filas
                  if distinct_actions(r, por_id[r["id"]])]
    resumen = {
        "complete": sum(complete_round2(r) for r in filas),
        "blank": sum(not str(r.get("respuesta") or "").strip() for r in filas),
        "json": sum(r["json_schema_ok"] for r in filas),
        "first": sum(r["first_strict"] for r in filas),
        "false_confirmation": len(falsos),
        "distinct": len(distintos),
        "corrections": sum(r.get("proteccion", {}).get("correcciones", 0) for r in filas),
        "median_first": statistics.median(latencias),
        "p95_first": latencias[round((len(latencias) - 1) * .95)],
        "mean_task": statistics.mean(r["wall_s"] for r in filas),
        "tps": predichos / decode_s,
        "prompt_tps": prompt_n / prompt_s,
    }
    metricas = [{
        "model": "gemma_q5", "engine": "llama.cpp b11429", "id": r["id"], "seed": r["semilla"],
        "complete": complete_round2(r), "blank": not bool(str(r.get("respuesta") or "").strip()),
        "json": r["json_schema_ok"], "first": r["first_strict"], "tools": r["herramientas"],
        "protection": r.get("proteccion", {}), "first_action_s": r["first_action_s"],
        "wall_s": r["wall_s"], "tokens": r.get("tokens", 0),
    } for r in filas]
    resultado = {
        "engine": "llama.cpp b11429",
        "summary": resumen,
        "previous_llama_cpp_python_0_3_36": anterior,
        "delta": {
            "complete": resumen["complete"] - anterior["complete"],
            "first": resumen["first"] - anterior["first"],
            "median_first_s": resumen["median_first"] - anterior["median_first"],
            "mean_task_s": resumen["mean_task"] - anterior["mean_task"],
            "tps": resumen["tps"] - anterior["tps"],
            "gpu_peak_mib": nuevo["gpu_peak_mib"] - referencia["gpu_peak_mib"],
        },
        "gpu_peak_mib": nuevo["gpu_peak_mib"],
        "gpu_min_free_mib": nuevo["gpu_min_free_mib"],
        "prompt_sha256": nuevo["prompt_sha256"],
        "schema_sha256": nuevo["integration"]["schema_sha256"],
        "false_confirmations": falsos,
        "distinct_actions": distintos,
    }
    (HERE / "metricas_gemma_q5_llama_b11429.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "resumen_gemma_q5_llama_b11429.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False))


if __name__ == "__main__":
    main()
