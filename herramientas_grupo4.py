"""
Fase 5, grupo 4: cerrar_app, mover_archivo, mouse y teclado. Todas tienen permiso 'confirmar' en
herramientas.json (el ejecutor pide un sí antes de llamarlas).

Cada herramienta se divide en planificar_* (valida y calcula qué haría, sin efectos) y la función real que ejecuta
ese plan. Las pruebas usan solo los planes. Los rechazos de seguridad devuelven "bloqueado": True; el ejecutor
corta la tarea al verlos.
"""
import ctypes
import json
import os
import shutil
import time
from datetime import datetime
from ctypes import wintypes
from pathlib import Path

from protecciones_ejecucion import parece_atajo

import psutil
import win32api
import win32clipboard
import win32con
import win32gui
import win32process

import vision
from herramientas_grupo1 import (ALIAS, CARPETAS_PERMITIDAS, PROCESOS_OCULTOS, _normalizar, es_de_la_isla,
                                 es_sensible, es_titulo_sensible, listar_ventanas, resolver_ruta,
                                 titulo_para_el_modelo)

user32 = ctypes.windll.user32
shcore = ctypes.windll.shcore
# píxeles físicos para todo (capturas, UI Automation y cursor), sin que Windows escale coordenadas;
# si ya se fijó (mss o pywinauto lo hacen), la llamada falla sin efecto
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
except (AttributeError, OSError):
    pass

# el agente la reemplaza por Emergencia.comprobar: las herramientas largas la llaman para poder cortarse
comprobar_emergencia = lambda: None  # noqa: E731
# id de la tarea en curso (lo pone el agente): el historial de movimientos se deshace por tareas
tarea_actual = None


def _zonas_isla_por_defecto():
    """Ventanas de la isla (rectángulo entero). El agente la cambia por ServidorIsla.zonas_isla, que sabe la forma
    exacta de la isla."""
    import ui_isla
    return [ui_isla.rect_ventana(h) for h in ui_isla.ventanas_isla()]


# Fase 7: la herramienta mouse nunca hace clic dentro de la isla (ahí están los botones de confirmar)
zonas_isla = _zonas_isla_por_defecto


def _en_la_isla(punto):
    x, y = punto
    return any(izq <= x < der and arr <= y < aba for izq, arr, der, aba in zonas_isla())


def _bloqueado(motivo):
    return None, {"ok": False, "bloqueado": True, "error": motivo}


# ---------- ventanas donde mouse y teclado no actúan, en ningún modo ----------

# El menú Inicio y la búsqueda de Windows lanzan cualquier cosa escribiendo su nombre: para abrir apps está
# abrir_app, que respeta los bloqueos. Ahí no se escribe (la barra de tareas sí se puede usar).
PROCESOS_INICIO = {"startmenuexperiencehost.exe", "searchhost.exe", "searchapp.exe", "searchui.exe"}
# Cambiar la configuración del sistema es una acción prohibida: ni clics ni teclas en Configuración, el Panel de
# control y sus subprogramas (rundll32, SystemProperties*) ni las consolas de administración (mmc).
PROCESOS_CONFIGURACION = {"systemsettings.exe": "Configuración de Windows", "control.exe": "el Panel de control",
                          "rundll32.exe": "un subprograma del Panel de control",
                          "mmc.exe": "una consola de administración de Windows"}
# carpetas del Panel de control dentro del Explorador (CLSID de la vista por categorías y de todos los elementos)
CLSID_PANEL = ("{26ee0668-a00a-44d7-9371-beb064c98683}", "{21ec2020-3aea-1069-a2dd-08002b30309d}")
TITULOS_PANEL = ("panel de control", "control panel")


def _es_panel_de_control(raiz):
    """Ventana del Explorador que muestra el Panel de control (lo dice su carpeta; si no se puede leer, el título)."""
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        for w in win32com.client.Dispatch("Shell.Application").Windows():
            try:
                if int(w.HWND) == int(raiz):
                    ruta = str(w.Document.Folder.Self.Path).lower()
                    return any(c in ruta for c in CLSID_PANEL)
            except Exception:
                continue
    except Exception:
        pass
    return any(t in _normalizar(win32gui.GetWindowText(raiz)) for t in TITULOS_PANEL)


def ventana_prohibida(hwnd, teclado):
    """Motivo del bloqueo si mouse (teclado=False) o teclado (True) no deben actuar en esta ventana, o None.
    Ante la duda (no se pudo mirar), también se bloquea."""
    try:
        import modo_directo
        raiz = user32.GetAncestor(hwnd, 2) or hwnd  # GA_ROOT
        app = modo_directo.app_de_ventana(raiz)
        exe = (app or {}).get("proceso", "").lower()
        if teclado and exe in PROCESOS_INICIO:
            return ("Es el menú Inicio o la búsqueda de Windows: ahí no escribo. Para abrir una app uso abrir_app, "
                    "que respeta los bloqueos.")
        nombre = PROCESOS_CONFIGURACION.get(exe) or ("las propiedades del sistema" if exe.startswith("systemproperties")
                                                     else None)
        if not nombre and exe == "explorer.exe" and _clase(raiz) == "cabinetwclass" and _es_panel_de_control(raiz):
            nombre = "el Panel de control"
        if nombre:
            return (f"Es {nombre}: cambiar la configuración del sistema está prohibido; no hago clic ni escribo "
                    "ahí.")
        return None
    except Exception:
        return "No pude comprobar en qué ventana actuaría; por seguridad no lo hago."


def _clase(hwnd):
    return win32gui.GetClassName(hwnd).lower()


