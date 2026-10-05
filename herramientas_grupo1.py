"""
Fase 5, grupo 1: listar_ventanas, enfocar_ventana, listar_carpeta, leer_archivo y buscar_web.
Las de archivos solo aceptan rutas dentro de limites.carpetas_permitidas de herramientas.json.
"""
import ctypes
import fnmatch
import json
import os
import re
import unicodedata
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import psutil
import win32con
import win32gui
import win32process

BASE = Path(__file__).parent
_LIMITES = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))["limites"]
CARPETAS_PERMITIDAS = [Path(os.path.expandvars(c)).resolve() for c in _LIMITES["carpetas_permitidas"]]


def _normalizar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


# nombres que leer_archivo nunca abre y listar_carpeta oculta (contraseñas exportadas, claves, wallets...)
PATRONES_SENSIBLES = [_normalizar(x) for x in _LIMITES["patrones_sensibles"]]
# nombres en español que el modelo suele usar para las carpetas permitidas
ALIAS = {"escritorio": "Desktop", "documentos": "Documents", "mis documentos": "Documents",
         "descargas": "Downloads", "imagenes": "Pictures", "imágenes": "Pictures", "fotos": "Pictures",
         "musica": "Music", "música": "Music", "videos": "Videos", "vídeos": "Videos"}
MAX_ELEMENTOS = 100      # listar_carpeta: más que esto llena el contexto
MAX_CARACTERES = 20000   # leer_archivo: tope duro aunque el modelo pida más
BINARIOS = {".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt", ".zip", ".rar", ".7z", ".exe", ".dll",
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".mp3", ".wav", ".flac", ".mp4", ".mkv", ".avi"}


# ---------- Ventanas ----------

PROCESOS_OCULTOS = {"asistente-ui.exe"}  # la isla (Fase 7): el agente no la ve ni la toca


def es_de_la_isla(hwnd):
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        return psutil.Process(pid).name().lower() in PROCESOS_OCULTOS
    except psutil.Error:
        return False

def _oculta_por_dwm(hwnd):
    # ventanas "cloaked": apps de la Tienda suspendidas u otros escritorios virtuales
    valor = ctypes.c_int(0)
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(valor), ctypes.sizeof(valor))
    return valor.value != 0


def _es_ventana_de_usuario(hwnd):
    if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd).strip():
        return False
    if win32gui.GetWindow(hwnd, win32con.GW_OWNER):
        return False  # diálogos y ventanas secundarias
    if win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOOLWINDOW:
        return False
    return not _oculta_por_dwm(hwnd) and win32gui.GetClassName(hwnd) != "Progman"


