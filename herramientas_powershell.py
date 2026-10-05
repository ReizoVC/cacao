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
