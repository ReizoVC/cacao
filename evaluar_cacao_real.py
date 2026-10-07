"""
Mide un detector de "Cacao" con las grabaciones reales de Reizo (voz_pruebas/cacao_real, de grabar_cacao.py).
Para cada toma: probabilidad máxima del detector y si detecta con un umbral dado (paciencia del modelo), con 1 s de
silencio antes, como en la escucha real. Positivos: todas las categorías salvo 'parecida' (negativos).

Uso: .venv\\Scripts\\python evaluar_cacao_real.py [modelo.npz] [--archivos a,b,c] [--json salida.json]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import palabra_activacion as pa
from entrenar_cacao import leer_wav

BASE = Path(__file__).parent
CARPETA = BASE / "voz_pruebas" / "cacao_real"
UMBRALES = (0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 0.95)


def probabilidades(detector, audio):
    """Probabilidad por trama (80 ms), con 1 s de silencio antes y 0,5 s después, como en la escucha real."""
    x = np.concatenate([np.zeros(pa.TASA, np.int16), audio, np.zeros(pa.TASA // 2, np.int16)])
    detector.reiniciar()
    ps = []
    for i in range(0, len(x) - pa.TROZO + 1, pa.TROZO):
        detector.procesar(x[i:i + pa.TROZO])
        ps.append(detector.ultima)
    return np.array(ps)


def detecta(ps, umbral, paciencia):
    racha = 0
    for p in ps:
        racha = racha + 1 if p >= umbral else 0
        if racha >= paciencia:
            return True
    return False


def evaluar(ruta_modelo, archivos=None):
    modelo = pa.ModeloCacao(ruta_modelo)
    indice = json.loads((CARPETA / "indice.json").read_text(encoding="utf-8"))
    if archivos is not None:
        indice = [x for x in indice if x["archivo"] in archivos]
    detector = pa.Detector(modelo, umbral=2.0)
    tomas = [(x["archivo"], x["categoria"], probabilidades(detector, leer_wav(CARPETA / x["archivo"]))) for x in indice]
    r = {"modelo": Path(ruta_modelo).name, "umbral_del_modelo": modelo.umbral, "paciencia": modelo.paciencia,
         "maximos": {a: round(float(ps.max()), 3) for a, _, ps in tomas}, "por_umbral": {}}
    for umbral in UMBRALES:
        por_cat = defaultdict(lambda: [0, 0])
        for _, cat, ps in tomas:
            por_cat[cat][0] += detecta(ps, umbral, modelo.paciencia)
            por_cat[cat][1] += 1
        pos = [v for c, v in por_cat.items() if c != "parecida"]
        r["por_umbral"][umbral] = {
            "positivos": f"{sum(a for a, _ in pos)}/{sum(t for _, t in pos)}",
            "parecidas_activadas": f"{por_cat['parecida'][0]}/{por_cat['parecida'][1]}",
            "por_categoria": {c: f"{a}/{t}" for c, (a, t) in sorted(por_cat.items())}}
    return r


if __name__ == "__main__":
    args, saltar = [], False
    for a in sys.argv[1:]:
        if saltar:
            saltar = False
        elif a.startswith("--"):
            saltar = True  # --archivos y --json llevan un valor
        else:
            args.append(a)
    ruta = args[0] if args else str(pa.RUTA_MODELO)
    archivos = set(sys.argv[sys.argv.index("--archivos") + 1].split(",")) if "--archivos" in sys.argv else None
    r = evaluar(ruta, archivos)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(r, ensure_ascii=False, indent=1),
                                                                encoding="utf-8")