def listar_ventanas():
    enfocada = win32gui.GetForegroundWindow()
    ventanas = []

    def agregar(hwnd, _):
        if _es_ventana_de_usuario(hwnd) and not es_de_la_isla(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proceso = psutil.Process(pid).name()
            except psutil.Error:
                proceso = ""
            ventanas.append({"id_ventana": hwnd, "titulo": win32gui.GetWindowText(hwnd),
                             "proceso": proceso, "pid": pid, "enfocada": hwnd == enfocada})
        return True

    win32gui.EnumWindows(agregar, None)
    return ventanas


def enfocar_ventana(id_ventana: int):
    if not win32gui.IsWindow(id_ventana):
        return {"ok": False, "error": "Esa ventana ya no existe; vuelve a usar listar_ventanas."}
    if es_de_la_isla(id_ventana):
        return {"ok": False, "bloqueado": True, "error": "Esa es la isla del asistente: no la toco."}
    if win32gui.IsIconic(id_ventana):
        win32gui.ShowWindow(id_ventana, win32con.SW_RESTORE)
    # Windows solo deja traer al frente desde el hilo que tiene el foco: se enlazan las colas de entrada un momento
    actual = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[0]
    propio = ctypes.windll.kernel32.GetCurrentThreadId()
    ctypes.windll.user32.AttachThreadInput(propio, actual, True)
    try:
        win32gui.BringWindowToTop(id_ventana)
        win32gui.SetForegroundWindow(id_ventana)
    finally:
        ctypes.windll.user32.AttachThreadInput(propio, actual, False)
    return {"ok": win32gui.GetForegroundWindow() == id_ventana}


# ---------- Archivos ----------

def es_sensible(ruta):
    """True si el archivo o alguna carpeta de su ruta (dentro de la permitida) coincide con un patrón sensible."""
    base = next((c for c in CARPETAS_PERMITIDAS if ruta == c or ruta.is_relative_to(c)), None)
    partes = ruta.relative_to(base).parts if base else (ruta.name,)
    return any(fnmatch.fnmatch(_normalizar(parte), patron) for parte in partes for patron in PATRONES_SENSIBLES)


def es_titulo_sensible(titulo):
    """True si el título de una ventana nombra algo sensible. Los editores ponen el archivo antes o después del
    programa ("claves.env: Bloc de notas", "claves.kdbx - KeePass"), así que se prueba cada parte."""
    t = _normalizar(titulo).strip().lstrip("*●◐◑ ").strip()
    partes = [t] + [p.strip() for p in re.split(r"\s[-–—|:]\s|:\s", t) if p.strip()]
    return any(fnmatch.fnmatch(parte, patron) for parte in partes for patron in PATRONES_SENSIBLES)


def resolver_ruta(ruta):
    """Convierte la ruta del modelo en absoluta y comprueba que esté dentro de una carpeta permitida.
    Devuelve (Path, None) o (None, mensaje de error)."""
    texto = os.path.expandvars(os.path.expanduser(ruta.strip().strip('"')))
    p = Path(texto)
    if not p.is_absolute():
        partes = p.parts
        primera = partes[0].lower() if partes else ""
        if primera in ALIAS:
            p = Path(os.environ["USERPROFILE"], ALIAS[primera], *partes[1:])
        else:
            p = Path(os.environ["USERPROFILE"], *partes)
    p = p.resolve()  # quita '..' y sigue enlaces, para que no se pueda salir de las permitidas
    if not any(p == c or p.is_relative_to(c) for c in CARPETAS_PERMITIDAS):
        permitidas = ", ".join(str(c) for c in CARPETAS_PERMITIDAS)
        return None, f"Ruta fuera de las carpetas permitidas ({permitidas})."
    return p, None


def listar_carpeta(ruta: str, patron: str = ""):
    carpeta, error = resolver_ruta(ruta)
    if error:
        return {"ok": False, "bloqueado": True, "error": error}
    if not carpeta.is_dir():
        return {"ok": False, "error": f"No existe la carpeta {carpeta}"}
    if es_sensible(carpeta):
        return {"ok": False, "bloqueado": True,
                "error": "Esa carpeta puede tener contraseñas o claves; no la muestro por seguridad."}
    elementos = []
    for e in carpeta.iterdir():
        if patron and not fnmatch.fnmatch(e.name.lower(), patron.lower()):
            continue
        if e.name.lower() == "desktop.ini" or es_sensible(e):
            continue
        try:
            st = e.stat()
        except OSError:
            continue
        elementos.append({"nombre": e.name, "tipo": "carpeta" if e.is_dir() else "archivo",
                          "tamano_bytes": None if e.is_dir() else st.st_size,
                          "modificado": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")})
    elementos.sort(key=lambda x: x["modificado"], reverse=True)
    if len(elementos) > MAX_ELEMENTOS:
        return {"ruta": str(carpeta), "total": len(elementos), "mostrados": MAX_ELEMENTOS,
                "nota": "Son los más recientes; usa 'patron' para filtrar.", "elementos": elementos[:MAX_ELEMENTOS]}
    return elementos


def leer_archivo(ruta: str, max_caracteres: int = MAX_CARACTERES):
    archivo, error = resolver_ruta(ruta)
    if error:
        return {"ok": False, "bloqueado": True, "error": error}
    if not archivo.is_file():
        return {"ok": False, "error": f"No existe el archivo {archivo}"}
    if es_sensible(archivo):
        return {"ok": False, "bloqueado": True,
                "error": "Ese archivo puede tener contraseñas o claves; no lo leo por seguridad."}
    datos = archivo.read_bytes()
    if b"\x00" in datos[:4096]:
        return {"ok": False, "error": "Es un archivo binario (por ejemplo .docx, .pdf o una imagen); solo leo texto."}
    for codificacion in ("utf-8-sig", "cp1252", "latin-1"):  # latin-1 nunca falla
        try:
            texto = datos.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    limite = max(1, min(int(max_caracteres), MAX_CARACTERES))
    return {"ok": True, "contenido": texto[:limite], "truncado": len(texto) > limite}


# ---------- Web ----------

def url_busqueda(consulta):
    return "https://www.google.com/search?q=" + quote_plus(consulta)


def buscar_web(consulta: str):
    url = url_busqueda(consulta)
    return {"ok": webbrowser.open(url), "url": url}