def prohibida_en_punto(punto):
    """ventana_prohibida para un clic en ese punto de la pantalla (las pruebas la reemplazan)."""
    return ventana_prohibida(win32gui.WindowFromPoint(tuple(int(v) for v in punto)), teclado=False)


def prohibida_al_frente():
    """ventana_prohibida para el teclado, que actúa en la ventana al frente (las pruebas la reemplazan)."""
    return ventana_prohibida(win32gui.GetForegroundWindow(), teclado=True)


def _error(motivo, **extra):
    return None, {"ok": False, "error": motivo, **extra}


# ---------- cerrar_app ----------

# procesos de Windows que nunca se cierran (cerrarlos cuelga la sesión o el escritorio)
PROTEGIDOS = {"system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
              "lsass.exe", "svchost.exe", "dwm.exe", "explorer.exe", "fontdrvhost.exe", "sihost.exe",
              "taskhostw.exe", "ctfmon.exe", "conhost.exe", "runtimebroker.exe", "searchhost.exe",
              "startmenuexperiencehost.exe", "shellexperiencehost.exe", "textinputhost.exe", "audiodg.exe",
              "spoolsv.exe", "msmpeng.exe", "securityhealthservice.exe", "lockapp.exe"}
ESPERA_CIERRE = 5  # segundos para que la app cierre sus ventanas (puede preguntar si guardar)


def _ancestros_propios():
    """El agente y los procesos que lo contienen (la terminal): cerrarlos mataría al propio agente."""
    pids = set()
    try:
        p = psutil.Process()
        while p is not None:
            pids.add(p.pid)
            p = p.parent()
    except psutil.Error:
        pass
    return pids


def planificar_cierre(proceso=None, pid=None, id_ventana=None):
    """Elige la ventana a cerrar. Devuelve ({pid, proceso, ventanas, titulos, otras_del_proceso}, None) o
    (None, error). Si coincide más de una ventana devuelve la lista para elegir por id_ventana: varias ventanas
    pueden ser del mismo proceso (el Bloc de notas de Windows 11 usa uno para todas) y cerrarlas juntas cerraría
    también las que Reizo no pidió."""
    try:
        nombre_pid = psutil.Process(pid).name().lower() if pid is not None else ""
    except psutil.Error:
        nombre_pid = ""
    if (nombre_pid in PROCESOS_OCULTOS or (proceso and _normalizar(proceso).removesuffix(".exe") + ".exe"
                                            in PROCESOS_OCULTOS) or (id_ventana is not None
                                                                     and win32gui.IsWindow(id_ventana)
                                                                     and es_de_la_isla(id_ventana))):
        return _bloqueado("Esa es la isla de Cacao: no la cierro.")
    ventanas = listar_ventanas()
    if id_ventana is not None:
        objetivo = [v for v in ventanas if v["id_ventana"] == id_ventana]
        if not objetivo:
            return _error(f"No hay ninguna ventana abierta con id {id_ventana}; vuelve a usar listar_ventanas.")
    elif pid is not None:
        objetivo = [v for v in ventanas if v["pid"] == pid]
        if not objetivo and not psutil.pid_exists(pid):
            return _error(f"No hay ningún proceso con pid {pid}.")
    elif proceso:
        q = _normalizar(proceso).removesuffix(".exe")
        por_proceso = [v for v in ventanas if _normalizar(v["proceso"]).removesuffix(".exe") == q]
        objetivo = por_proceso or [v for v in ventanas if len(q) >= 3 and q in _normalizar(v["titulo"])]
        if not objetivo:
            return _error("No encontré una ventana abierta que coincida.",
                          ventanas=[f"{v['titulo']} ({v['proceso']})" for v in ventanas])
    else:
        return _error("Indica 'id_ventana', 'proceso' o 'pid' (tomados de listar_ventanas).")
    if len(objetivo) > 1:
        return _error("Hay varias ventanas que coinciden; usa 'id_ventana' para cerrar solo la que pidió Reizo, "
                      "o pregúntale cuál.",
                      coincidencias=[{"id_ventana": v["id_ventana"], "titulo": v["titulo"], "proceso": v["proceso"]}
                                     for v in objetivo])
    elegido = objetivo[0]["pid"] if objetivo else pid
    try:
        nombre = psutil.Process(elegido).name()
    except psutil.Error:
        return _error(f"El proceso {elegido} ya no existe.")
    if nombre.lower() in PROTEGIDOS:
        return _bloqueado(f"{nombre} es un proceso de Windows; no lo cierro por seguridad.")
    if elegido in _ancestros_propios():
        return _bloqueado(f"{nombre} es el propio Cacao o la ventana donde corre; no lo cierro.")
    # Windows Terminal aloja las consolas sin ser su proceso padre: si el agente corre dentro (WT_SESSION),
    # no se sabe cuál de sus ventanas es la suya, así que no se cierra ninguna
    if nombre.lower() == "windowsterminal.exe" and os.environ.get("WT_SESSION"):
        return _bloqueado("Cacao corre dentro de Windows Terminal; cerrarla lo cerraría a él también.")
    ids = {v["id_ventana"] for v in objetivo}
    otras = [v["titulo"] for v in ventanas if v["pid"] == elegido and v["id_ventana"] not in ids]
    return {"pid": elegido, "proceso": nombre, "ventanas": sorted(ids), "titulos": [v["titulo"] for v in objetivo],
            "otras_del_proceso": otras}, None


