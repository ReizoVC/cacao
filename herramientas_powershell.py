"""
ejecutar_powershell: último recurso cuando ninguna otra herramienta sirve. Permiso "confirmar" (herramientas.json):
el ejecutor muestra el motivo y el comando y espera un sí explícito antes de llamar a esta función.

Antes de ejecutar, planificar_powershell() bloquea:
  - los patrones de limites.powershell_patrones_bloqueados (sin mayúsculas, como palabra completa: "del" bloquea
    "del x.txt" pero no "Delete" ni "model");
  - comandos que nombran archivos sensibles (limites.patrones_sensibles, p. ej. un CSV de contraseñas o un .env);
  - comandos de más de LARGO_MAXIMO caracteres.
La ejecución tiene el tiempo máximo de limites.timeout_powershell_seg; el atajo de emergencia la corta.
OJO: los patrones son una red de seguridad, no un sandbox (un alias raro o un script ofuscado podrían pasar);
la confirmación del usuario sigue siendo la barrera principal.
"""
import fnmatch
import json
import re
import subprocess
import time
from pathlib import Path

from herramientas_grupo1 import PATRONES_SENSIBLES, _normalizar

CATALOGO = json.loads((Path(__file__).parent / "herramientas.json").read_text(encoding="utf-8"))
LIMITES = CATALOGO["limites"]
PATRONES_BLOQUEADOS = LIMITES["powershell_patrones_bloqueados"]
TIMEOUT_S = LIMITES["timeout_powershell_seg"]
LARGO_MAXIMO = 2000
MAX_SALIDA = 4000  # caracteres de salida que vuelven al modelo
comprobar_emergencia = lambda: None  # noqa: E731  (agente_minimo.py la conecta al atajo de emergencia)


def _patron_regex(patron):
    p = patron.strip().lower()
    inicio = r"(?<![\w-])" if p[0].isalnum() or p[0] == "-" else ""
    fin = r"(?![\w-])" if p[-1].isalnum() else ""
    return re.compile(inicio + re.escape(p) + fin)


REGEX_BLOQUEADOS = [(p, _patron_regex(p)) for p in PATRONES_BLOQUEADOS]


def nombra_archivo_sensible(comando):
    """True si alguna palabra del comando (o el último tramo de una ruta) coincide con un patrón sensible."""
    for token in re.findall(r"[^\s'\"`;|(){}<>,]+", comando):
        nombre = _normalizar(re.split(r"[\\/]", token)[-1])
        if nombre and any(fnmatch.fnmatch(nombre, p) for p in PATRONES_SENSIBLES):
            return True
    # nombres con espacios entre comillas ("Mis contraseñas.csv")
    for entre_comillas in re.findall(r"[\"']([^\"']+)[\"']", comando):
        nombre = _normalizar(re.split(r"[\\/]", entre_comillas)[-1])
        if any(fnmatch.fnmatch(nombre, p) for p in PATRONES_SENSIBLES):
            return True
    return False


# Consultas que escriben archivos: si el comando solo lee (sus cmdlets son de lectura: Get-, Select-, Where-...),
# no tiene por qué guardar nada en disco. Se rechaza la salida a archivo (Out-File, Set-Content, Add-Content,
# Tee-Object, Export-*, y las redirecciones > y >>) y el modelo puede repetirlo sin ella. Si el comando ya modifica
# algo (New-Item, Copy-Item...) o solo escribe un texto fijo ("hola" > x.txt), escribir es la tarea y decide el sí.
SALIDAS_A_ARCHIVO = {"out-file", "set-content", "add-content", "tee-object", "sc", "ac", "tee"}
VERBOS_LECTURA = {"get", "select", "where", "sort", "measure", "format", "group", "test", "resolve", "find",
                  "search", "compare", "convertto", "convertfrom", "foreach", "write", "join", "split", "out",
                  "show", "read", "trace", "debug", "wait", "use", "limit", "skip"}
# > y >> a un archivo (también 1>, 2>, *>), no la fusión de flujos (2>&1) ni el descarte (> $null)
RE_REDIRECCION = re.compile(r"(?:\d|\*)?>>?(?!&)\s*(?!\$null\b)(\S+)", re.I)


def _sin_cadenas(comando):
    return re.sub(r"'[^']*'|\"(?:`.|[^\"`])*\"", "''", comando)


def _cabezas(codigo):
    """Primera palabra de cada tramo del comando (tras inicio, |, ;, (, { o $( ), sin las redirecciones."""
    sin_redir = RE_REDIRECCION.sub(" ", codigo)
    return [t.split()[0].lower() for t in re.split(r"[|;({]|\$\(", sin_redir) if t.split()]


