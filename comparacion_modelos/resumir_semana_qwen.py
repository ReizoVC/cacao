"""
Cifras agregadas de la semana de uso real de Qwen 9B (desde el 2026-10-11, cerebro/decisiones/qwen-como-cerebro.md).
Correr SOLO con permiso del usuario: exige --con-permiso.

Lee únicamente registro_cacao.log y registro_cacao.1.log (raíz del repositorio): la salida de voz.py que guarda
iniciar_cacao.py. No lee voz_registro/, memoria.db, la wiki ni ninguna otra ruta de CLAUDE.md. Solo cuenta líneas con
marcadores fijos del agente; no imprime ni guarda el texto de ningún pedido, respuesta o pensamiento.

Cuenta, en las sesiones que empiezan («=== fecha Cacao arranca ===») a partir de --desde:
  - pedidos: líneas «Tú (isla):» o «Tú (voz…)»;
  - finalizaciones rechazadas por el ejecutor: «[evidencia]» (aparte, las de mensaje_final descartado);
  - bloqueos: «[bloqueado] tarea terminada por el ejecutor»;
  - cerrar_app: intentos del modelo («[cerrar_app]»), bloqueados por el freno («[cerrar] cerrar_app bloqueado»),
    negados por el usuario («[rechazado]» justo después de un intento de cerrar_app) y el resto, que pasó a
    ejecutarse (aproximado: incluye los que fallaron al planificar); además «[forzar]» ignorados;
  - «[alternativas] dos caminos fallaron»;
  - límite de pasos: respuestas «Cacao: Me pasé del límite de pasos».
Uso: .venv\\Scripts\\python comparacion_modelos\\resumir_semana_qwen.py --con-permiso [--desde "AAAA-MM-DD HH:MM"]
     [--guardar]   (--guardar: comparacion_modelos/datos/semana_qwen_<fecha>.json, ignorado por Git; no sobrescribe)
"""
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTROS = [ROOT / "registro_cacao.1.log", ROOT / "registro_cacao.log"]  # el rotado primero: orden cronológico
DESDE = "2026-10-11 16:21"  # 5e9eee0: Qwen activo
ARRANQUE = re.compile(r"^=== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) Cacao arranca ===$")
HERRAMIENTA = re.compile(r"^  \[([a-z_]+)\] ")


def contar(lineas, desde):
    c = {"sesiones": 0, "pedidos": 0, "finalizaciones_rechazadas": 0, "mensaje_final_descartado": 0, "bloqueos": 0,
         "cerrar_app_intentos": 0, "cerrar_app_bloqueados_freno": 0, "cerrar_app_negados_usuario": 0,
         "forzar_ignorado": 0, "dos_alternativas_fallidas": 0, "limite_de_pasos": 0}
    dentro, ultima = False, None
    for linea in lineas:
        linea = linea.rstrip("\r\n")
        m = ARRANQUE.match(linea)
        if m:
            dentro = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S") >= desde
            c["sesiones"] += dentro
            ultima = None
            continue
        if not dentro:
            continue
        if linea.startswith("Tú (isla):") or linea.startswith("Tú (voz"):
            c["pedidos"] += 1
        elif linea.startswith("Cacao: Me pasé del límite de pasos"):
            c["limite_de_pasos"] += 1
        elif linea.startswith("  [evidencia] mensaje_final descartado"):
            c["mensaje_final_descartado"] += 1
        elif linea.startswith("  [evidencia] "):
            c["finalizaciones_rechazadas"] += 1
        elif linea.startswith("  [bloqueado] tarea terminada por el ejecutor"):
            c["bloqueos"] += 1
        elif linea.startswith("  [cerrar] cerrar_app bloqueado"):
            c["cerrar_app_bloqueados_freno"] += 1
        elif linea.startswith("  [forzar] "):
            c["forzar_ignorado"] += 1
        elif linea.startswith("  [alternativas] dos caminos fallaron"):
            c["dos_alternativas_fallidas"] += 1
        elif linea.startswith("  [rechazado] "):
            c["cerrar_app_negados_usuario"] += ultima == "cerrar_app"
        m = HERRAMIENTA.match(linea)
        if m and m.group(1) not in ("evidencia", "bloqueado", "cerrar", "forzar", "alternativas", "rechazado"):
            ultima = m.group(1)
            c["cerrar_app_intentos"] += ultima == "cerrar_app"
    c["cerrar_app_ejecutados_aprox"] = (c["cerrar_app_intentos"] - c["cerrar_app_bloqueados_freno"]
                                        - c["cerrar_app_negados_usuario"])
    return c


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--con-permiso", action="store_true", help="el usuario autorizó leer registro_cacao.log")
    parser.add_argument("--desde", default=DESDE)
    parser.add_argument("--guardar", action="store_true")
    args = parser.parse_args()
    if not args.con_permiso:
        raise SystemExit("Lee el registro del agente: córrelo solo con permiso del usuario (--con-permiso).")
    desde = datetime.strptime(args.desde, "%Y-%m-%d %H:%M")
    lineas = []
    for ruta in REGISTROS:
        if ruta.exists():
            lineas += ruta.read_text(encoding="utf-8", errors="replace").splitlines()
    cifras = {"desde": args.desde, "registros": [r.name for r in REGISTROS if r.exists()], **contar(lineas, desde)}
    print(json.dumps(cifras, ensure_ascii=False, indent=1))
    if args.guardar:
        destino = ROOT / "comparacion_modelos" / "datos" / f"semana_qwen_{time.strftime('%Y-%m-%d')}.json"
        if destino.exists():
            raise SystemExit(f"{destino} ya existe: no lo sobrescribo.")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(cifras, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
