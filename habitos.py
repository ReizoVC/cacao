"""
Fase 6: registro de hábitos (capa de fuentes de la wiki) en habitos.db.

Cada muestra guarda fecha y hora, app (ejecutable o AppID de la Tienda), categoría y estado (activo, inactivo,
bloqueado). NUNCA guarda títulos de ventana. Las apps privadas (gestores de contraseñas, apps de banco, Seguridad de
Windows) y las ventanas de incógnito no dejan ninguna fila: el hueco es igual que si el registrador estuviera apagado.
El único uso del título es detectar el incógnito en navegadores: se lee en memoria, se compara con una lista fija y
se descarta.

Las muestras son inmutables: solo se añaden, y se borran por antigüedad (conservar_dias) después de resumirlas en
resumen_diario, que no se borra. Lo escribe registro_habitos.py (proceso aparte, sin modelo) y lo lee la reflexión.

periodos_dudosos (desde, hasta, motivo): tramos cuyas muestras no son fiables (p. ej. todo lo anterior al
2026-10-06, cuando el estado activo/inactivo salía de GetLastInputInfo, que se reiniciaba sin entrada). No se borra
nada: el resumen diario, la actividad por hora (reflexión y sugerencias) y los días ya resumidos que se solapan con
un tramo dudoso (resumenes_dudosos) los dejan fuera.
"""
import ctypes
import json
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from ctypes import wintypes
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).parent
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
MW = CONFIG["memoria_wiki"]
RUTA = BASE / MW["habitos_db"]  # las pruebas la cambian por habitos_prueba.db
RUTA_CATEGORIAS = BASE / "apps_categorias.json"
RUTA_DATOS_LOCALES = BASE / "datos_locales.json"
FORMATO = "%Y-%m-%d %H:%M:%S"

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def normalizar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in sin_tildes if not unicodedata.combining(c)).lower().split())


# ---------- base de datos ----------

@contextmanager
def conectar():
    con = sqlite3.connect(RUTA, timeout=10)
    try:
        con.execute("PRAGMA journal_mode=WAL")  # escribe registro_habitos.py y lee el agente a la vez
        con.execute("""CREATE TABLE IF NOT EXISTS muestras (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           fecha_hora TEXT NOT NULL,
                           app TEXT NOT NULL,
                           categoria TEXT NOT NULL,
                           estado TEXT NOT NULL)""")
        con.execute("CREATE INDEX IF NOT EXISTS muestras_fecha ON muestras(fecha_hora)")
        con.execute("""CREATE TABLE IF NOT EXISTS resumen_diario (
                           dia TEXT NOT NULL,
                           app TEXT NOT NULL,
                           nombre TEXT NOT NULL,
                           categoria TEXT NOT NULL,
                           minutos REAL NOT NULL,
                           primera TEXT,
                           ultima TEXT,
                           PRIMARY KEY (dia, app))""")
        con.execute("CREATE TABLE IF NOT EXISTS dias_resumidos (dia TEXT PRIMARY KEY)")
        con.execute("""CREATE TABLE IF NOT EXISTS periodos_dudosos (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           desde TEXT NOT NULL,
                           hasta TEXT NOT NULL,
                           motivo TEXT NOT NULL,
                           marcado TEXT NOT NULL)""")
        # días que ya estaban resumidos cuando se marcó un tramo dudoso que los toca: su resumen no se usa
        con.execute("CREATE TABLE IF NOT EXISTS resumenes_dudosos (dia TEXT PRIMARY KEY, periodo INTEGER NOT NULL)")
        yield con
        con.commit()
    finally:
        con.close()


def guardar_muestra(momento, muestra):
    with conectar() as con:
        con.execute("INSERT INTO muestras (fecha_hora, app, categoria, estado) VALUES (?, ?, ?, ?)",
                    (momento.strftime(FORMATO), muestra["app"], muestra["categoria"], muestra["estado"]))


# ---------- clasificación de apps y juegos ----------

class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8)]


def _carpeta_conocida(guid_texto):
    """'{1AC14E77-...}' -> ruta de la carpeta conocida de Windows (System32, Program Files...), o None."""
    guid = GUID()
    try:
        ctypes.oledll.ole32.CLSIDFromString(guid_texto, ctypes.byref(guid))
    except OSError:
        return None
    ruta = ctypes.c_wchar_p()
    if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(ruta)) != 0:
        return None
    valor = ruta.value
    ctypes.windll.ole32.CoTaskMemFree(ruta)
    return valor


