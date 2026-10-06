"""
Benchmark del muestreo con gramática: original vs (a) gramática tras top_k vs (b) rechazo estilo llama.cpp.
No toca agente_minimo.py: toma de él (con ast) el esquema, el prompt y el loop, pero con herramientas
SIMULADAS (no cambia el volumen, no abre apps ni el navegador, no enfoca ventanas). listar_ventanas y
listar_controles devuelven siempre las mismas ventanas simuladas (VENTANAS_SIM, con un Bloc de notas), para que los
resultados no dependan de lo que esté abierto; listar_carpeta, leer_archivo y ver_pantalla son las reales. Uso: .venv\\Scripts\\python benchmark_gramatica.py
"""
import ast
import atexit
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz import process, fuzz

import psutil
import win32gui

import herramientas_grupo4 as g4
import herramientas_powershell as ps
import memoria
import sugerencias
import wiki
from emergencia import Detenido, Emergencia
from herramientas_grupo1 import listar_carpeta, leer_archivo, url_busqueda
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
           "terminar", "ACCIONES_A_VERIFICAR", "VERIFICADORAS", "MAX_RECORDATORIOS", "MENSAJE_DETENIDO",
           "MODO_VOZ", "PLANIFICADORES", "TEXTO_EXTERNO", "GUARDAN_SOBRE_REIZO", "SOLO_CONSULTAN", "_tarea",
           "_modos", "_decision", "_politica", "decision_modo", "_guardia", "enviar_modos", "_isla"}
arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
nodos = [n for n in arbol.body
         if (isinstance(n, ast.FunctionDef) and n.name in NOMBRES)
         or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in NOMBRES for t in n.targets))]
CATALOGO = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))
ACTIVAS = next(ast.literal_eval(n.value) for n in arbol.body
               if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "ACTIVAS")
if os.environ.get("SOLO_FASE3"):  # para comparar con el prompt de la Fase 3
    ACTIVAS = {"listar_apps", "abrir_app", "volumen", "finalizar"}
