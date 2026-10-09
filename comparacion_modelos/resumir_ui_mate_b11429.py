"""Resume UI-Mate 9B Q5 con el protocolo protegido y su visión nativa."""

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
    run = read(HERE / "datos/ui_mate_b11429/ronda3/ui_mate_q5.json")
    vision = read(HERE / "ui_mate_q5_vision_nativa.json")
    tests = read(ROOT / "pruebas.json")["pruebas"]
    by_id = {test["id"]: test for test in tests}
    rows = run["cases"]
    assert run["complete"] and len(rows) == 195 and len(run["conversation"]) == 10
    assert {(row["id"], row["semilla"]) for row in rows} == {
        (case, seed) for case in range(1, 66) for seed in (11, 22, 33)
    }
    reference = read(HERE / "datos/llama_cpp_b11429/ronda3/gemma_q5.json")
    assert run["prompt_sha256"] == reference["prompt_sha256"]
    assert run["integration"]["schema_sha256"] == reference["integration"]["schema_sha256"]

    first_latency = sorted(row["first_action_s"] for row in rows if row["first_action_s"] is not None)
    outputs = [output for row in rows for output in row["outputs"]]
    predicted = sum(output.get("timings", {}).get("predicted_n", 0) for output in outputs)
    decode_s = sum(output.get("timings", {}).get("predicted_ms", 0) for output in outputs) / 1000
    automatic_false = [(row["id"], row["semilla"], claims_without_evidence(row)) for row in rows
                       if claims_without_evidence(row)]
    # La protección actual registra "teclado" como verificado tras escribir, pero
    # eso no acredita un efecto posterior distinto como guardar el documento.
    manual_false = [(58, 22, ["Afirmó que el texto se guardó; solo se verificó escribirlo."])]
    false = automatic_false + manual_false
    different = [(row["id"], row["semilla"], distinct_actions(row, by_id[row["id"]]))
                 for row in rows if distinct_actions(row, by_id[row["id"]])]
    incomplete = [(row["id"], row["semilla"]) for row in rows if not complete_round2(row)]
    conversation_actions = [
        {"id": i, "tools": row["herramientas"]}
        for i, row in enumerate(run["conversation"], 1)
        if any(tool != "finalizar" for tool in row["herramientas"])
    ]
    summary = {
        "complete": sum(complete_round2(row) for row in rows),
        "blank": sum(not str(row.get("respuesta") or "").strip() for row in rows),
        "json": sum(row["json_schema_ok"] for row in rows),
        "first": sum(row["first_strict"] for row in rows),
        "false_confirmation": len(false),
        "automatic_false_confirmation": len(automatic_false),
        "distinct": len(different),
        "corrections": sum(row.get("proteccion", {}).get("correcciones", 0) for row in rows),
        "median_first": statistics.median(first_latency),
        "p95_first": first_latency[round((len(first_latency) - 1) * .95)],
        "mean_task": statistics.mean(row["wall_s"] for row in rows),
        "tps": predicted / decode_s,
        "vision_native": f"{vision['aciertos']}/{vision['total']}",
        "conversation_with_actions": len(conversation_actions),
    }
    metrics = [{
        "model": "ui_mate_q5", "engine": "llama.cpp b11429",
        "id": row["id"], "seed": row["semilla"], "complete": complete_round2(row),
        "blank": not bool(str(row.get("respuesta") or "").strip()),
        "json": row["json_schema_ok"], "first": row["first_strict"],
        "tools": row["herramientas"], "protection": row.get("proteccion", {}),
        "first_action_s": row["first_action_s"], "wall_s": row["wall_s"],
        "tokens": row.get("tokens", 0),
    } for row in rows]
    result = {
        "model": "tencent/UI-Mate-9B Q5_K_M GGUF",
        "base_model": "Qwen/Qwen3.5-9B",
        "source_revision": "d66487fa0deb83cfbae88fc143d7d76987d3437a",
        "official_harness_revision": "1cb9e1e44ce856e23b593992b02efbd489943fcb",
        "model_sha256": "8aaef02bce71b9056df67986b67964d10396278689dbcd807b1cd204df4959e7",
        "model_bytes": 6467970336,
        "mmproj_sha256": "5a8380c4637dddceed9dbc28fffcdfa8601909c0ece9fe218fbd6888ec5d2c16",
        "mmproj_bytes": 918166016,
        "engine": "llama.cpp b11429",
        "summary": summary,
        "gemma_q5_llama_b11429": read(HERE / "resumen_gemma_q5_llama_b11429.json")["summary"],
        "gpu_peak_mib": run["gpu_peak_mib"],
        "gpu_min_free_mib": run["gpu_min_free_mib"],
        "prompt_sha256": run["prompt_sha256"],
        "schema_sha256": run["integration"]["schema_sha256"],
        "incomplete": incomplete,
        "false_confirmations": false,
        "distinct_actions": different,
        "conversation_actions": conversation_actions,
        "vision": vision,
    }
    (HERE / "metricas_ui_mate_b11429.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "resumen_ui_mate_b11429.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