def cerrar_app(proceso: str = None, pid: int = None, forzar: bool = False, id_ventana: int = None):
    plan, error = planificar_cierre(proceso, pid, id_ventana)
    if error:
        return error
    # cierre normal: WM_CLOSE solo a la ventana elegida, como pulsar su X (la app puede preguntar si guardar)
    for hwnd in plan["ventanas"]:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    limite = time.time() + ESPERA_CIERRE
    while time.time() < limite:
        comprobar_emergencia()
        abiertas = [h for h in plan["ventanas"] if win32gui.IsWindow(h) and win32gui.IsWindowVisible(h)]
        if not abiertas or not psutil.pid_exists(plan["pid"]):
            return {"ok": True, "cerrada": True, "requirio_forzar": False, "proceso": plan["proceso"]}
        time.sleep(0.2)
    if not forzar:
        return {"ok": False, "cerrada": False, "requirio_forzar": False,
                "nota": f"{plan['proceso']} no se cerró en {ESPERA_CIERRE} s; puede estar preguntando si guardar. "
                        "Míralo con ver_pantalla y pregúntale a Reizo qué responder. Usa forzar=true solo si "
                        "Reizo lo pide."}
    if plan["otras_del_proceso"]:
        # forzar termina el proceso entero: se llevaría ventanas que Reizo no pidió cerrar
        return {"ok": False, "cerrada": False, "requirio_forzar": False,
                "error": "Forzar cerraría también estas ventanas del mismo programa: "
                         f"{plan['otras_del_proceso']}. Pregúntale a Reizo antes."}
    # forzado: termina el proceso y sus hijos (los navegadores usan varios)
    try:
        principal = psutil.Process(plan["pid"])
        procesos = principal.children(recursive=True) + [principal]
        for p in procesos:
            p.terminate()
        _, vivos = psutil.wait_procs(procesos, timeout=3)
        for p in vivos:
            p.kill()
    except psutil.NoSuchProcess:
        pass
    return {"ok": True, "cerrada": True, "requirio_forzar": True, "proceso": plan["proceso"]}


# ---------- mover_archivo ----------

def planificar_movimiento(origen, destino):
    """Devuelve ((Path origen, Path destino final), None) o (None, error). Nunca acepta un destino existente."""
    o, error = resolver_ruta(origen)
    if error:
        return _bloqueado(error)
    texto_destino = destino.strip().strip('"')
    partes = Path(texto_destino).parts
    if len(partes) == 1 and partes[0].lower() not in ALIAS and not Path(texto_destino).is_absolute():
        d = o.parent / partes[0]  # solo un nombre nuevo: renombrar en la misma carpeta
    else:
        d, error = resolver_ruta(texto_destino)
        if error:
            return _bloqueado(error)
    if es_sensible(o) or es_sensible(d):
        return _bloqueado("Ese archivo o carpeta puede tener contraseñas o claves; no lo muevo por seguridad.")
    if not o.exists():
        return _error(f"No existe {o}")
    if o in CARPETAS_PERMITIDAS:
        return _bloqueado(f"{o} es una de las carpetas principales; no la muevo.")
    if d.is_dir():
        d = d / o.name  # mover dentro de una carpeta existente
    if d.exists():
        return _error(f"Ya existe {d}; nunca sobrescribo. Elige otro nombre o pregunta a Reizo.")
    if not d.parent.is_dir():
        return _error(f"No existe la carpeta de destino {d.parent}")
    if o.is_dir() and (d == o or d.is_relative_to(o)):
        return _error("No se puede mover una carpeta dentro de sí misma.")
    return (o, d), None


def mover_archivo(origen: str, destino: str):
    plan, error = planificar_movimiento(origen, destino)
    if error:
        return error
    o, d = plan
    try:
        os.rename(o, d)  # en el mismo disco es atómico y falla si el destino ya existe: nunca sobrescribe
    except FileExistsError:
        return {"ok": False, "error": f"Ya existe {d}; nunca sobrescribo."}
    except OSError:
        if d.exists():  # otro disco: shutil.move copiaría encima, así que se vuelve a comprobar justo antes
            return {"ok": False, "error": f"Ya existe {d}; nunca sobrescribo."}
        shutil.move(str(o), str(d))
    anotar_movimiento(o, d)
    return {"ok": True, "ruta_final": str(d)}


HISTORIAL_MOVIMIENTOS = Path(__file__).parent / "historial_movimientos.json"  # no va a git
MAX_HISTORIAL = 200


