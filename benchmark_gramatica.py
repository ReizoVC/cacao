"""
Benchmark del muestreo con gramática: original vs (a) gramática tras top_k vs (b) rechazo estilo llama.cpp.
No toca agente_minimo.py: toma de él (con ast) el esquema, el prompt y el loop, pero con herramientas
SIMULADAS (no cambia el volumen, no abre apps ni el navegador, no enfoca ventanas); listar_ventanas,
listar_carpeta y leer_archivo son las reales porque solo leen. Uso: .venv\\Scripts\\python benchmark_gramatica.py
"""
import ast
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz import process, fuzz

import herramientas_grupo4 as g4
import memoria
from emergencia import Detenido, Emergencia
from herramientas_grupo1 import listar_ventanas, listar_carpeta, leer_archivo, url_busqueda
from modelo import cargar_config, crear_llm
from vision import CapturaBloqueada, ManejadorVision, PRESUPUESTOS, capturar

BASE = Path(__file__).parent
MODOS = sys.argv[1:] or ["original", "topk", "rechazo"]
SEMILLAS = [11, 22, 33]
# las 5 frases de prueba de la Fase 3 de guia_instalacion_agente.md
FRASES = [
    "sube el volumen un poco",
    "pon el volumen al 30",
    "abre la calculadora",
    "¿qué apps de música tengo?",
    "hola, ¿cómo estás?",
]

# ---------- piezas de agente_minimo.py, sin ejecutar su código de arranque ----------
NOMBRES = {"CATEGORIAS", "LIMITE_RESULTADO", "normalizar", "listar_apps", "ESQUEMA_ACCION",
           "prompt_sistema", "pedir_accion", "ejecutar", "resumir_resultado", "compactar_historial",
           "atender", "rellenar_marcadores", "CON_MARCADORES", "elegir_app",
           "coincide_por_siglas", "nivel_app", "_sin_articulos", "es_generico", "opciones_genericas",
           "preparar_apertura", "cubre_bien", "ARTICULOS", "GENERICOS", "APPS_SENSIBLES", "ver_pantalla",
           "terminar", "ACCIONES_A_VERIFICAR", "VERIFICADORAS", "MAX_RECORDATORIOS", "MENSAJE_DETENIDO"}
arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
nodos = [n for n in arbol.body
         if (isinstance(n, ast.FunctionDef) and n.name in NOMBRES)
         or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in NOMBRES for t in n.targets))]
CATALOGO = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))
ACTIVAS = next(ast.literal_eval(n.value) for n in arbol.body
               if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "ACTIVAS")
if os.environ.get("SOLO_FASE3"):  # para comparar con el prompt de la Fase 3
    ACTIVAS = {"listar_apps", "abrir_app", "volumen", "finalizar"}
ns = {"json": json, "re": re, "time": time, "Counter": Counter, "process": process, "fuzz": fuzz, "unicodedata": unicodedata,
      "CATALOGO": CATALOGO, "capturar": capturar, "PRESUPUESTOS": PRESUPUESTOS, "CapturaBloqueada": CapturaBloqueada,
      "_presupuesto_imagen": 280, "_ultima_captura": None,
      "HERRAMIENTAS": {h["nombre"]: h for h in CATALOGO["herramientas"] if h["nombre"] in ACTIVAS},
      "MAX_PASOS": CATALOGO["limites"]["max_pasos_por_tarea"],
      "_categorias": json.loads((BASE / "apps_categorias.json").read_text(encoding="utf-8"))}
exec(compile(ast.Module(body=nodos, type_ignores=[]), "agente_minimo.py", "exec"), ns)

# ---------- herramientas simuladas ----------
estado = {"volumen": 50, "silenciado": False}


def abrir_app_sim(nombre: str, argumentos: str = ""):
    # misma elección y confirmación que la real (preparar_apertura), pero sin abrir nada
    apps = [{"nombre": d["nombre"], "id": i} for i, d in ns["_categorias"].items()]
    app, error = ns["preparar_apertura"](nombre, apps)
    return error or {"ok": True, "app_abierta": app["nombre"]}


def enfocar_ventana_sim(id_ventana: int):
    existe = any(v["id_ventana"] == id_ventana for v in listar_ventanas())
    return {"ok": True} if existe else {"ok": False, "error": "Esa ventana ya no existe; vuelve a usar listar_ventanas."}


# grupo 4: misma validación que las reales (planificar_*), sin efectos. Cada plan se guarda para revisarlo.
planes = []


