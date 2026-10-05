"""
Fase 5, grupo 4: cerrar_app, mover_archivo, mouse y teclado. Todas tienen permiso 'confirmar' en
herramientas.json (el ejecutor pide un sí antes de llamarlas).

Cada herramienta se divide en planificar_* (valida y calcula qué haría, sin efectos) y la función real que ejecuta
ese plan. Las pruebas usan solo los planes. Los rechazos de seguridad devuelven "bloqueado": True; el ejecutor
corta la tarea al verlos.
"""
import ctypes
import os
import shutil
import time
from ctypes import wintypes
from pathlib import Path

import psutil
import win32api
import win32clipboard
import win32con
import win32gui
import win32process

import vision
from herramientas_grupo1 import (ALIAS, CARPETAS_PERMITIDAS, PROCESOS_OCULTOS, _normalizar, es_de_la_isla,
                                 es_sensible, es_titulo_sensible, listar_ventanas, resolver_ruta)

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
        return _bloqueado("Esa es la isla del asistente: no la cierro.")
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
        return _bloqueado(f"{nombre} es el propio asistente o la ventana donde corre; no lo cierro.")
    # Windows Terminal aloja las consolas sin ser su proceso padre: si el agente corre dentro (WT_SESSION),
    # no se sabe cuál de sus ventanas es la suya, así que no se cierra ninguna
    if nombre.lower() == "windowsterminal.exe" and os.environ.get("WT_SESSION"):
        return _bloqueado("El asistente corre dentro de Windows Terminal; cerrarla lo cerraría a él también.")
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
    return {"ok": True, "ruta_final": str(d)}


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
        return None, _bloqueado("Esa es la isla del asistente: no la inspecciono.")[1]
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


def estado_despues():
    """Lo que hay al frente justo después de una acción: evidencia para que el modelo verifique el resultado."""
    time.sleep(0.6)  # deja que la app reaccione (abrir un menú, un diálogo)
    hwnd = win32gui.GetForegroundWindow()
    titulo = win32gui.GetWindowText(hwnd)
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
            return _bloqueado("Esa es la isla del asistente: no hago clic en ella.")
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
        return _bloqueado("Esa posición es la isla del asistente (sus botones confirman acciones): no hago clic ahí.")
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
    return {"ok": True, "pantalla": plan["pantalla"], "control": plan.get("control"), "despues": estado_despues(),
            "nota": "Comprueba con listar_controles o ver_pantalla que pasó lo que esperabas antes de confirmarlo."}


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
# combinaciones que abren herramientas bloqueadas o el propio atajo de emergencia
ATAJOS_BLOQUEADOS = {frozenset({"win", "r"}): "abre Ejecutar, que está bloqueado",
                     frozenset({"win", "x"}): "abre el menú de administración de Windows",
                     frozenset({"ctrl", "alt", "shift", "q"}): "es el atajo de emergencia del asistente"}
MAX_TEXTO = 2000


def _canonica(tecla):
    t = _normalizar(tecla).strip()
    return {"control": "ctrl", "mayus": "shift", "escape": "esc", "intro": "enter"}.get(t, t)


def planificar_teclado(accion, texto=None, teclas=None):
    if accion == "escribir":
        if not texto:
            return _error("Para 'escribir' indica 'texto'.")
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


def teclado(accion: str, texto: str = None, teclas: list = None):
    plan, error = planificar_teclado(accion, texto, teclas)
    if error:
        return error
    comprobar_emergencia()
    if accion == "escribir" and MODO_ESCRIBIR == "pegar":
        if _pegar(plan["texto"]):
            return {"ok": True, "nota": "El portapapeles tenía algo que no era texto y se reemplazó."}
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
    if accion == "escribir":
        return {"ok": True}
    return {"ok": True, "despues": estado_despues(),
            "nota": "Comprueba con listar_controles o ver_pantalla que pasó lo que esperabas antes de confirmarlo."}
