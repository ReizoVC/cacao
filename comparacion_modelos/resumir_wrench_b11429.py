"""Resume Wrench 9B Q4 con el protocolo protegido de la ronda 3."""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "comparacion_modelos"
sys.path[:0] = [str(ROOT), str(HERE)]

from integracion import complete_round2
from resumir_ronda3 import claims_without_evidence, distinct_actions


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    run = read(HERE / "datos/wrench_b11429/ronda3/qwen_wrench_q4.json")
    tests = read(ROOT / "pruebas.json")["pruebas"]
    by_id = {test["id"]: test for test in tests}
    rows = run["cases"]
    assert run["complete"] and len(rows) == 195 and len(run["conversation"]) == 10
    assert {(row["id"], row["semilla"]) for row in rows} == {
        (case, seed) for case in range(1, 66) for seed in (11, 22, 33)
    }
    reference = read(HERE / "datos/ronda3/qwen_q5.json")
    assert run["prompt_sha256"] == reference["prompt_sha256"]
    assert run["integration"]["schema_sha256"] == reference["integration"]["schema_sha256"]

    first_latency = sorted(row["first_action_s"] for row in rows if row["first_action_s"] is not None)
    outputs = [output for row in rows for output in row["outputs"]]
    predicted = sum(output.get("timings", {}).get("predicted_n", 0) for output in outputs)
    decode_s = sum(output.get("timings", {}).get("predicted_ms", 0) for output in outputs) / 1000
    false = [(row["id"], row["semilla"], claims_without_evidence(row)) for row in rows
             if claims_without_evidence(row)]
    different = [(row["id"], row["semilla"], distinct_actions(row, by_id[row["id"]]))
                 for row in rows if distinct_actions(row, by_id[row["id"]])]
    incomplete = [(row["id"], row["semilla"]) for row in rows if not complete_round2(row)]
    summary = {
        "complete": sum(complete_round2(row) for row in rows),
        "blank": sum(not str(row.get("respuesta") or "").strip() for row in rows),
        "json": sum(row["json_schema_ok"] for row in rows),
        "first": sum(row["first_strict"] for row in rows),
        "false_confirmation": len(false),
        "distinct": len(different),
        "corrections": sum(row.get("proteccion", {}).get("correcciones", 0) for row in rows),
        "two_failure_stops": sum("Probé dos alternativas" in str(row.get("respuesta")) for row in rows),
        "median_first": statistics.median(first_latency),
        "p95_first": first_latency[round((len(first_latency) - 1) * .95)],
        "mean_task": statistics.mean(row["wall_s"] for row in rows),
        "tps": predicted / decode_s,
    }
    metrics = [{
        "model": "qwen_wrench_q4", "engine": "llama.cpp b11429",
        "id": row["id"], "seed": row["semilla"], "complete": complete_round2(row),
        "blank": not bool(str(row.get("respuesta") or "").strip()),
        "json": row["json_schema_ok"], "first": row["first_strict"],
        "tools": row["herramientas"], "protection": row.get("proteccion", {}),
        "first_action_s": row["first_action_s"], "wall_s": row["wall_s"],
        "tokens": row.get("tokens", 0),
    } for row in rows]
    result = {
        "model": "ClankLabs/Wrench-9B-Q4_K_M-GGUF",
        "base_model": "Qwen/Qwen3.5-9B",
        "source_revision": "6d4f489d2a1ebb0f41f6cc8779a07df5917e5ddc",
        "model_sha256": "e21435c7150794cccddf2ab0737fb5509eba681e7c9a89b1dc9e51948c4f78b7",
        "model_bytes": 5629108640,
        "engine": "llama.cpp b11429",
        "summary": summary,
        "previous_qwen_q5_llama_cpp_python_0_3_36": read(HERE / "resumen_ronda3.json")["summaries"]["qwen_q5"],
        "gemma_q5_llama_b11429": read(HERE / "resumen_gemma_q5_llama_b11429.json")["summary"],
        "gpu_peak_mib": run["gpu_peak_mib"],
        "gpu_min_free_mib": run["gpu_min_free_mib"],
        "prompt_sha256": run["prompt_sha256"],
        "schema_sha256": run["integration"]["schema_sha256"],
        "incomplete": incomplete,
        "false_confirmations": false,
        "distinct_actions": different,
        "comparison_limit": "Wrench solo está publicado en Q4_K_M; la referencia Qwen usa UD-Q5_K_XL y el motor Python anterior.",
    }
    (HERE / "metricas_wrench_b11429.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "resumen_wrench_b11429.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