def resolver_appid(app_id):
    """Ruta de archivo de un AppID de Get-StartApps ('{GUID}\\carpeta\\x.exe' o 'D:\\...\\x.exe'), o None."""
    m = re.match(r"^(\{[0-9A-Fa-f-]{36}\})\\(.*)$", app_id)
    if m:
        carpeta = _carpeta_conocida(m.group(1))
        return str(Path(carpeta, m.group(2))) if carpeta else None
    return app_id if re.match(r"^[A-Za-z]:\\", app_id) else None


def familia_de_ruta(ruta):
    """'C:\\Program Files\\WindowsApps\\SpotifyAB.SpotifyMusic_1.2_x64__zpdn\\Spotify.exe' ->
    'spotifyab.spotifymusic_zpdn' (familia del paquete, la parte del AppID antes de '!')."""
    m = re.search(r"\\WindowsApps\\([^\\]+)\\", ruta or "", re.I)
    if not m:
        return None
    partes = m.group(1).split("_")
    return f"{partes[0]}_{partes[-1]}".lower() if len(partes) >= 3 else None


def _carpeta_demasiado_general(carpeta):
    p = Path(carpeta)
    if len(p.parts) < 3:  # 'D:\\' o 'D:\\Juegos'
        return True
    generales = {normalizar(str(Path(x))) for x in (
        "C:\\Program Files", "C:\\Program Files (x86)", "C:\\Windows", "C:\\ProgramData",
        str(Path.home()), str(Path.home() / "Desktop"), str(Path.home() / "AppData" / "Local"),
        str(Path.home() / "AppData" / "Roaming"))}
    return normalizar(str(p)) in generales or "start menu" in normalizar(str(p))


class Clasificador:
    """Nombre y categoría de una app (por ejecutable, AppID o familia de paquete) y si un proceso es un juego."""

    def __init__(self, categorias=None):
        if categorias is None:
            categorias = json.loads(RUTA_CATEGORIAS.read_text(encoding="utf-8")) if RUTA_CATEGORIAS.exists() else {}
        # lanzadores (Steam, Epic...) y programas que viven en carpetas de juegos sin serlo (Wallpaper Engine)
        self.lanzadores = {x.lower() for x in MW["lanzadores"] + MW.get("no_son_juegos", [])}
        self.carpetas_tipicas = [normalizar(x) for x in MW["carpetas_juegos"]]
        self.overrides = {k.lower(): v for k, v in MW["categorias_procesos"].items()}
        self.por_exe, self.por_aumid, self.por_familia = {}, {}, {}
        self.carpetas_juegos = set()
        for app_id, d in categorias.items():
            nombre, categoria = d["nombre"].strip(), d["categoria"]
            if "!" in app_id:
                self.por_aumid[app_id.lower()] = (nombre, categoria)
                self.por_familia.setdefault(app_id.split("!")[0].lower(), (nombre, categoria))
                continue
            ruta = resolver_appid(app_id)
            base = (ruta or app_id).replace("/", "\\").rsplit("\\", 1)[-1].lower()
            if base.endswith(".exe"):
                self.por_exe.setdefault(base, (nombre, categoria))
            if categoria == "juegos" and ruta and not self._es_lanzador(base, nombre):
                carpeta = str(Path(ruta).parent)
                if not _carpeta_demasiado_general(carpeta):
                    self.carpetas_juegos.add(normalizar(carpeta))

    def _es_lanzador(self, exe, nombre=""):
        n = normalizar(nombre)
        return exe.lower() in self.lanzadores or any(p in n for p in ("launcher", "support center", "steam"))

    def info(self, exe_ruta, aumid=None):
        """{'app', 'nombre', 'categoria'} de una ventana o proceso."""
        if aumid:
            nombre, categoria = (self.por_aumid.get(aumid.lower())
                                 or self.por_familia.get(aumid.split("!")[0].lower()) or (aumid, "otros"))
            return {"app": aumid, "nombre": nombre, "categoria": categoria}
        exe = (exe_ruta or "").replace("/", "\\").rsplit("\\", 1)[-1]
        clave = exe.lower()
        nombre, categoria = self.por_exe.get(clave, (exe.removesuffix(".exe").removesuffix(".EXE") or "?", None))
        if clave in self.overrides:
            categoria = self.overrides[clave]
        if categoria is None:
            familia = familia_de_ruta(exe_ruta)
            if familia and familia in self.por_familia:
                nombre, categoria = self.por_familia[familia]
        if categoria is None:
            categoria = "juegos" if self.es_juego(exe_ruta) else "otros"
        if categoria == "juegos" and self._es_lanzador(clave, nombre):
            categoria = "utilidades"  # Steam o Epic en la bandeja no son "jugar"
        return {"app": exe or "?", "nombre": nombre, "categoria": categoria}

    def nombre(self, app):
        if "!" in app:
            return self.info(None, app)["nombre"]
        return self.por_exe.get(app.lower(), (app.removesuffix(".exe"), None))[0]

    def es_juego(self, exe_ruta):
        """True si el ejecutable es un juego (no un lanzador): por categoría, por estar en la carpeta de un juego
        conocido o en steamapps\\common, Epic Games o XboxGames."""
        if not exe_ruta:
            return False
        ruta = normalizar(exe_ruta.replace("/", "\\"))
        exe = ruta.rsplit("\\", 1)[-1]
        if exe in self.lanzadores:
            return False
        if any(c in ruta for c in self.carpetas_tipicas):
            return True
        if self.por_exe.get(exe, (None, None))[1] == "juegos" and not self._es_lanzador(exe, self.por_exe[exe][0]):
            return True
        familia = familia_de_ruta(exe_ruta)
        if familia and self.por_familia.get(familia, (None, None))[1] == "juegos":
            return True
        return any(ruta.startswith(c + "\\") for c in self.carpetas_juegos)