import herramientas_grupo4
import modo_directo
ns = {"json": json, "re": re, "time": time, "herramientas_grupo4": herramientas_grupo4, "modo_directo": modo_directo, "Counter": Counter, "process": process, "fuzz": fuzz, "unicodedata": unicodedata,
      "CATALOGO": CATALOGO, "planificar_powershell": ps.planificar_powershell, "capturar": capturar, "PRESUPUESTOS": PRESUPUESTOS, "CapturaBloqueada": CapturaBloqueada,
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


# ---------- ventanas simuladas ----------
# Siempre la misma lista, con un Bloc de notas: los resultados no dependen de lo que Reizo tenga abierto.
# planificar_cierre (grupo 4) también la ve, y los pid simulados tienen nombre de proceso propio; los controles de
# estas ventanas y la ventana "al frente" tras un clic o atajo también son simulados. ver_pantalla sigue siendo real.
VENTANAS_SIM = [
    {"id_ventana": 9001, "titulo": "Windows PowerShell", "proceso": "WindowsTerminal.exe", "pid": 90001, "enfocada": True},
    {"id_ventana": 9002, "titulo": "Sin título: Bloc de notas", "proceso": "Notepad.exe", "pid": 90002, "enfocada": False},
    {"id_ventana": 9003, "titulo": "Clima en Lima - Google Chrome", "proceso": "chrome.exe", "pid": 90003, "enfocada": False},
    {"id_ventana": 9004, "titulo": "Calculadora", "proceso": "CalculatorApp.exe", "pid": 90004, "enfocada": False},
    {"id_ventana": 9005, "titulo": "Descargas - Explorador de archivos", "proceso": "explorer.exe", "pid": 90005,
     "enfocada": False},
    {"id_ventana": 9006, "titulo": "Spotify Premium", "proceso": "Spotify.exe", "pid": 90006, "enfocada": False}]
_PID_SIM = {v["pid"]: v["proceso"] for v in VENTANAS_SIM}
_ID_SIM = {v["id_ventana"]: v for v in VENTANAS_SIM}
_BOTONES = [("Minimizar", "Button"), ("Maximizar", "Button"), ("Cerrar", "Button")]
_CONTROLES_SIM = {9002: [("Archivo", "MenuItem"), ("Editar", "MenuItem"), ("Ver", "MenuItem"),
                         ("Sin título. No modificado.", "TabItem"), ("Editor de texto", "Document")] + _BOTONES}


def listar_ventanas_sim():
    return [dict(v) for v in VENTANAS_SIM]


def _controles_sim(id_ventana):
    if id_ventana not in _ID_SIM:
        if id_ventana == win32gui.GetForegroundWindow():  # mouse sin id_ventana: la "ventana al frente" simulada
            id_ventana = next(v["id_ventana"] for v in VENTANAS_SIM if v["enfocada"])
        else:
            return None, {"ok": False, "error": "Esa ventana ya no existe; vuelve a usar listar_ventanas."}
    return [{"nombre": n, "tipo": t, "centro": [100 + 40 * i, 120], "rect": [80 + 40 * i, 110, 120 + 40 * i, 130],
             "habilitado": True} for i, (n, t) in enumerate(_CONTROLES_SIM.get(id_ventana, _BOTONES))], None


def listar_controles_sim(id_ventana: int, filtro: str = ""):
    controles, error = _controles_sim(id_ventana)
    if error:
        return error
    if filtro:
        controles = [c for c in controles if filtro.lower() in c["nombre"].lower() or filtro.lower() in c["tipo"].lower()]
    return [{k: v for k, v in c.items() if k != "rect"} for c in controles]


def estado_despues_sim():
    al_frente = next(v for v in VENTANAS_SIM if v["enfocada"])
    return {"ventana_al_frente": al_frente["titulo"], "id_ventana": al_frente["id_ventana"]}


class _ProcesoSim:
    def __init__(self, nombre):
        self._nombre = nombre

    def name(self):
        return self._nombre


class _PsutilSim:
    """psutil para planificar_cierre: los pid simulados tienen nombre; el resto (el propio agente) es real."""

    def __getattr__(self, nombre):
        return getattr(psutil, nombre)

    def Process(self, pid=None):
        return _ProcesoSim(_PID_SIM[pid]) if pid in _PID_SIM else psutil.Process(pid)

    def pid_exists(self, pid):
        return pid in _PID_SIM or psutil.pid_exists(pid)


g4.listar_ventanas = listar_ventanas_sim
g4.psutil = _PsutilSim()
g4._controles = _controles_sim
g4.estado_despues = estado_despues_sim


def enfocar_ventana_sim(id_ventana: int):
    existe = id_ventana in _ID_SIM
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


def ejecutar_powershell_sim(comando: str, motivo: str = ""):
    return _simular("ejecutar_powershell", ps.planificar_powershell(comando, motivo),
                    lambda p: {"ok": True, "codigo_salida": 0, "salida": "(simulado: el comando no se ejecutó)"})


def registro_habitos_sim(accion: str):
    return {"ok": True, "registrando": accion != "pausar"}  # sin tocar PAUSA_HABITOS


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
                         "listar_ventanas": listar_ventanas_sim, "enfocar_ventana": enfocar_ventana_sim,
                         "listar_carpeta": listar_carpeta, "leer_archivo": leer_archivo, "buscar_web": buscar_web_sim,
                         "recordar": memoria.recordar, "consultar_memoria": memoria.consultar_memoria,
                         "ver_pantalla": ns["ver_pantalla"],  # real: solo captura la pantalla
                         "cerrar_app": cerrar_app_sim, "mover_archivo": mover_archivo_sim, "mouse": mouse_sim,
                         "teclado": teclado_sim,
                         "listar_controles": listar_controles_sim,
                         "ejecutar_powershell": ejecutar_powershell_sim,
                         "sugerencias": sugerencias.herramienta, "registro_habitos": registro_habitos_sim}
# la memoria real, pero sobre una base aparte para no tocar memoria.db; empieza vacía
# SIN_REALES=1: también simuladas las que leen el PC (carpetas, archivos, pantalla), para probar sin Reizo delante
# y sin tocar sus archivos. Un sistema de archivos falso fijo; las rutas se validan con las reglas reales.
CARPETAS_SIM = {
    "Downloads": [("Spark.txt", "archivo"), ("informe_ventas.pdf", "archivo"), ("notas_reunion.md", "archivo"),
                  ("README.md", "archivo"), ("instalador.exe", "archivo")],
    "Desktop": [("inventarios", "carpeta"), ("proyecto", "carpeta"), ("notas.txt", "archivo")],
    "Desktop\\inventarios": [("HELP.md", "archivo"), ("datos.csv", "archivo")],
    "Documents": [("Trabajo", "carpeta"), ("cv.docx", "archivo")],
}
TEXTOS_SIM = {"HELP.md": "# Inventarios\nEste proyecto gestiona el inventario de una tienda: altas, bajas y reportes "
                         "en CSV. Ejecuta main.py para empezar."}