def _leer_historial():
    try:
        return json.loads(HISTORIAL_MOVIMIENTOS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def anotar_movimiento(origen, destino):
    historial = _leer_historial()
    historial.append({"fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tarea": tarea_actual,
                      "origen": str(origen), "destino": str(destino)})
    HISTORIAL_MOVIMIENTOS.write_text(json.dumps(historial[-MAX_HISTORIAL:], ensure_ascii=False, indent=1),
                                     encoding="utf-8")


def planificar_deshacer():
    """Los movimientos de la última tarea que movió algo, del último al primero: [(desde, hacia)]. Cada uno vuelve
    a su ruta original solo si sigue donde quedó y el sitio original está libre."""
    historial = _leer_historial()
    if not historial:
        return _error("No hay movimientos que deshacer.")
    tarea = historial[-1].get("tarea")
    grupo = []
    for m in reversed(historial):
        if m.get("tarea") != tarea or (tarea is None and grupo):
            break
        grupo.append(m)
    pasos = []
    for m in grupo:
        desde, hacia = Path(m["destino"]), Path(m["origen"])
        for ruta in (desde, hacia):
            _, error = resolver_ruta(str(ruta))
            if error:
                return _bloqueado(error)
        if not desde.exists():
            return _error(f"{desde} ya no está; no puedo deshacer ese movimiento.")
        if hacia.exists():
            return _error(f"Ya existe {hacia}; nunca sobrescribo.")
        pasos.append((desde, hacia))
    return {"pasos": pasos, "cuantos": len(grupo)}, None


def deshacer_movimiento():
    plan, error = planificar_deshacer()
    if error:
        return error
    hechos = []
    for desde, hacia in plan["pasos"]:
        try:
            os.rename(desde, hacia)
        except OSError:
            if hacia.exists():
                return {"ok": False, "error": f"Ya existe {hacia}; nunca sobrescribo.", "deshechos": hechos}
            shutil.move(str(desde), str(hacia))
        hechos.append(str(hacia))
    historial = _leer_historial()
    HISTORIAL_MOVIMIENTOS.write_text(json.dumps(historial[:-plan["cuantos"]], ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    return {"ok": True, "deshechos": hechos}


# ---------- mouse ----------

MAX_ANTIGUEDAD_CAPTURA = 120  # segundos: con una captura vieja la pantalla pudo cambiar
PROCESS_PER_MONITOR_DPI_AWARE = 2
MDT_EFFECTIVE_DPI = 0


def proceso_dpi_aware():
    """True si Windows le da a este proceso coordenadas en píxeles físicos (mss lo activa al capturar)."""
    valor = ctypes.c_int(0)
    if shcore.GetProcessDpiAwareness(None, ctypes.byref(valor)) != 0:
        return False
    return valor.value != 0


def dpi_en(x, y):
    """DPI efectivo del monitor que contiene el punto físico (x, y): 96 = 100 %, 144 = 150 %."""
    monitor = user32.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 2)  # MONITOR_DEFAULTTONEAREST
    dpi_x, dpi_y = ctypes.c_uint(96), ctypes.c_uint(96)
    if shcore.GetDpiForMonitor(monitor, MDT_EFFECTIVE_DPI, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) != 0:
        return 96
    return dpi_x.value


def a_pantalla(x, y, captura, consciente=None, dpi=None):
    """Convierte (x, y) de la imagen enviada al modelo en coordenadas para SetCursorPos.
    1. Imagen -> píxeles físicos: se deshace la reducción (escala) y se suma el origen de la zona capturada.
    2. Si el proceso no es DPI-aware, Windows virtualiza el cursor en píxeles lógicos: se divide por el
       escalado del monitor (DPI / 96). 'consciente' y 'dpi' se pueden pasar para probar sin tocar Windows."""
    fx = captura["origen"][0] + x / captura["escala"]
    fy = captura["origen"][1] + y / captura["escala"]
    if consciente is None:
        consciente = proceso_dpi_aware()
    if not consciente:
        factor = (dpi or dpi_en(fx, fy)) / 96
        fx, fy = fx / factor, fy / factor
    return round(fx), round(fy)


# ---------- controles (UI Automation) ----------

TIPOS_CONTROL = {"Button", "MenuItem", "MenuBar", "TabItem", "Edit", "Document", "CheckBox", "RadioButton",
                 "ComboBox", "ListItem", "Hyperlink", "SplitButton", "TreeItem", "DataItem", "Slider", "Spinner"}
MAX_CONTROLES = 80


def _ventana_uia(id_ventana):
    from pywinauto import Desktop  # importación diferida: tarda ~1 s y solo la usan estas herramientas
    if not win32gui.IsWindow(id_ventana):
        return None, _error("Esa ventana ya no existe; vuelve a usar listar_ventanas.")[1]
    if es_titulo_sensible(win32gui.GetWindowText(id_ventana)):
        return None, _bloqueado("Esa ventana parece tener contraseñas o claves; no la inspecciono.")[1]
    if es_de_la_isla(id_ventana):
        return None, _bloqueado("Esa es la isla de Cacao: no la inspecciono.")[1]
    return Desktop(backend="uia").window(handle=id_ventana), None


def _emergentes(id_ventana):
    """Menús y ventanas emergentes abiertos por la misma app: son ventanas aparte ("Host de ventanas emergentes"
    en las apps WinUI), así que no salen entre los descendientes de la ventana principal."""
    pid = win32process.GetWindowThreadProcessId(id_ventana)[1]
    encontradas = []

    def agregar(hwnd, _):
        if (hwnd != id_ventana and win32gui.IsWindowVisible(hwnd)
                and win32process.GetWindowThreadProcessId(hwnd)[1] == pid
                and (win32gui.GetWindow(hwnd, win32con.GW_OWNER) == id_ventana
                     or win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOOLWINDOW
                     or win32gui.GetClassName(hwnd) in ("#32768", "Xaml_WindowedPopupClass"))):
            encontradas.append(hwnd)
        return True

    win32gui.EnumWindows(agregar, None)
    return encontradas


def _controles(id_ventana):
    ventana, error = _ventana_uia(id_ventana)
    if error:
        return None, error
    from pywinauto import Desktop
    elementos = list(ventana.descendants())
    for hwnd in _emergentes(id_ventana):
        try:
            elementos += Desktop(backend="uia").window(handle=hwnd).descendants()
        except Exception:  # un menú que se cerró entre la enumeración y la lectura
            continue
    controles = []
    for e in elementos:
        info = e.element_info
        r = info.rectangle
        if info.control_type not in TIPOS_CONTROL or not info.name or r.width() <= 0 or r.height() <= 0:
            continue
        controles.append({"nombre": info.name.strip()[:60], "tipo": info.control_type,
                          "centro": [(r.left + r.right) // 2, (r.top + r.bottom) // 2],
                          "rect": [r.left, r.top, r.right, r.bottom], "habilitado": bool(info.enabled)})
    return controles, None


def listar_controles(id_ventana: int, filtro: str = ""):
    """Controles de una ventana por UI Automation: nombre, tipo y posición en la pantalla real."""
    controles, error = _controles(id_ventana)
    if error:
        return error
    if filtro:
        f = _normalizar(filtro)
        controles = [c for c in controles if f in _normalizar(c["nombre"]) or f in _normalizar(c["tipo"])]
    vistos, unicos = set(), []
    for c in controles:  # algunos controles aparecen repetidos (el botón y su texto)
        clave = (c["nombre"], c["tipo"], tuple(c["centro"]))
        if clave not in vistos:
            vistos.add(clave)
            unicos.append({k: v for k, v in c.items() if k != "rect"})
    if len(unicos) > MAX_CONTROLES:
        return {"total": len(unicos), "mostrados": MAX_CONTROLES, "nota": "Usa 'filtro' para acotar.",
                "controles": unicos[:MAX_CONTROLES]}
    return unicos


def buscar_control(id_ventana, nombre):
    """Devuelve (control, None) o (None, error). Coincidencia exacta (sin mayúsculas ni tildes) y, si no hay,
    una única que contenga el nombre."""
    controles, error = _controles(id_ventana)
    if error:
        return None, error
    q = _normalizar(nombre).strip()
    exactos = [c for c in controles if _normalizar(c["nombre"]) == q]
    candidatos = exactos or [c for c in controles if q in _normalizar(c["nombre"])]
    lugares = {tuple(c["centro"]) for c in candidatos}
    if not candidatos:
        return _error(f"No hay ningún control '{nombre}' en esa ventana; usa listar_controles.")
    if len(lugares) > 1:
        return _error(f"Varios controles se llaman parecido a '{nombre}'; usa el nombre exacto.",
                      coincidencias=[f"{c['nombre']} ({c['tipo']})" for c in candidatos[:10]])
    control = candidatos[0]
    if not control["habilitado"]:
        return _error(f"El control '{control['nombre']}' está deshabilitado.")
    return control, None


# ---------- ¿tuvo efecto? (obstaculos.py) ----------

class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD), ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND), ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND), ("rcCaret", wintypes.RECT)]


