"""
Pruebas sin modelo del contrato de la ronda 2 por perfil (contrato_ronda2.py, "contrato_ronda2" en config.json):
  a) perfil qwen9b: prompt, HERRAMIENTAS y ESQUEMA_ACCION idénticos a los de comparacion_modelos/integracion.adjust(ns,
     'combined') aplicado a los globales de agente_minimo con el perfil gemma (hashes, como adjust);
  b) perfil gemma: prompt y esquema idénticos byte a byte a los de antes del cambio (hashes guardados abajo);
  c) perfil qwen9b: una acción con mensaje_final no valida el esquema, ni finalizar sin mensaje.
Cada perfil se carga en su propio proceso, sin tocar config.json. La memoria y la wiki van a rutas temporales vacías
(sin datos personales en el prompt). No carga ningún modelo.
Uso: .venv\\Scripts\\python probar_contrato_ronda2.py
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).parent
# perfil gemma antes de este cambio (d95855d), con memoria y wiki vacías
ANTES_GEMMA = {"prompt": "8a3bea036dd7664b459d2e350b26ae55b551edf0d38f38b030b9588eb47783c8",
               "prompt_voz": "37c39a391f44bbc570025019cc4c0c24d0c440087d38b9b1fcd64a9adbbcd73c",
               "herramientas": "4cd7a441923753272374c46545a5450da9a3d9b36a1234403b14855b54b29026",
               "esquema": "90971f7d1c74532fe59b28f99bc9f0e9cb0bfda05ca4b000b2cdc4ba4924c1b1"}
fallos, ejecutadas = [], []


def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    print(("OK " if condicion else "MAL ") + nombre + (f": {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


def sha(texto):
    return hashlib.sha256(texto.encode()).hexdigest()


def hijo(perfil, con_adjust):
    sys.path.insert(0, str(BASE))
    import modelo
    _aplicar = modelo.aplicar_perfil
    modelo.aplicar_perfil = lambda config: _aplicar({**config, "modelo_activo": perfil})
    import agente_minimo as a
    temporal = Path(tempfile.mkdtemp(prefix="cacao_contrato_"))
    a.memoria.RUTA, a.wiki.VAULT = temporal / "memoria.db", temporal / "wiki"
    if con_adjust:  # la referencia: el adjust del banco sobre los globales de producción
        sys.path.insert(0, str(BASE / "comparacion_modelos"))
        from integracion import adjust
        adjust(vars(a), "combined")
    print("HUELLAS " + json.dumps({
        "contrato": bool(a.CONFIG.get("contrato_ronda2")),
        "prompt": sha(a.prompt_sistema()), "prompt_voz": sha(a.prompt_sistema(voz=True)),
        "herramientas": sha(json.dumps(a.HERRAMIENTAS, sort_keys=True, ensure_ascii=False)),
        "esquema": sha(json.dumps(a.ESQUEMA_ACCION, sort_keys=True)), "esquema_json": a.ESQUEMA_ACCION}))


def huellas(perfil, con_adjust=False):
    r = subprocess.run([sys.executable, __file__], capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "_PERFIL": perfil, "_ADJUST": "1" if con_adjust else "",
                            "PYTHONIOENCODING": "utf-8"})
    linea = next((l for l in r.stdout.splitlines() if l.startswith("HUELLAS ")), None)
    if linea is None:
        raise SystemExit(f"{perfil}: {r.stderr[-2000:]}")
    return json.loads(linea[8:])


def valida(instancia, esquema):
    """Validador mínimo del subconjunto de JSON Schema que usan ESQUEMA_ACCION y el contrato (oneOf, type object y
    string, properties, required, enum, additionalProperties false, minLength, maxLength). .venv no tiene jsonschema."""
    if "oneOf" in esquema:
        return sum(valida(instancia, e) for e in esquema["oneOf"]) == 1
    tipo = esquema.get("type")
    if tipo == "object":
        if not isinstance(instancia, dict) or any(k not in instancia for k in esquema.get("required", [])):
            return False
        props = esquema.get("properties", {})
        if esquema.get("additionalProperties") is False and set(instancia) - set(props):
            return False
        return all(valida(instancia[k], props[k]) for k in instancia if k in props)
    if tipo == "string":
        return (isinstance(instancia, str) and len(instancia) >= esquema.get("minLength", 0)
                and len(instancia) <= esquema.get("maxLength", 10**9)
                and ("enum" not in esquema or instancia in esquema["enum"]))
    if tipo == "boolean":
        return isinstance(instancia, bool)
    if tipo == "integer":
        return isinstance(instancia, int) and not isinstance(instancia, bool)
    return True


def main():
    gemma, qwen, referencia = huellas("gemma"), huellas("qwen9b"), huellas("gemma", con_adjust=True)
    claves = ("prompt", "prompt_voz", "herramientas", "esquema")
    print("-- a) qwen9b = integracion.adjust(ns, 'combined') sobre producción")
    ok("qwen9b activa el contrato y gemma no", qwen["contrato"] and not gemma["contrato"])
    for k in claves:
        ok(f"a) {k} de qwen9b idéntico al del adjust del banco", qwen[k] == referencia[k], (qwen[k][:12], referencia[k][:12]))
    print("-- b) gemma idéntico a antes del cambio")
    for k in claves:
        ok(f"b) {k} de gemma sin cambios", gemma[k] == ANTES_GEMMA[k], (gemma[k][:12], ANTES_GEMMA[k][:12]))
    print("-- c) esquema de qwen9b")
    esquema = qwen["esquema_json"]
    accion = {"pensamiento": "Subo el volumen.", "herramienta": "volumen", "argumentos": {"accion": "subir"}}
    final = {"pensamiento": "Respondo.", "herramienta": "finalizar", "argumentos": {"mensaje": "Listo.", "exito": True}}
    ok("c) acción normal válida", valida(accion, esquema))
    ok("c) finalizar con mensaje válido", valida(final, esquema))
    ok("c) acción con mensaje_final NO valida", not valida({**accion, "mensaje_final": "Listo."}, esquema))
    ok("c) finalizar con mensaje_final NO valida", not valida({**final, "mensaje_final": "Listo."}, esquema))
    ok("c) finalizar sin mensaje NO valida", not valida({**final, "argumentos": {"exito": True}}, esquema))
    ok("c) finalizar con mensaje vacío NO valida", not valida({**final, "argumentos": {"mensaje": ""}}, esquema))
    ok("c) con gemma, mensaje_final sigue siendo válido", valida({**accion, "mensaje_final": "Listo."},
                                                                 gemma["esquema_json"]))
    print(f"{len(ejecutadas) - len(fallos)}/{len(ejecutadas)} OK")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    if os.environ.get("_PERFIL"):
        hijo(os.environ["_PERFIL"], bool(os.environ.get("_ADJUST")))
    else:
        main()