# ---------- ventana al frente ----------

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
APPMODEL_ERROR_NO_APPLICATION = 15703


def aumid_de_pid(pid):
    """AppUserModelID de un proceso empaquetado (Tienda), o None."""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        largo = wintypes.UINT(0)
        if kernel32.GetApplicationUserModelId(h, ctypes.byref(largo), None) == APPMODEL_ERROR_NO_APPLICATION:
            return None
        buf = ctypes.create_unicode_buffer(largo.value)
        if kernel32.GetApplicationUserModelId(h, ctypes.byref(largo), buf) != 0:
            return None
        return buf.value
    finally:
        kernel32.CloseHandle(h)


def _pid_de(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _ruta_de_pid(pid):
    import psutil
    try:
        return psutil.Process(pid).exe()
    except (psutil.Error, OSError):
        try:
            return psutil.Process(pid).name()
        except psutil.Error:
            return None


class FuenteWindows:
    """Lo que el registrador consulta del sistema. Las pruebas usan una fuente simulada con la misma interfaz."""

    def ventana_al_frente(self):
        """{'hwnd', 'pid', 'exe_ruta', 'aumid'} o None. Para apps de la Tienda, el proceso visible es
        ApplicationFrameHost.exe: se busca la ventana hija de otro proceso, que es la app real."""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = _pid_de(hwnd)
        ruta = _ruta_de_pid(pid)
        if ruta and ruta.lower().endswith("applicationframehost.exe"):
            hijos = []
            cb = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(
                lambda h, _: hijos.append(_pid_de(h)) or True)
            user32.EnumChildWindows(hwnd, cb, 0)
            otro = next((p for p in hijos if p != pid), None)
            if otro:
                pid, ruta = otro, _ruta_de_pid(otro)
        return {"hwnd": hwnd, "pid": pid, "exe_ruta": ruta, "aumid": aumid_de_pid(pid)}

    def titulo(self, hwnd):
        largo = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(largo + 1)
        user32.GetWindowTextW(hwnd, buf, largo + 1)
        return buf.value

    def incognito_por_uia(self, hwnd, marcas):
        """Busca el indicador de incógnito (botón de perfil 'Incógnito', 'InPrivate') en la barra del navegador.
        Solo se usa si el título no lo dice, una vez por ventana (el resultado se guarda en memoria)."""
        try:
            from pywinauto import Desktop
            ventana = Desktop(backend="uia").window(handle=hwnd)
            for e in ventana.descendants(control_type="Button", depth=8):
                if any(m in normalizar(e.element_info.name) for m in marcas):
                    return True
        except Exception:
            pass
        return False

    def bloqueada(self):
        # con la sesión bloqueada, el escritorio de entrada es el de Winlogon y no se puede abrir
        h = user32.OpenInputDesktop(0, False, 0x0100)  # DESKTOP_SWITCHDESKTOP
        if not h:
            return True
        user32.CloseDesktop(h)
        return False


# ---------- privacidad ----------

def _apps_banco():
    if not RUTA_DATOS_LOCALES.exists():
        return []
    datos = json.loads(RUTA_DATOS_LOCALES.read_text(encoding="utf-8"))
    return [x for x in datos.get("apps_banco", []) if isinstance(x, str) and x.strip()]


class Privacidad:
    def __init__(self, fuente, apps_banco=None):
        self.fuente = fuente
        banco = _apps_banco() if apps_banco is None else apps_banco
        self.exes = {x.lower() for x in MW["procesos_privados"]} | {x.lower() for x in banco if "!" not in x}
        self.aumids = {x.lower() for x in MW["appids_privados"]} | {x.lower() for x in banco if "!" in x}
        self.familias = {a.split("!")[0] for a in self.aumids}
        self.navegadores = {x.lower() for x in MW["navegadores"]}
        self.marcas = [normalizar(m) for m in MW["marcas_incognito"]]
        self.usar_uia = MW.get("incognito_uia", True)
        self._incognito = {}  # hwnd -> bool: una ventana no cambia de modo

    def es_app_privada(self, ventana):
        """Gestor de contraseñas, Seguridad de Windows o app de banco (sin mirar el incógnito)."""
        exe = (ventana.get("exe_ruta") or "").replace("/", "\\").rsplit("\\", 1)[-1].lower()
        aumid = (ventana.get("aumid") or "").lower()
        return exe in self.exes or aumid in self.aumids or bool(aumid and aumid.split("!")[0] in self.familias)

    def es_privada(self, ventana):
        if self.es_app_privada(ventana):
            return True
        exe = (ventana.get("exe_ruta") or "").replace("/", "\\").rsplit("\\", 1)[-1].lower()
        if exe not in self.navegadores:
            return False
        hwnd = ventana["hwnd"]
        # el título se lee solo aquí, en memoria, y se descarta al salir de la función
        if any(m in normalizar(self.fuente.titulo(hwnd)) for m in self.marcas):
            return True
        if hwnd not in self._incognito:
            self._incognito[hwnd] = self.usar_uia and self.fuente.incognito_por_uia(hwnd, self.marcas)
        return self._incognito[hwnd]


def tomar_muestra(fuente, clasificador, privacidad, segundos_sin_entrada):
    """Muestra de este momento o None si no debe quedar fila (app privada o incógnito)."""
    if fuente.bloqueada():
        return {"app": "-", "categoria": "-", "estado": "bloqueado"}
    ventana = fuente.ventana_al_frente()
    estado = "inactivo" if segundos_sin_entrada >= MW["inactivo_min"] * 60 else "activo"
    if ventana is None:
        return {"app": "-", "categoria": "-", "estado": estado}
    if privacidad.es_privada(ventana):
        return None
    info = clasificador.info(ventana.get("exe_ruta"), ventana.get("aumid"))
    return {"app": info["app"], "categoria": info["categoria"], "estado": estado}


# ---------- resumen, purga y consultas (los usa la reflexión) ----------

def minutos_por_muestra():
    return MW["muestreo_s"] / 60


# ---------- periodos dudosos ----------

# condición SQL: la muestra no cae en ningún periodo dudoso (desde incluido, hasta excluido)
FIABLE = ("NOT EXISTS (SELECT 1 FROM periodos_dudosos p WHERE muestras.fecha_hora >= p.desde "
          "AND muestras.fecha_hora < p.hasta)")


def marcar_dudoso(desde, hasta, motivo, ahora=None):
    """Marca [desde, hasta) como dudoso (datetime o texto 'AAAA-MM-DD HH:MM:SS'). No borra nada. Devuelve
    (id del periodo, muestras que quedan dentro)."""
    texto = lambda t: t if isinstance(t, str) else t.strftime(FORMATO)  # noqa: E731
    desde, hasta = texto(desde), texto(hasta)
    with conectar() as con:
        cur = con.execute("INSERT INTO periodos_dudosos (desde, hasta, motivo, marcado) VALUES (?, ?, ?, ?)",
                          (desde, hasta, motivo, (ahora or datetime.now()).strftime(FORMATO)))
        periodo = cur.lastrowid
        con.execute("INSERT OR IGNORE INTO resumenes_dudosos SELECT dia, ? FROM dias_resumidos "
                    "WHERE dia >= substr(?, 1, 10) AND dia <= substr(?, 1, 10)", (periodo, desde, hasta))
        n = con.execute("SELECT COUNT(*) FROM muestras WHERE fecha_hora >= ? AND fecha_hora < ?",
                        (desde, hasta)).fetchone()[0]
    return periodo, n


def periodos_dudosos():
    with conectar() as con:
        return con.execute("SELECT id, desde, hasta, motivo, marcado FROM periodos_dudosos ORDER BY desde").fetchall()


def resumir_dias(hoy, clasificador):
    """Resume en resumen_diario los días cerrados (anteriores a 'hoy') que aún no estén resumidos. Las muestras de
    periodos dudosos no cuentan."""
    hecho = []
    with conectar() as con:
        ya = {d for (d,) in con.execute("SELECT dia FROM dias_resumidos")}
        dias = [d for (d,) in con.execute("SELECT DISTINCT substr(fecha_hora, 1, 10) FROM muestras "
                                          "WHERE fecha_hora < ?", (hoy.strftime("%Y-%m-%d"),))]
        for dia in sorted(set(dias) - ya):
            filas = con.execute("SELECT app, categoria, COUNT(*), MIN(fecha_hora), MAX(fecha_hora) FROM muestras "
                                "WHERE substr(fecha_hora, 1, 10) = ? AND estado = 'activo' AND app != '-' "
                                f"AND {FIABLE} GROUP BY app", (dia,)).fetchall()
            for app, categoria, n, primera, ultima in filas:
                con.execute("INSERT OR REPLACE INTO resumen_diario VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (dia, app, clasificador.nombre(app), categoria, n * minutos_por_muestra(),
                             primera[11:16], ultima[11:16]))
            con.execute("INSERT INTO dias_resumidos VALUES (?)", (dia,))
            hecho.append(dia)
    return hecho