ESPERA_EFECTO_S = 1.5  # un diálogo como "Guardar como" tarda en aparecer


def proceso_de(hwnd):
    try:
        return psutil.Process(win32process.GetWindowThreadProcessId(hwnd)[1]).name().lower()
    except (psutil.Error, Exception):
        return ""


def instantanea():
    """Lo visible de la ventana al frente, para saber si una acción cambió algo: la ventana al frente, su título
    (solo en memoria, para comparar), las ventanas visibles de su proceso (diálogos, menús), el control con el foco
    y el número de secuencia del portapapeles."""
    frente = win32gui.GetForegroundWindow()
    hilo, pid = win32process.GetWindowThreadProcessId(frente)
    ventanas = set()

    def agregar(h, _):
        if win32gui.IsWindowVisible(h) and win32process.GetWindowThreadProcessId(h)[1] == pid:
            ventanas.add(h)
        return True

    try:
        win32gui.EnumWindows(agregar, None)
    except Exception:
        pass
    info = _GUITHREADINFO(cbSize=ctypes.sizeof(_GUITHREADINFO))
    foco = info.hwndFocus if user32.GetGUIThreadInfo(hilo, ctypes.byref(info)) else None
    return {"frente": frente, "titulo": win32gui.GetWindowText(frente), "ventanas": frozenset(ventanas),
            "foco": foco, "portapapeles": user32.GetClipboardSequenceNumber()}


def hubo_efecto(antes, despues):
    return any(antes[k] != despues[k] for k in ("frente", "titulo", "ventanas", "foco", "portapapeles"))


def esperar_efecto(antes, espera=ESPERA_EFECTO_S, foto=None, dormir=time.sleep):
    """True en cuanto algo cambia respecto de 'antes', o False tras 'espera' segundos sin cambios."""
    foto = foto or instantanea
    limite = time.monotonic() + espera
    while True:
        dormir(0.1)
        if hubo_efecto(antes, foto()):
            return True
        if time.monotonic() >= limite:
            return False


NOTA_SIN_EFECTO = ("No vi ningún cambio (ni ventana nueva, ni título, ni foco): puede que ese atajo o clic no "
                   "exista en esta app o en este idioma (en español, Guardar suele ser Ctrl+G). Compruébalo con "
                   "listar_controles o ver_pantalla y prueba otro camino, por ejemplo el menú.")


def estado_despues():
    """Lo que hay al frente justo después de una acción: evidencia para que el modelo verifique el resultado."""
    time.sleep(0.6)  # deja que la app reaccione (abrir un menú, un diálogo)
    hwnd = win32gui.GetForegroundWindow()
    titulo = titulo_para_el_modelo(win32gui.GetWindowText(hwnd), proceso_de(hwnd))  # navegadores: sin la pestaña
    return {"ventana_al_frente": "[título sensible]" if es_titulo_sensible(titulo) else titulo,
            "id_ventana": hwnd}