def _relativa_sim(ruta):
    p, error = g1.resolver_ruta(ruta)
    if error:
        return None, None, {"ok": False, "bloqueado": True, "error": error}
    return p, str(p.relative_to(Path(os.environ["USERPROFILE"]))), None


def listar_carpeta_sim(ruta: str, patron: str = ""):
    p, rel, error = _relativa_sim(ruta)
    if error:
        return error
    if rel not in CARPETAS_SIM:
        return {"ok": False, "error": f"No existe la carpeta {p}"}
    import fnmatch
    return [{"nombre": n, "tipo": t, "tamano_bytes": None if t == "carpeta" else 1024, "modificado": "2026-10-01 10:00"}
            for n, t in CARPETAS_SIM[rel] if not patron or fnmatch.fnmatch(n.lower(), patron.lower())]


def leer_archivo_sim(ruta: str, max_caracteres: int = 20000):
    p, rel, error = _relativa_sim(ruta)
    if error:
        return error
    carpeta, _, nombre = rel.rpartition("\\")
    if (nombre, "archivo") not in CARPETAS_SIM.get(carpeta, []):
        return {"ok": False, "error": f"No existe el archivo {p}"}
    if g1.es_sensible(p):
        return {"ok": False, "bloqueado": True, "error": "Ese archivo puede tener contraseñas o claves; no lo leo por seguridad."}
    return {"ok": True, "contenido": TEXTOS_SIM.get(nombre, f"Contenido de prueba de {nombre}."), "truncado": False}


def mover_archivo_sin_reales(origen: str, destino: str):
    p, rel, error = _relativa_sim(origen)
    if error:
        return _simular("mover_archivo", (None, error), None)
    carpeta, _, nombre = rel.rpartition("\\")
    if g1.es_sensible(p):
        return _simular("mover_archivo", (None, {"ok": False, "bloqueado": True,
                                                 "error": "Ese archivo puede tener contraseñas o claves; no lo muevo."}), None)
    if not any(n == nombre for n, _ in CARPETAS_SIM.get(carpeta, [])):
        return _simular("mover_archivo", (None, {"ok": False, "error": f"No existe {p}"}), None)
    return _simular("mover_archivo", ((p, destino), None), lambda plan: {"ok": True, "ruta_final": str(destino)})


def ver_pantalla_sim(region: str = "ventana_activa", presupuesto_tokens: int = 560, cuadricula: bool = False):
    return {"ok": True, "ancho": 1920, "alto": 1080, "presupuesto_tokens": presupuesto_tokens,
            "cuadricula": bool(cuadricula), "nota": "(simulado: sin imagen) Se ve PowerShell al frente."}


if os.environ.get("SIN_REALES"):
    import herramientas_grupo1 as g1
    ns["IMPLEMENTACIONES"].update({"listar_carpeta": listar_carpeta_sim, "leer_archivo": leer_archivo_sim,
                                   "mover_archivo": mover_archivo_sin_reales, "ver_pantalla": ver_pantalla_sim})
else:
    import herramientas_grupo1 as g1
memoria.RUTA = BASE / "memoria_prueba.db"
memoria.RUTA.unlink(missing_ok=True)
ns["memoria"] = memoria
# Fase 6: una wiki de prueba (vault temporal, con el índice inicial en el prompt), que se borra al salir
wiki.VAULT = BASE / "memoria_prueba"
wiki.obsidian_abierto = lambda: False
if wiki.ruta("perfil").exists() is False:
    wiki.asegurar_vault()
ns["wiki"] = wiki


def _borrar_vault_prueba():
    import shutil
    import stat

    def quitar_solo_lectura(func, ruta, _):
        os.chmod(ruta, stat.S_IWRITE)
        func(ruta)

    shutil.rmtree(wiki.VAULT, onerror=quitar_solo_lectura)


atexit.register(_borrar_vault_prueba)
# respuesta a toda confirmación: CONFIRMAR=s deja avanzar las simuladas del grupo 4 (no hacen nada real)
ns["confirmar"] = lambda *_a, **_k: os.environ.get("CONFIRMAR", "n") == "s"  # sin hooks ni isla
ns["notificar"] = lambda *_a, **_k: None

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
