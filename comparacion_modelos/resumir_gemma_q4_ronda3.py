"""Resume Gemma Q4 con el protocolo congelado de la ronda 3."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "comparacion_modelos"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from integracion import complete_round2
from resumir_ronda3 import claims_without_evidence, distinct_actions, stats


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    q4 = read(HERE / "datos/ronda3/gemma_q4.json")
    q5 = read(HERE / "datos/ronda3/gemma_q5.json")
    cases = read(ROOT / "pruebas.json")["pruebas"]
    by_id = {case["id"]: case for case in cases}
    assert q4["complete"] and len(q4["cases"]) == 195 and len(q4["conversation"]) == 10
    assert {(r["id"], r["semilla"]) for r in q4["cases"]} == {
        (i, seed) for i in range(1, 66) for seed in (11, 22, 33)
    }
    assert q4["prompt_sha256"] == q5["prompt_sha256"]
    assert q4["integration"]["schema_sha256"] == q5["integration"]["schema_sha256"]

    summary = stats(q4, cases)
    metrics = []
    audit = []
    for r in q4["cases"]:
        different = distinct_actions(r, by_id[r["id"]])
        false = claims_without_evidence(r)
        row = {
            "model": "gemma_q4", "id": r["id"], "seed": r["semilla"],
            "complete": complete_round2(r), "blank": not bool(str(r.get("respuesta") or "").strip()),
            "json": r["json_schema_ok"], "first": r["first_strict"], "tools": r["herramientas"],
            "protection": r.get("proteccion", {}), "first_action_s": r["first_action_s"],
            "wall_s": r["wall_s"], "tokens": r.get("tokens", 0),
            "t_decode": r.get("t_decode", 0), "t_sample": r.get("t_sample", 0),
        }
        metrics.append(row)
        if different or false or r.get("proteccion", {}).get("correcciones"):
            audit.append({
                "id": r["id"], "seed": r["semilla"], "complete": row["complete"],
                "distinct_actions": different, "false_confirmation": false,
                "corrections": r.get("proteccion", {}).get("correcciones", 0),
                "tools": r["herramientas"], "response": r.get("respuesta"),
            })

    result = {
        "summary": summary,
        "gpu_peak_mib": q4["gpu_peak_mib"], "gpu_min_free_mib": q4["gpu_min_free_mib"],
        "disk_bytes": (ROOT / "modelos/comparacion/gemma-4-12b-it-UD-Q4_K_XL.gguf").stat().st_size,
        "prompt_sha256": q4["prompt_sha256"],
        "schema_sha256": q4["integration"]["schema_sha256"],
        "audit": audit,
    }
    (HERE / "metricas_gemma_q4_ronda3.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "resumen_gemma_q4_ronda3.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