def planificar_mouse(accion, x=None, y=None, cantidad=None, captura=None, ahora=None, control=None,
                     id_ventana=None):
    captura = captura or vision.ultima_captura
    necesita_punto = accion in ("clic", "doble_clic", "clic_derecho", "mover") or x is not None
    if accion not in ("clic", "doble_clic", "clic_derecho", "mover", "desplazar"):
        return _error(f"Acción de mouse desconocida: {accion}")
    plan = {"accion": accion, "pantalla": None, "cantidad": None}
    if control:
        # por nombre (UI Automation): el centro del control ya está en píxeles de la pantalla real
        hwnd = id_ventana or win32gui.GetForegroundWindow()
        if es_de_la_isla(hwnd):
            return _bloqueado("Esa es la isla de Cacao: no hago clic en ella.")
        encontrado, error = buscar_control(hwnd, control)
        if error:
            return None, error
        plan.update(pantalla=tuple(encontrado["centro"]), control=f"{encontrado['nombre']} ({encontrado['tipo']})")
    elif necesita_punto:
        if x is None or y is None:
            return _error("Faltan x e y (en píxeles de la última captura).")
        if captura is None:
            return _error("Primero usa ver_pantalla: las coordenadas son relativas a la última captura.")
        if (ahora or time.time()) - captura["momento"] > MAX_ANTIGUEDAD_CAPTURA:
            return _error("La última captura tiene más de 2 minutos; vuelve a usar ver_pantalla.")
        if not (0 <= x < captura["ancho"] and 0 <= y < captura["alto"]):
            return _error(f"({x}, {y}) está fuera de la captura de {captura['ancho']}x{captura['alto']}.")
        plan["pantalla"] = a_pantalla(x, y, captura)
    if plan["pantalla"] and _en_la_isla(plan["pantalla"]):
        return _bloqueado("Esa posición es la isla de Cacao (sus botones confirman acciones): no hago clic ahí.")
    motivo = prohibida_en_punto(plan["pantalla"] or win32api.GetCursorPos())  # desplazar y mover: bajo el cursor
    if motivo:
        return _bloqueado(motivo)
    if accion == "desplazar":
        if not cantidad:
            return _error("Para desplazar indica 'cantidad' (positivo arriba, negativo abajo).")
        plan["cantidad"] = max(-10, min(10, int(cantidad)))  # pasos de rueda; si manda píxeles, se acota
    return plan, None


def mouse(accion: str, x: int = None, y: int = None, cantidad: int = None, control: str = None,
          id_ventana: int = None):
    plan, error = planificar_mouse(accion, x, y, cantidad, control=control, id_ventana=id_ventana)
    if error:
        return error
    comprobar_emergencia()
    antes = instantanea() if accion in ("clic", "doble_clic", "clic_derecho") else None
    if plan["pantalla"]:
        win32api.SetCursorPos(plan["pantalla"])
    eventos = {"clic": [(win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP)],
               "doble_clic": [(win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP)] * 2,
               "clic_derecho": [(win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP)]}
    for abajo, arriba in eventos.get(accion, []):
        win32api.mouse_event(abajo, 0, 0, 0, 0)
        win32api.mouse_event(arriba, 0, 0, 0, 0)
    if accion == "desplazar":
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, plan["cantidad"] * win32con.WHEEL_DELTA, 0)
    resultado = {"ok": True, "pantalla": plan["pantalla"], "control": plan.get("control")}
    if antes is not None:
        efecto = esperar_efecto(antes)
        resultado.update(efecto_visible=efecto, app=proceso_de(antes["frente"]))
        if not efecto:
            resultado["nota"] = NOTA_SIN_EFECTO
    resultado["despues"] = estado_despues()
    resultado.setdefault("nota", "Comprueba con listar_controles o ver_pantalla que pasó lo que esperabas antes de "
                                 "confirmarlo.")
    return resultado


# ---------- teclado ----------

TECLAS = {"ctrl": win32con.VK_CONTROL, "control": win32con.VK_CONTROL, "alt": win32con.VK_MENU,
          "shift": win32con.VK_SHIFT, "mayus": win32con.VK_SHIFT, "win": win32con.VK_LWIN,
          "enter": win32con.VK_RETURN, "intro": win32con.VK_RETURN, "tab": win32con.VK_TAB,
          "esc": win32con.VK_ESCAPE, "escape": win32con.VK_ESCAPE, "backspace": win32con.VK_BACK,
          "retroceso": win32con.VK_BACK, "delete": win32con.VK_DELETE, "supr": win32con.VK_DELETE,
          "espacio": win32con.VK_SPACE, "space": win32con.VK_SPACE, "arriba": win32con.VK_UP, "up": win32con.VK_UP,
          "abajo": win32con.VK_DOWN, "down": win32con.VK_DOWN, "izquierda": win32con.VK_LEFT,
          "left": win32con.VK_LEFT, "derecha": win32con.VK_RIGHT, "right": win32con.VK_RIGHT,
          "inicio": win32con.VK_HOME, "home": win32con.VK_HOME, "fin": win32con.VK_END, "end": win32con.VK_END,
          "repag": win32con.VK_PRIOR, "pageup": win32con.VK_PRIOR, "avpag": win32con.VK_NEXT,
          "pagedown": win32con.VK_NEXT}
TECLAS.update({"flecha_arriba": win32con.VK_UP, "flecha_abajo": win32con.VK_DOWN,  # nombres que usa el modelo
               "flecha_izquierda": win32con.VK_LEFT, "flecha_derecha": win32con.VK_RIGHT,
               "suprimir": win32con.VK_DELETE, "escape": win32con.VK_ESCAPE})
