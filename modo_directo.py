"""
Modo sin confirmación (diseño aprobado por Reizo el 2026-10-05).

Lo activa y lo desactiva solo Reizo, con un clic FÍSICO en la bandeja o en la isla (la isla lo comprueba con un hook
de mouse de bajo nivel, LLMHF_INJECTED). Ninguna herramienta del agente ni la voz pueden cambiarlo: el estado vive
en el agente y solo lo toca ServidorIsla al recibir ese clic. Empieza apagado en cada arranque.

Con el modo activo, Politica.decidir() dice si una herramienta va directa (sin preguntar) o sigue las reglas
normales (que piden confirmación según el permiso, y en modo voz para todo lo que cambia algo):
  - directas: volumen, abrir_app, enfocar_ventana, buscar_web y cerrar_app con cierre normal;
  - mouse: solo si el punto del clic está en una ventana de la app que Reizo nombró en el pedido (nunca la barra de
    tareas, el escritorio, Inicio ni la isla);
  - teclado: solo en la ventana al frente de la app nombrada, y 'escribir' solo con texto que sale del pedido. Una
    'tecla' con letras o números, o un atajo con letras sin Ctrl ni Alt, es escribir: sigue las reglas normales;
  - mover_archivo: directo hasta 10 archivos por tarea, sin ejecutables ni scripts y fuera de las carpetas
    importantes (datos_locales.json -> carpetas_importantes). Cada movimiento queda en un historial para deshacer;
  - siempre con confirmación: ejecutar_powershell y cerrar_app forzado;
  - si en la tarea entró contenido externo (leer_archivo, buscar_web, ejecutar_powershell), todo vuelve a las reglas
    normales hasta que termine. ver_pantalla, listar_controles y listar_ventanas sirven para ubicar botones y
    ventanas: después de usarlas, mouse, teclado, enfocar_ventana, cerrar_app y abrir_app solo van directos sobre la
    app nombrada, y buscar_web y mover_archivo vuelven a las reglas normales (lo de la pantalla no puede dictarlos).
Los bloqueos no cambian: lo bloqueado sigue bloqueado en cualquier modo.
"""
import ctypes
import json
import os
import re
import unicodedata
from ctypes import wintypes
from pathlib import Path

BASE = Path(__file__).parent
RUTA_DATOS_LOCALES = BASE / "datos_locales.json"

DIRECTAS = {"volumen", "abrir_app", "enfocar_ventana", "buscar_web"}
EXTERNO = {"leer_archivo", "buscar_web", "ejecutar_powershell"}
UBICACION = {"ver_pantalla", "listar_controles", "listar_ventanas"}
SIEMPRE_CONFIRMAR = {"ejecutar_powershell"}
MAX_ARCHIVOS = 10
EXTENSIONES_RIESGO = {".exe", ".dll", ".bat", ".ps1", ".cmd", ".msi", ".lnk",
                      ".vbs", ".js", ".scr", ".com", ".reg", ".psm1", ".msc"}  # las 7 pedidas y otras parecidas
# ventanas del shell: un clic ahí abre apps o menús de Windows, nunca cuenta como "dentro de la app"
CLASES_SHELL = {"shell_traywnd", "shell_secondarytraywnd", "progman", "workerw", "notifyiconoverflowwindow",
                "toplevelwindowforoverflowxamlisland", "windows.ui.core.corewindow", "xaml_windowedpopupclass"}
PROCESOS_SHELL = {"startmenuexperiencehost.exe", "searchhost.exe", "shellexperiencehost.exe", "asistente-ui.exe"}
VENDEDORES = ("microsoft ", "google ", "mozilla ", "adobe ")
# teclas que no escriben nada (navegar, borrar, enviar)
TECLAS_SIN_TEXTO = {"enter", "tab", "esc", "backspace", "delete", "supr", "arriba", "abajo", "izquierda", "derecha",
                    "inicio", "fin", "repag", "avpag", "pageup", "pagedown", "up", "down", "left", "right", "home",
                    "end", "flecha_arriba", "flecha_abajo", "flecha_izquierda", "flecha_derecha", "suprimir",
                    "retroceso", "intro", "escape", "espacio", "space", "shift", "mayus"} | {f"f{i}" for i in range(1, 13)}


def normalizar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^\w]+", " ", t).split())


def carpetas_importantes(ruta=RUTA_DATOS_LOCALES):
    if not Path(ruta).exists():
        return []
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    return [Path(os.path.expandvars(c)).resolve() for c in datos.get("carpetas_importantes", [])
            if isinstance(c, str) and c.strip() and not c.startswith("ej:")]