def escribe_en_consulta(comando):
    """Si el comando solo consulta y aun así escribe en un archivo, devuelve qué lo escribe; si no, None.
    Consulta: cada tramo empieza por un cmdlet de lectura (Get-, Select-...), un alias o una variable. Si algún
    tramo es un cmdlet que modifica (New-Item, Copy-Item...) o todo es texto fijo ('hola' > x.txt), escribir es
    la tarea y no se considera consulta."""
    codigo = _sin_cadenas(comando)
    cabezas = _cabezas(codigo)
    salidas = [c for c in cabezas if c in SALIDAS_A_ARCHIVO or c.startswith("export-")]
    redirecciones = [m.group(0).strip() for m in RE_REDIRECCION.finditer(codigo)]
    if not salidas and not redirecciones:
        return None
    resto = [c for c in cabezas if c not in SALIDAS_A_ARCHIVO and not c.startswith("export-")]
    lectura = []
    for c in resto:
        if c in ("''",) or re.fullmatch(r"[\d.]+", c):
            continue  # texto o número fijo
        verbo = c.split("-")[0] if re.fullmatch(r"[a-z]+-[a-z0-9]+", c) else None
        if verbo is not None and verbo not in VERBOS_LECTURA:
            return None  # el comando ya modifica algo: escribir puede ser parte de la tarea
        lectura.append(c)
    if not lectura:
        return None  # solo texto fijo: guardar es la tarea
    nombres = {"sc": "Set-Content", "ac": "Add-Content", "tee": "Tee-Object"}
    return ", ".join(dict.fromkeys(nombres.get(s, s.title()) for s in salidas)) or redirecciones[0]


def planificar_powershell(comando, motivo=""):
    """Devuelve (plan, None) o (None, resultado de error/bloqueo). No ejecuta nada."""
    comando = (comando or "").strip()
    if not comando:
        return None, {"ok": False, "error": "Falta el comando."}
    if not (motivo or "").strip():
        return None, {"ok": False, "error": "Falta el motivo: explica en una frase qué hace y por qué."}
    if len(comando) > LARGO_MAXIMO:
        return None, {"ok": False, "error": f"El comando es demasiado largo (más de {LARGO_MAXIMO} caracteres)."}
    texto = comando.lower()
    for patron, regex in REGEX_BLOQUEADOS:
        if regex.search(texto):
            return None, {"ok": False, "bloqueado": True,
                          "error": f"El comando usa «{patron.strip()}», que está bloqueado por seguridad."}
    if nombra_archivo_sensible(comando):
        return None, {"ok": False, "bloqueado": True,
                      "error": "El comando nombra un archivo que parece tener contraseñas o claves; no lo ejecuto."}
    escritura = escribe_en_consulta(comando)
    if escritura:  # sin "bloqueado": no corta la tarea, el modelo puede repetirlo sin guardar nada
        return None, {"ok": False, "error": f"Es una consulta y no debe escribir archivos ({escritura}). Repite el "
                                            "comando sin guardar en un archivo: su salida ya te llega."}
    return {"comando": comando, "motivo": motivo.strip(), "timeout_s": TIMEOUT_S}, None


def ejecutar_powershell(comando: str, motivo: str = ""):
    plan, error = planificar_powershell(comando, motivo)
    if error:
        return error
    # salida en UTF-8 para que las tildes lleguen bien; sin perfil y sin preguntas interactivas
    script = "[Console]::OutputEncoding = [Text.Encoding]::UTF8; $ProgressPreference = 'SilentlyContinue'; " \
             + plan["comando"]
    proceso = subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    limite = time.monotonic() + plan["timeout_s"]
    try:
        while proceso.poll() is None:
            comprobar_emergencia()  # lanza Detenido si se pulsó el atajo
            if time.monotonic() > limite:
                proceso.kill()
                proceso.communicate()
                return {"ok": False, "error": f"El comando superó el tiempo máximo ({plan['timeout_s']} s) y lo detuve."}
            time.sleep(0.05)
    except BaseException:
        proceso.kill()
        proceso.communicate()
        raise
    salida, errores = proceso.communicate()
    salida = salida.decode("utf-8", "replace").strip()
    errores = errores.decode("utf-8", "replace").strip()
    resultado = {"ok": proceso.returncode == 0 and not errores, "codigo_salida": proceso.returncode,
                 "salida": salida[:MAX_SALIDA] + ("…" if len(salida) > MAX_SALIDA else "")}
    if errores:
        resultado["error"] = errores[:1000]
    return resultado