TECLAS.update({f"f{i}": win32con.VK_F1 + i - 1 for i in range(1, 13)})
TECLAS.update({c: ord(c.upper()) for c in "abcdefghijklmnopqrstuvwxyz0123456789"})
# Atajos bloqueados en cualquier modo (con o sin confirmación). Con Win solo valen los de ventanas y escritorios de
# WIN_PERMITIDOS: el resto abre Inicio o la búsqueda (desde ahí se lanza cualquier cosa), Ejecutar, Configuración,
# la barra de tareas o la bandeja (abren apps sin pasar por abrir_app, y en la bandeja está el modo sin
# confirmación), el portapapeles, la grabación, el dictado o el Narrador.
ATAJOS_BLOQUEADOS = {frozenset({"win", "r"}): "abre Ejecutar, que está bloqueado",
                     frozenset({"win", "x"}): "abre el menú de administración de Windows",
                     frozenset({"win", "i"}): "abre Configuración",
                     frozenset({"win", "s"}): "abre la búsqueda de Windows, desde la que se lanza cualquier cosa",
                     frozenset({"win", "q"}): "abre la búsqueda de Windows, desde la que se lanza cualquier cosa",
                     frozenset({"win", "e"}): "abre el Explorador, cuya barra de direcciones ejecuta comandos",
                     frozenset({"win", "a"}): "abre la configuración rápida",
                     frozenset({"win", "u"}): "abre la configuración de accesibilidad",
                     frozenset({"win", "k"}): "abre la configuración de proyección",
                     frozenset({"win", "p"}): "abre la configuración de proyección",
                     frozenset({"win", "n"}): "abre el centro de notificaciones",
                     frozenset({"win", "b"}): "lleva a la bandeja del sistema",
                     frozenset({"win", "t"}): "lleva a la barra de tareas, que abre apps",
                     frozenset({"win", "v"}): "abre el historial del portapapeles",
                     frozenset({"win", "h"}): "activa el dictado por voz",
                     frozenset({"win", "l"}): "bloquea la sesión",
                     frozenset({"win", "g"}): "abre la Xbox Game Bar (graba la pantalla)",
                     frozenset({"win", "alt", "r"}): "graba la pantalla",
                     frozenset({"win", "ctrl", "enter"}): "activa el Narrador",
                     frozenset({"win", "ctrl", "o"}): "abre el teclado en pantalla",
                     frozenset({"win", "ctrl", "shift", "b"}): "reinicia el controlador gráfico",
                     frozenset({"win"}): "abre el menú Inicio, desde el que se lanza cualquier cosa",
                     frozenset({"ctrl", "esc"}): "abre el menú Inicio, desde el que se lanza cualquier cosa",
                     frozenset({"ctrl", "shift", "esc"}): "abre el Administrador de tareas (puede ejecutar programas)",
                     frozenset({"ctrl", "alt", "delete"}): "abre la pantalla de seguridad de Windows",
                     frozenset({"alt", "f4"}): "cierra ventanas sin las protecciones de cerrar_app (y en el "
                                               "escritorio abre Apagar); usa cerrar_app",
                     frozenset({"ctrl", "alt", "shift", "q"}): "es el atajo de emergencia de Cacao"}
ATAJOS_BLOQUEADOS.update({frozenset({"win", str(n)}): "abre una app de la barra de tareas sin pasar por abrir_app"
                          for n in range(10)})
WIN_PERMITIDOS = {frozenset({"win", t}) for t in ("d", "m", "tab", "arriba", "abajo", "izquierda", "derecha")} | {
    frozenset({"win", "shift", t}) for t in ("m", "s", "arriba", "abajo", "izquierda", "derecha")} | {
    frozenset({"win", "ctrl", t}) for t in ("d", "izquierda", "derecha", "f4")}
MAX_TEXTO = 2000


def _canonica(tecla):
    t = _normalizar(tecla).strip()
    return {"control": "ctrl", "mayus": "shift", "escape": "esc", "intro": "enter", "supr": "delete", "suprimir": "delete",
            "retroceso": "backspace", "up": "arriba", "down": "abajo", "left": "izquierda", "right": "derecha",
            "flecha_arriba": "arriba", "flecha_abajo": "abajo", "flecha_izquierda": "izquierda",
            "flecha_derecha": "derecha", "home": "inicio", "end": "fin", "space": "espacio"}.get(t, t)


def planificar_teclado(accion, texto=None, teclas=None):
    if accion == "escribir":
        if not texto:
            return _error("Para 'escribir' indica 'texto'.")
        if parece_atajo(texto):
            return _error("Ese texto parece un atajo de teclado. No lo escribiré: usa accion 'atajo' y pasa "
                          "cada tecla en 'teclas', por ejemplo ['ctrl', 'g'].")
        if len(texto) > MAX_TEXTO:
            return _error(f"El texto supera {MAX_TEXTO} caracteres; divídelo.")
        return {"accion": accion, "texto": texto}, None
    if accion not in ("atajo", "tecla"):
        return _error(f"Acción de teclado desconocida: {accion}")
    if not teclas:
        return _error("Indica 'teclas', por ejemplo ['ctrl', 's'].")
    desconocidas = [t for t in teclas if _normalizar(t).strip() not in TECLAS]
    if desconocidas:
        return _error(f"Teclas desconocidas: {desconocidas}. Usa nombres como ctrl, alt, shift, win, enter, tab, "
                      "esc, f1-f12, flechas (arriba/abajo/izquierda/derecha), letras o números.")
    combo = frozenset(_canonica(t) for t in teclas)
    if accion == "atajo" and combo in ATAJOS_BLOQUEADOS:
        return _bloqueado(f"El atajo {'+'.join(teclas)} {ATAJOS_BLOQUEADOS[combo]}; no lo uso.")
    if accion == "atajo" and "win" in combo and combo not in WIN_PERMITIDOS:
        return _bloqueado(f"El atajo {'+'.join(teclas)} usa la tecla Windows: solo uso los de ventanas y "
                          "escritorios (Win+D, Win+flechas...).")
    if accion == "tecla" and "win" in combo:
        return _bloqueado("La tecla Windows sola abre el menú Inicio, desde el que se lanza cualquier cosa; no la uso.")
    return {"accion": accion, "teclas": [TECLAS[_normalizar(t).strip()] for t in teclas],
            "nombres": [_canonica(t) for t in teclas]}, None


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _MOUSEINPUT(ctypes.Structure):  # solo para que la unión tenga el tamaño correcto
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


INPUT_KEYBOARD, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 1, 0x0002, 0x0004