def _simular(nombre, plan_error, si_ok):
    plan, error = plan_error
    planes.append({"herramienta": nombre, "plan": plan, "error": error})
    return error or si_ok(plan)


def cerrar_app_sim(proceso: str = None, pid: int = None, forzar: bool = False, id_ventana: int = None):
    return _simular("cerrar_app", g4.planificar_cierre(proceso, pid, id_ventana),
                    lambda p: {"ok": True, "cerrada": True, "requirio_forzar": bool(forzar), "proceso": p["proceso"]})


def mover_archivo_sim(origen: str, destino: str):
    return _simular("mover_archivo", g4.planificar_movimiento(origen, destino),
                    lambda p: {"ok": True, "ruta_final": str(p[1])})


def mouse_sim(accion: str, x: int = None, y: int = None, cantidad: int = None, control: str = None,
              id_ventana: int = None):
    return _simular("mouse", g4.planificar_mouse(accion, x, y, cantidad, control=control, id_ventana=id_ventana),
                    lambda p: {"ok": True, "pantalla": p["pantalla"], "control": p.get("control"),
                               "despues": g4.estado_despues(),
                               "nota": "Comprueba con listar_controles o ver_pantalla que pasó lo que esperabas "
                                       "antes de confirmarlo."})


def teclado_sim(accion: str, texto: str = None, teclas: list = None):
    return _simular("teclado", g4.planificar_teclado(accion, texto, teclas),
                    lambda p: {"ok": True} if accion == "escribir" else
                    {"ok": True, "despues": g4.estado_despues(),
                     "nota": "Comprueba con listar_controles o ver_pantalla que pasó lo que esperabas antes de "
                             "confirmarlo."})


def buscar_web_sim(consulta: str):
    return {"ok": True, "url": url_busqueda(consulta)}  # no abre el navegador


def volumen_sim(accion: str, cantidad: int | None = None):
    v = estado["volumen"]
    if accion in ("subir", "bajar"):
        d = cantidad if cantidad is not None else 10
        estado["volumen"] = max(0, min(100, v + (d if accion == "subir" else -d)))
    elif accion == "fijar" and cantidad is not None:
        estado["volumen"] = max(0, min(100, cantidad))
    elif accion in ("silenciar", "activar"):
        estado["silenciado"] = accion == "silenciar"
    return {"ok": True, "volumen_actual": estado["volumen"], "silenciado": estado["silenciado"]}


ns["IMPLEMENTACIONES"] = {"listar_apps": ns["listar_apps"], "abrir_app": abrir_app_sim, "volumen": volumen_sim,
                         "listar_ventanas": listar_ventanas, "enfocar_ventana": enfocar_ventana_sim,
                         "listar_carpeta": listar_carpeta, "leer_archivo": leer_archivo, "buscar_web": buscar_web_sim,
                         "recordar": memoria.recordar, "consultar_memoria": memoria.consultar_memoria,
                         "ver_pantalla": ns["ver_pantalla"],  # real: solo captura la pantalla
                         "cerrar_app": cerrar_app_sim, "mover_archivo": mover_archivo_sim, "mouse": mouse_sim,
                         "teclado": teclado_sim,
                         "listar_controles": g4.listar_controles}  # real: solo lee la interfaz
# la memoria real, pero sobre una base aparte para no tocar memoria.db; empieza vacía
memoria.RUTA = BASE / "memoria_prueba.db"
memoria.RUTA.unlink(missing_ok=True)
ns["memoria"] = memoria
# respuesta a toda confirmación: CONFIRMAR=s deja avanzar las simuladas del grupo 4 (no hacen nada real)
ns["input"] = lambda *_: os.environ.get("CONFIRMAR", "n")

# ---------- modelo con medición ----------
CONFIG = cargar_config()
llm = crear_llm({**CONFIG, "modo_gramatica": None})  # cada corrida elige el modo con llm.modo_gramatica
med = {}
_eval, _sample = llm.eval, llm.sample


def eval_medido(tokens):
    t = time.perf_counter()
    _eval(tokens)
    clave = "t_prompt" if len(tokens) > 1 else "t_decode"
    med[clave] = med.get(clave, 0) + time.perf_counter() - t


def sample_medido(*a, **k):
    t = time.perf_counter()
    tok = _sample(*a, **k)
    med["t_sample"] = med.get("t_sample", 0) + time.perf_counter() - t
    med["n_sample"] = med.get("n_sample", 0) + 1
    return tok