def purgar(hoy):
    """Borra las muestras de más de conservar_dias (solo de días ya resumidos). Devuelve cuántas borró."""
    limite = (hoy - timedelta(days=MW["conservar_dias"])).strftime("%Y-%m-%d")
    with conectar() as con:
        cur = con.execute("DELETE FROM muestras WHERE fecha_hora < ? AND substr(fecha_hora, 1, 10) IN "
                          "(SELECT dia FROM dias_resumidos)", (limite,))
        return cur.rowcount


def actividad_por_hora(desde, hasta):
    """{(dia, hora, app): minutos activos} entre dos fechas (datetime, 'hasta' excluido), desde las muestras. Las de
    periodos dudosos no cuentan."""
    with conectar() as con:
        filas = con.execute("SELECT substr(fecha_hora, 1, 10), CAST(substr(fecha_hora, 12, 2) AS INTEGER), app, "
                            "COUNT(*) FROM muestras WHERE fecha_hora >= ? AND fecha_hora < ? AND estado = 'activo' "
                            f"AND app != '-' AND {FIABLE} GROUP BY 1, 2, 3",
                            (desde.strftime(FORMATO), hasta.strftime(FORMATO))).fetchall()
    return {(d, h, a): n * minutos_por_muestra() for d, h, a, n in filas}


def resumen_dias(desde, hasta):
    """Filas de resumen_diario entre dos días (datetime.date o datetime; 'hasta' excluido), sin los días que ya
    estaban resumidos cuando se marcó un periodo dudoso que los toca."""
    with conectar() as con:
        return con.execute("SELECT dia, app, nombre, categoria, minutos, primera, ultima FROM resumen_diario "
                           "WHERE dia >= ? AND dia < ? AND dia NOT IN (SELECT dia FROM resumenes_dudosos) "
                           "ORDER BY dia",
                           (desde.strftime("%Y-%m-%d"), hasta.strftime("%Y-%m-%d"))).fetchall()


def hay_datos(desde, hasta):
    """True si hay muestras fiables (fuera de periodos dudosos) entre dos fechas."""
    with conectar() as con:
        return con.execute(f"SELECT COUNT(*) FROM muestras WHERE fecha_hora >= ? AND fecha_hora < ? AND {FIABLE}",
                           (desde.strftime(FORMATO), hasta.strftime(FORMATO))).fetchone()[0] > 0


def ahora():
    return datetime.now()