def nombrada_en(nombres, pedido):
    """True si alguno de los nombres de la app aparece en el pedido como palabras completas."""
    p = f" {normalizar(pedido)} "
    for n in nombres:
        n = normalizar(n)
        for v in VENDEDORES:
            if n.startswith(v.strip() + " "):
                n = n[len(v):]
        if len(n) >= 3 and f" {n} " in p:
            return True
    return False


def texto_del_pedido(texto, pedido):
    """True si todo el texto a escribir sale del pedido (sin mayúsculas, tildes ni signos)."""
    t = normalizar(texto)
    return bool(t) and f" {t} " in f" {normalizar(pedido)} "


# ---------- ventanas (Win32; las pruebas pasan funciones falsas) ----------

user32 = ctypes.windll.user32
GA_ROOT = 2


def _clase(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value.lower()


def app_de_ventana(hwnd):
    """{'nombres', 'proceso', 'pid', 'shell'} de una ventana de primer nivel. Para las apps de la Tienda (el proceso
    visible es ApplicationFrameHost) se usa la ventana hija de la app real, como en el registro de hábitos."""
    import habitos
    import herramientas_grupo4 as g4
    if not hwnd or not user32.IsWindow(hwnd):
        return None
    raiz = user32.GetAncestor(hwnd, GA_ROOT) or hwnd
    pid = habitos._pid_de(raiz)
    ruta = habitos._ruta_de_pid(pid)
    if ruta and ruta.lower().endswith("applicationframehost.exe"):
        hijos = []
        cb = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(
            lambda h, _: hijos.append(habitos._pid_de(h)) or True)
        user32.EnumChildWindows(raiz, cb, 0)
        otro = next((p for p in hijos if p != pid), None)
        if otro:
            pid, ruta = otro, habitos._ruta_de_pid(otro)
    exe = (ruta or "").replace("/", "\\").rsplit("\\", 1)[-1]
    info = habitos.Clasificador().info(ruta, habitos.aumid_de_pid(pid))
    propio = pid in g4._ancestros_propios() or (exe.lower() == "windowsterminal.exe" and os.environ.get("WT_SESSION"))
    return {"nombres": {info["nombre"], exe.removesuffix(".exe").removesuffix(".EXE")}, "proceso": exe, "pid": pid,
            "shell": _clase(raiz) in CLASES_SHELL or exe.lower() in PROCESOS_SHELL or bool(propio)}


def app_en_punto(x, y):
    return app_de_ventana(user32.WindowFromPoint(wintypes.POINT(int(x), int(y))))


def app_al_frente():
    return app_de_ventana(user32.GetForegroundWindow())


def posicion_cursor():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


# ---------- archivos ----------

def contar_archivos(ruta, limite=MAX_ARCHIVOS + 1):
    """(cuántos archivos mueve, si alguno es ejecutable o script). Cuenta hasta 'limite' para no recorrer carpetas
    enormes; si llega al límite ya no hace falta saber más."""
    ruta = Path(ruta)
    if ruta.is_file():
        return 1, ruta.suffix.lower() in EXTENSIONES_RIESGO
    n, riesgo = 0, False
    for raiz, _, archivos in os.walk(ruta):
        for a in archivos:
            n += 1
            riesgo = riesgo or Path(a).suffix.lower() in EXTENSIONES_RIESGO
            if n >= limite or riesgo:
                return n, riesgo
    return n, riesgo


def en_importante(ruta, importantes):
    r = Path(ruta).resolve()
    return next((c for c in importantes if r == c or r.is_relative_to(c)), None)


# ---------- política ----------

class Politica:
    def __init__(self, app_en_punto=app_en_punto, app_al_frente=app_al_frente, posicion_cursor=posicion_cursor,
                 planificar_mouse=None, planificar_movimiento=None, importantes=None, contar=contar_archivos):
        import herramientas_grupo4 as g4
        self.app_en_punto, self.app_al_frente, self.posicion_cursor = app_en_punto, app_al_frente, posicion_cursor
        self.planificar_mouse = planificar_mouse or g4.planificar_mouse
        self.planificar_movimiento = planificar_movimiento or g4.planificar_movimiento
        self._importantes = importantes
        self.contar = contar

    @property
    def importantes(self):
        return self._importantes if self._importantes is not None else carpetas_importantes()

    def decidir(self, nombre, args, pedido, usadas, movidos=0):
        """(True, detalle) si va directa; (False, motivo) si sigue las reglas normales. 'usadas': nombres de las
        herramientas ya usadas en la tarea; 'movidos': archivos ya movidos sin confirmación en la tarea.
        Para mouse y teclado, el detalle trae lo que la ejecución debe volver a comprobar (la app y el punto)."""
        if nombre in SIEMPRE_CONFIRMAR:
            return False, f"{nombre} siempre se confirma"
        if nombre == "cerrar_app" and args.get("forzar"):
            return False, "cerrar a la fuerza siempre se confirma"
        externo = sorted(set(usadas) & EXTERNO)
        if externo:
            return False, f"en esta tarea entró contenido externo ({', '.join(externo)})"
        ubico = bool(set(usadas) & UBICACION)
        if nombre == "volumen":
            return True, None
        if nombre == "buscar_web":
            return (False, "la búsqueda podría venir de lo que hay en pantalla") if ubico else (True, None)
        if nombre == "abrir_app":
            if ubico and not nombrada_en([args.get("nombre", "")], pedido):
                return False, "abre una app que no nombraste, después de mirar la pantalla"
            return True, None
        if nombre in ("enfocar_ventana", "cerrar_app"):
            if not ubico:
                return True, None
            app = self._app_objetivo(nombre, args)
            if app and not app["shell"] and nombrada_en(app["nombres"], pedido):
                return True, None
            return False, "la ventana no es de la app que nombraste"
        if nombre == "mouse":
            return self._mouse(args, pedido)
        if nombre == "teclado":
            return self._teclado(args, pedido)
        if nombre == "mover_archivo":
            return self._mover(args, movidos, ubico)
        if nombre == "deshacer_movimiento":
            return True, None
        return False, "no es de las que van directas"

    def _app_objetivo(self, nombre, args):
        import win32gui
        hwnd = args.get("id_ventana")
        if hwnd and win32gui.IsWindow(hwnd):
            return app_de_ventana(hwnd)
        return None

    def _mouse(self, args, pedido):
        plan, error = self.planificar_mouse(args.get("accion"), args.get("x"), args.get("y"), args.get("cantidad"),
                                            control=args.get("control"), id_ventana=args.get("id_ventana"))
        if error:
            return False, "el clic no se pudo planificar"
        punto = plan["pantalla"] or self.posicion_cursor()
        app = self.app_en_punto(*punto)
        if not app or app["shell"]:
            return False, "el clic cae en Windows (barra de tareas, escritorio, Inicio) o en el propio Cacao"
        if not nombrada_en(app["nombres"], pedido):
            return False, f"el clic cae en {app['proceso']}, que no es la app que nombraste"
        return True, {"pid": app["pid"], "nombres": sorted(app["nombres"])}

    def _teclado(self, args, pedido):
        app = self.app_al_frente()
        if not app or app["shell"]:
            return False, "la ventana al frente es de Windows o del propio Cacao"
        if not nombrada_en(app["nombres"], pedido):
            return False, f"la ventana al frente es {app['proceso']}, que no es la app que nombraste"
        accion = args.get("accion")
        teclas = [normalizar(t) for t in args.get("teclas") or []]
        if accion == "escribir":
            if not texto_del_pedido(args.get("texto", ""), pedido):
                return False, "el texto no sale de tu pedido"
        elif accion == "tecla":
            if any(t not in TECLAS_SIN_TEXTO for t in teclas):
                return False, "esas teclas escriben texto"
        elif accion == "atajo":
            modificadores = {"ctrl", "control", "alt"}
            if not modificadores & set(teclas) and any(t not in TECLAS_SIN_TEXTO for t in teclas):
                return False, "ese atajo escribe texto"
        return True, {"pid": app["pid"], "nombres": sorted(app["nombres"])}

    def _mover(self, args, movidos, ubico):
        if ubico:
            return False, "el movimiento podría venir de lo que hay en pantalla"
        plan, error = self.planificar_movimiento(args.get("origen", ""), args.get("destino", ""))
        if error:
            return False, "el movimiento no se pudo planificar"
        origen, destino = plan
        for ruta in (origen, destino):
            carpeta = en_importante(ruta, self.importantes)
            if carpeta:
                return False, f"{carpeta} está en tus carpetas importantes"
        n, riesgo = self.contar(origen)
        if riesgo:
            return False, "hay ejecutables o scripts"
        if movidos + n > MAX_ARCHIVOS:
            return False, f"serían {movidos + n} archivos en esta tarea (más de {MAX_ARCHIVOS})"
        return True, {"archivos": n}