llm.eval, llm.sample = eval_medido, sample_medido
# atajo de emergencia real (registrado en Windows) y conectado igual que en agente_minimo.py
emergencia = Emergencia(CATALOGO["limites"]["atajo_emergencia"])
emergencia.iniciar()
llm.interrumpir = emergencia.comprobar
g4.comprobar_emergencia = emergencia.comprobar
ns["emergencia"], ns["Detenido"] = emergencia, Detenido


class Proxy:
    def __getattr__(self, n):
        return getattr(llm, n)

    def create_chat_completion(self, **kw):
        t = time.perf_counter()
        r = llm.create_chat_completion(**kw)
        med["t_total"] = med.get("t_total", 0) + time.perf_counter() - t
        med["tokens"] = med.get("tokens", 0) + r["usage"]["completion_tokens"]
        med["llamadas"] = med.get("llamadas", 0) + 1
        m = llm.ultimo_muestreador
        if m is not None:
            med["respaldos"] = med.get("respaldos", 0) + m.respaldos
        med.setdefault("salidas", []).append(r["choices"][0]["message"]["content"])
        return r


class VisionMedida:
    """El handler multimodal necesita el Llama real (cambia n_tokens); se mide igual que Proxy."""

    def __init__(self, real):
        self.real = real

    def fijar_presupuesto(self, presupuesto):
        self.real.fijar_presupuesto(presupuesto)

    def __call__(self, **kw):
        t = time.perf_counter()
        r = self.real(**{**kw, "llama": llm})
        med["t_total"] = med.get("t_total", 0) + time.perf_counter() - t
        med["tokens"] = med.get("tokens", 0) + r["usage"]["completion_tokens"]
        med["llamadas"] = med.get("llamadas", 0) + 1
        med["llamadas_vision"] = med.get("llamadas_vision", 0) + 1
        med.setdefault("salidas", []).append(r["choices"][0]["message"]["content"])
        return r


ns["llm"] = Proxy()
ns["vision"] = VisionMedida(ManejadorVision(CONFIG["mmproj"])) if CONFIG.get("mmproj") else None
_pedir = ns["pedir_accion"]
herramientas_usadas = []


def pedir_medido(historial):
    accion = _pedir(historial)
    herramientas_usadas.append((accion.get("herramienta"), accion.get("argumentos")))
    return accion


ns["pedir_accion"] = pedir_medido


def json_valido(texto):
    try:
        d = json.loads(texto)
    except json.JSONDecodeError:
        return False
    esq = ns["ESQUEMA_ACCION"]
    return (all(k in d for k in esq["required"])
            and d["herramienta"] in esq["properties"]["herramienta"]["enum"]
            and isinstance(d["argumentos"], dict)
            and len(d["pensamiento"]) <= 120)


def correr(modo, semilla, frase):
    llm.modo_gramatica = None if modo == "original" else modo
    llm.set_seed(semilla)
    med.clear()
    herramientas_usadas.clear()
    planes.clear()
    estado.update(volumen=50, silenciado=False)
    historial = [{"role": "system", "content": ns["prompt_sistema"]()}]
    error = None
    try:
        respuesta = ns["atender"](frase, historial)
    except Exception as e:  # JSON inválido u otro fallo
        respuesta, error = None, f"{type(e).__name__}: {e}"
    return {"modo": modo, "semilla": semilla, "frase": frase, "respuesta": respuesta, "error": error,
            "herramientas": [h for h, _ in herramientas_usadas],
            "argumentos": [a for _, a in herramientas_usadas],
            "planes": [{**x, "plan": str(x["plan"]) if x["plan"] is not None else None} for x in planes],
            "json_ok": error is None and all(json_valido(s) for s in med.get("salidas", [])),
            **{k: v for k, v in med.items() if k != "salidas"}}


if __name__ == "__main__":
    # calentamiento: carga los kernels de CUDA y el prefijo del prompt de sistema en la caché KV
    correr(MODOS[0], 1, "hola")
    resultados = []
    for semilla in SEMILLAS:
        for modo in MODOS:
            for frase in FRASES:
                r = correr(modo, semilla, frase)
                resultados.append(r)
                print(f"{modo:8} s{semilla} {frase[:28]:28} {r['tokens'] if 'tokens' in r else '-':>4} tok "
                      f"{r.get('t_total', 0):6.2f}s  {r['herramientas']}  json_ok={r['json_ok']} "
                      f"resp={r.get('respaldos', '-')} {r['error'] or ''}", flush=True)
    (BASE / f"resultados_benchmark_{'_'.join(MODOS)}.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
