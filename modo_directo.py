"""
Modo sin confirmación (diseño aprobado por Reizo el 2026-10-05).

Lo activa y lo desactiva solo Reizo, con un clic FÍSICO en la bandeja o en la isla (la isla lo comprueba con un hook
de mouse de bajo nivel, LLMHF_INJECTED). Ninguna herramienta del agente ni la voz pueden cambiarlo: el estado vive
en el agente y solo lo toca ServidorIsla al recibir ese clic. Empieza apagado en cada arranque.

Con el modo activo, Politica.decidir() dice si una herramienta va directa (sin preguntar) o sigue las reglas
normales (que piden confirmación según el permiso, y en modo voz para todo lo que cambia algo):
  - directas: volumen, abrir_app, enfocar_ventana, buscar_web y cerrar_app con cierre normal;
  - mouse y teclado (decisión de Reizo del 2026-10-06): directos en cualquier ventana, también tras leer contenido de
    fuera. Única excepción: escribir un texto que no sale del pedido cuando el modelo leyó contenido de fuera (web,
    archivo, pantalla, carpetas, PowerShell, y títulos de ventanas solo si alguna es de un navegador, porque ese
    título lo pone cada página web) en esta tarea o en una anterior que sigue en su historial: ese texto puede venir
    de lo leído, y se pregunta. Una 'tecla' con letras o números, o un atajo con letras sin Ctrl
    ni Alt, también escribe texto;
  - mover_archivo: directo hasta 10 archivos por tarea, sin ejecutables ni scripts y fuera de las carpetas
    importantes (datos_locales.json -> carpetas_importantes). Cada movimiento queda en un historial para deshacer;
  - siempre con confirmación: ejecutar_powershell, autocompletar_login y cerrar_app forzado;
  - si en la tarea entró contenido externo (leer_archivo, buscar_web, ejecutar_powershell), todo lo demás vuelve a
    las reglas normales hasta que termine. ver_pantalla, listar_controles y listar_ventanas sirven para ubicar botones
    y ventanas: después de usarlas, enfocar_ventana, cerrar_app y abrir_app solo van directos sobre la app nombrada,
    y buscar_web y mover_archivo vuelven a las reglas normales (lo de la pantalla no puede dictarlos).
Los bloqueos no cambian: lo bloqueado sigue bloqueado en cualquier modo (atajos peligrosos, clic o teclas en la isla,
escribir en ventanas sensibles; herramientas_grupo4.py).
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
# todo lo que pone texto de fuera delante del modelo (como agente_minimo.TEXTO_EXTERNO)
LECTURA_EXTERNA = EXTERNO | UBICACION | {"listar_carpeta"}
# los títulos de sus ventanas los pone cada página web (config.json -> memoria_wiki.navegadores)
NAVEGADORES = {x.lower() for x in json.loads((BASE / "config.json").read_text(encoding="utf-8"))
               .get("memoria_wiki", {}).get("navegadores", [])}
SIEMPRE_CONFIRMAR = {"ejecutar_powershell", "autocompletar_login"}
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


def lectura_externa(nombre, resultado):
    """True si el resultado de la herramienta pone delante del modelo texto que no controla Reizo. listar_ventanas
    solo cuenta si alguna ventana es de un navegador: los títulos de las demás apps no los escribe una página web."""
    if nombre not in LECTURA_EXTERNA:
        return False
    if nombre == "listar_ventanas":
        return isinstance(resultado, list) and any(
            isinstance(v, dict) and str(v.get("proceso", "")).lower() in NAVEGADORES for v in resultado)
    return True


def leido_en_historial(historial):
    """Herramientas de tareas anteriores cuyo contenido de fuera el modelo aún tiene en el historial. Un
    listar_ventanas ya resumido (sin títulos) no cuenta."""
    leido = set()
    for m in historial:
        c = m.get("content")
        if m.get("role") != "user" or not isinstance(c, str) or not c.startswith("Resultado de "):
            continue
        cabecera, _, cuerpo = c.removeprefix("Resultado de ").partition(": ")
        nombre = cabecera.split(" ")[0]
        try:
            resultado = json.loads(cuerpo) if " " not in cabecera else None  # "(resumido)": sin el JSON entero
        except ValueError:
            resultado = None
        if lectura_externa(nombre, resultado):
            leido.add(nombre)
    return leido


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
    def __init__(self, planificar_movimiento=None, importantes=None, contar=contar_archivos):
        import herramientas_grupo4 as g4
        self.planificar_movimiento = planificar_movimiento or g4.planificar_movimiento
        self._importantes = importantes
        self.contar = contar

    @property
    def importantes(self):
        return self._importantes if self._importantes is not None else carpetas_importantes()

    def decidir(self, nombre, args, pedido, usadas, movidos=0, leido=None):
        """(True, detalle) si va directa; (False, motivo) si sigue las reglas normales. 'usadas': nombres de las
        herramientas ya usadas en la tarea; 'movidos': archivos ya movidos sin confirmación en la tarea;
        'leido': herramientas cuyo contenido de fuera tiene el modelo delante (lectura_externa, en esta tarea o en
        el historial); sin darlo, cuenta toda herramienta de LECTURA_EXTERNA usada en la tarea."""
        if nombre in SIEMPRE_CONFIRMAR:
            return False, f"{nombre} siempre se confirma"
        if nombre == "cerrar_app" and args.get("forzar"):
            return False, "cerrar a la fuerza siempre se confirma"
        if nombre == "mouse":
            return True, None
        if nombre == "teclado":
            return self._teclado(args, pedido, sorted(set(usadas) & LECTURA_EXTERNA if leido is None else leido))
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

    def _teclado(self, args, pedido, leido):
        """Directo salvo un texto que no sale del pedido después de leer contenido de fuera ('leido')."""
        if not leido:
            return True, None
        accion = args.get("accion")
        teclas = [normalizar(t) for t in args.get("teclas") or []]
        escribe = [t for t in teclas if t not in TECLAS_SIN_TEXTO]
        if accion == "escribir":
            texto = args.get("texto", "")
        elif escribe and (accion == "tecla" or not {"ctrl", "control", "alt"} & set(teclas)):
            texto = "".join(escribe)  # letras o números sueltos, o un atajo con letras sin Ctrl ni Alt
        else:
            return True, None
        if texto_del_pedido(texto, pedido):
            return True, None
        return False, f"el texto no sale de tu pedido y ya leí contenido de fuera ({', '.join(leido)})"

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
