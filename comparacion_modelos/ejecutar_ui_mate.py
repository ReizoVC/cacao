"""Añade UI-Mate al ejecutor congelado sin modificar la ronda 3 histórica."""

from pathlib import Path

import ejecutar


ejecutar.MODELS["ui_mate_q5"] = (
    Path(__file__).resolve().parents[1] / "modelos/comparacion/UI-Mate-9B.Q5_K_M.gguf"
)

if __name__ == "__main__":
    ejecutar.main()