def _enviar(vk=0, scan=0, flags=0):
    entrada = _INPUT(type=INPUT_KEYBOARD, ki=_KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags))
    user32.SendInput(1, ctypes.byref(entrada), ctypes.sizeof(_INPUT))


def _enviar_par(scan):
    """Bajar y subir un carácter Unicode en una sola llamada, para que la app no los separe."""
    entradas = (_INPUT * 2)(_INPUT(type=INPUT_KEYBOARD, ki=_KEYBDINPUT(wScan=scan, dwFlags=KEYEVENTF_UNICODE)),
                            _INPUT(type=INPUT_KEYBOARD,
                                   ki=_KEYBDINPUT(wScan=scan, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)))
    user32.SendInput(2, entradas, ctypes.sizeof(_INPUT))


MODO_ESCRIBIR = "pegar"  # "pegar" (portapapeles + Ctrl+V) o "teclear" (Unicode carácter a carácter)
PAUSA_TECLEO = 0.012  # segundos entre caracteres al teclear: las apps WinUI pierden pulsaciones muy seguidas


def _pegar(texto):
    """Pone el texto en el portapapeles, pulsa Ctrl+V y devuelve el texto que había antes (solo si era texto;
    otro contenido, como una imagen, se pierde y se avisa en el resultado)."""
    win32clipboard.OpenClipboard()
    try:
        anterior = (win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT) else None)
        otro_contenido = anterior is None and win32clipboard.CountClipboardFormats() > 0
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(texto, win32con.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()
    _enviar(vk=win32con.VK_CONTROL)
    _enviar(vk=ord("V"))
    _enviar(vk=ord("V"), flags=KEYEVENTF_KEYUP)
    _enviar(vk=win32con.VK_CONTROL, flags=KEYEVENTF_KEYUP)
    time.sleep(0.4)  # la app lee el portapapeles después de recibir Ctrl+V
    if anterior is not None:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(anterior, win32con.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
    return otro_contenido


def isla_al_frente():
    """True si la ventana al frente es la isla de Cacao (su campo de texto tiene el foco)."""
    try:
        return es_de_la_isla(win32gui.GetForegroundWindow())
    except Exception:
        return False


def ventana_sensible_al_frente():
    """True si la ventana al frente es sensible: su título nombra contraseñas o claves (lo mismo que ver_pantalla
    no captura) o es un gestor de contraseñas, Seguridad de Windows o una app de banco (las apps privadas del
    registro de hábitos). Ante la duda, también."""
    try:
        import habitos
        fuente = habitos.FuenteWindows()
        ventana = fuente.ventana_al_frente()
        if ventana is None:
            return False
        return es_titulo_sensible(fuente.titulo(ventana["hwnd"])) or habitos.Privacidad(fuente).es_app_privada(ventana)
    except Exception:
        return True


def planificar_teclado_ventana():
    """(None, error) si teclado no debe escribir en la ventana al frente. Son bloqueos (cortan la tarea) en cualquier
    modo: en la isla nunca, porque su campo manda pedidos al agente y el agente no puede dictarse pedidos a sí mismo;
    tampoco en una ventana sensible, en el menú Inicio o la búsqueda, ni en Configuración o el Panel de control."""
    if isla_al_frente():
        return _bloqueado("La ventana al frente es la isla de Cacao: no escribo ni pulso teclas en ella.")
    if ventana_sensible_al_frente():
        return _bloqueado("La ventana al frente es sensible (contraseñas, claves, seguridad o banco): no escribo ni "
                          "pulso teclas en ella.")
    motivo = prohibida_al_frente()
    if motivo:
        return _bloqueado(motivo)
    return None, None


def teclado(accion: str, texto: str = None, teclas: list = None):
    plan, error = planificar_teclado(accion, texto, teclas)
    if error:
        return error
    _, error = planificar_teclado_ventana()
    if error:
        return error
    comprobar_emergencia()
    antes = instantanea()
    reemplazo_otro_contenido = False
    if accion == "escribir" and MODO_ESCRIBIR == "pegar":
        reemplazo_otro_contenido = _pegar(plan["texto"])
    elif accion == "escribir":
        # Unicode carácter a carácter: tildes y ñ sin depender de la distribución del teclado
        for i, c in enumerate(plan["texto"]):
            if i % 20 == 0:
                comprobar_emergencia()
            if c == "\n":
                _enviar(vk=win32con.VK_RETURN)
                _enviar(vk=win32con.VK_RETURN, flags=KEYEVENTF_KEYUP)
                continue
            datos = c.encode("utf-16-le")  # 2 o 4 bytes: los emojis van como par sustituto
            for j in range(0, len(datos), 2):
                _enviar_par(int.from_bytes(datos[j:j + 2], "little"))
            time.sleep(PAUSA_TECLEO)
    elif accion == "atajo":
        for vk in plan["teclas"]:
            _enviar(vk=vk)
        for vk in reversed(plan["teclas"]):
            _enviar(vk=vk, flags=KEYEVENTF_KEYUP)
    else:  # tecla: una tras otra
        for vk in plan["teclas"]:
            comprobar_emergencia()
            _enviar(vk=vk)
            _enviar(vk=vk, flags=KEYEVENTF_KEYUP)
    efecto = esperar_efecto(antes)
    resultado = {"ok": True, "efecto_visible": efecto, "app": proceso_de(antes["frente"]),
                 "despues": estado_despues(),
                 "nota": "Comprueba con listar_controles o ver_pantalla que pasó lo que esperabas antes de confirmarlo."
                 if efecto else NOTA_SIN_EFECTO}
    if reemplazo_otro_contenido:
        resultado["nota_portapapeles"] = "El portapapeles tenía algo que no era texto y se reemplazó."
    return resultado
