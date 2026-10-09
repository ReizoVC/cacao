"""Evalúa UI-Mate con el adaptador oficial, sin ejecutar las acciones propuestas."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".comparacion-runtime/ui-mate-source/Tencent-UI-Mate-1cb9e1e"
POINT = re.compile(
    r"pyautogui\.(?:click|rightClick|middleClick|doubleClick|tripleClick|moveTo|dragTo)"
    r"\(\s*(\d+)\s*,\s*(\d+)"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18081/v1")
    parser.add_argument("--model", default="cacao-test-ui-mate-q5")
    parser.add_argument("--salida", required=True)
    args = parser.parse_args()

    if not SOURCE.exists():
        raise SystemExit("Falta el código oficial fijado de UI-Mate en .comparacion-runtime.")
    sys.path.insert(0, str(SOURCE))
    from agents.ui_mate_agent import UIMateAgent  # type: ignore

    tareas = json.loads((ROOT / "comparacion_modelos/vision.json").read_text(encoding="utf-8"))
    resultados = []
    for tarea in tareas:
        ruta = ROOT / "comparacion_modelos/capturas" / tarea["imagen"]
        agente = UIMateAgent(
            model=args.model,
            base_url=args.base_url,
            api_key="EMPTY",
            temperature=0.3,
            top_p=0.95,
            max_tokens=1024,
            enable_thinking=True,
            max_retry_times=1,
        )
        respuesta, acciones = agente.predict(
            f"Localiza y haz clic una vez en {tarea['objetivo']}.",
            {"screenshot": ruta.read_bytes()},
        )
        coincidencias = [POINT.search(a) for a in acciones]
        puntos = [(int(m.group(1)), int(m.group(2))) for m in coincidencias if m]
        rect = tarea["rect"]
        acierto = bool(puntos) and rect[0] <= puntos[0][0] <= rect[2] and rect[1] <= puntos[0][1] <= rect[3]
        resultados.append({
            "id": tarea["id"],
            "objetivo": tarea["objetivo"],
            "acciones": acciones,
            "puntos": puntos,
            "acierto": acierto,
            "respuesta": respuesta,
        })

    informe = {
        "modelo": "UI-Mate-9B Q5_K_M",
        "protocolo": "Adaptador oficial Tencent UI-Mate, pensamiento activado, coordenadas relativas 0-999",
        "tareas": resultados,
        "aciertos": sum(r["acierto"] for r in resultados),
        "total": len(resultados),
    }
    Path(args.salida).write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"aciertos": informe["aciertos"], "total": informe["total"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
