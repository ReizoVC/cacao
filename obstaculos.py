"""
Obstáculos por app y acción, en memoria.db (tabla obstaculos), gestionados SOLO por el código.

Cuando un atajo o un clic no tiene efecto visible (herramientas_grupo4.hubo_efecto: ni ventana nueva, ni cambio de
título, de ventana al frente, de foco o de portapapeles), el ejecutor lo anota en la tarea. Si la tarea termina
bien y, después del fallo, otra acción en la MISMA app sí tuvo efecto, se guarda:
    (app, acción que falló) -> alternativa (otro atajo, o la secuencia de controles pulsados)
La próxima vez, antes de enviar ese atajo en esa app:
  - si la alternativa es un atajo, se envía directamente ese (y se avisa a Reizo);
  - si es una secuencia de controles (menú), se le dice al modelo que use ese camino.
No se alimenta de contenido externo: lo escribe el ejecutor con lo que observó (proceso, teclas enviadas, nombres de
los controles pulsados), nunca el modelo, y no se escribe nada si en la tarea entró texto de archivos, de la web
o de PowerShell. Los nombres de controles se recortan y se limpian.
"""
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import memoria

ORDEN_MODIFICADORES = ("ctrl", "alt", "shift", "win")
MAX_TEXTO = 80


@contextmanager
def _conectar():
    con = sqlite3.connect(memoria.RUTA)  # memoria.RUTA: las pruebas la cambian por una base temporal
    try:
        con.execute("""CREATE TABLE IF NOT EXISTS obstaculos (
                           app TEXT NOT NULL,
                           accion TEXT NOT NULL,
                           fallos INTEGER NOT NULL DEFAULT 0,
                           alternativa TEXT,
                           tipo_alternativa TEXT,
                           usos_alternativa INTEGER NOT NULL DEFAULT 0,
                           primera TEXT NOT NULL,
                           ultima TEXT NOT NULL,
                           PRIMARY KEY (app, accion))""")
        yield con
        con.commit()
    finally:
        con.close()


def nombre_atajo(teclas):
    """['S', 'Control'] -> 'ctrl+s' (modificadores primero, en orden fijo)."""
    import herramientas_grupo4 as g4
    nombres = [g4._canonica(t) for t in teclas or []]
    mods = [m for m in ORDEN_MODIFICADORES if m in nombres]
    resto = [n for n in nombres if n not in ORDEN_MODIFICADORES]
    return "+".join(mods + resto)


def teclas_de(atajo):
    return atajo.split("+")


def limpiar(texto):
    texto = re.sub(r"[\r\n\t]+", " ", str(texto or "")).strip()
    return texto[:MAX_TEXTO]


def registrar_fallo(app, accion, ahora=None):
    t = (ahora or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    with _conectar() as con:
        con.execute("INSERT INTO obstaculos (app, accion, fallos, primera, ultima) VALUES (?, ?, 1, ?, ?) "
                    "ON CONFLICT(app, accion) DO UPDATE SET fallos = fallos + 1, ultima = excluded.ultima",
                    (app, accion, t, t))


def registrar_alternativa(app, accion, alternativa, tipo, ahora=None):
    """tipo: 'atajo' (alternativa = 'ctrl+g') o 'controles' (alternativa = 'Archivo > Guardar')."""
    if tipo not in ("atajo", "controles"):
        raise ValueError(tipo)
    t = (ahora or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    with _conectar() as con:
        con.execute("INSERT INTO obstaculos (app, accion, fallos, alternativa, tipo_alternativa, primera, ultima) "
                    "VALUES (?, ?, 1, ?, ?, ?, ?) ON CONFLICT(app, accion) DO UPDATE SET "
                    "alternativa = excluded.alternativa, tipo_alternativa = excluded.tipo_alternativa, "
                    "ultima = excluded.ultima", (app, accion, limpiar(alternativa), tipo, t, t))


def olvidar(app, accion):
    """La alternativa guardada no funcionó al usarla: se olvida (la fila y sus fallos se quedan) para aprender otra."""
    with _conectar() as con:
        con.execute("UPDATE obstaculos SET alternativa = NULL, tipo_alternativa = NULL WHERE app = ? AND accion = ?",
                    (app, accion))


def contar_uso(app, accion):
    with _conectar() as con:
        con.execute("UPDATE obstaculos SET usos_alternativa = usos_alternativa + 1 WHERE app = ? AND accion = ?",
                    (app, accion))


def consultar(app, accion):
    """{'fallos', 'alternativa', 'tipo'} si hay un camino conocido para esa acción en esa app; si no, None."""
    with _conectar() as con:
        fila = con.execute("SELECT fallos, alternativa, tipo_alternativa FROM obstaculos WHERE app = ? AND accion = ? "
                           "AND alternativa IS NOT NULL", (app, accion)).fetchone()
    return {"fallos": fila[0], "alternativa": fila[1], "tipo": fila[2]} if fila else None


def listar():
    with _conectar() as con:
        return con.execute("SELECT app, accion, fallos, alternativa, tipo_alternativa, usos_alternativa, ultima "
                           "FROM obstaculos ORDER BY ultima DESC").fetchall()


def resolver(intentos, externo):
    """Al terminar una tarea con éxito. intentos: [{'app', 'accion', 'tipo' ('atajo'|'tecla'|'control'), 'efecto'}]
    en orden. Para cada atajo sin efecto mira lo que vino JUSTO después en la misma app:
      - se mira el tramo hasta la primera tecla suelta (el Esc con que se cierra el diálogo no cuenta) y la ÚLTIMA
        acción con efecto de ese tramo es la que funcionó;
      - si es un atajo -> alternativa 'atajo' (p. ej. Ctrl+G);
      - si es un clic -> la ruta de clics con efecto que llevó a él -> 'controles' (p. ej. "Archivo > Guardar").
    Las teclas sueltas (Esc, Enter...) nunca son alternativa. Devuelve [(app, accion, alternativa, tipo)] guardadas.
    Con contenido externo en la tarea no guarda nada."""
    if externo:
        return []
    guardadas = []
    for i, fallo in enumerate(intentos):
        if fallo["efecto"] or fallo["tipo"] != "atajo":
            continue
        # lo que vino después en la misma app, hasta la primera tecla suelta (el Esc que cierra el diálogo)
        tramo = []
        for x in intentos[i + 1:]:
            if x["app"] != fallo["app"]:
                continue
            if x["tipo"] == "tecla":
                break
            tramo.append(x)
        efectivos = [x for x in tramo if x["efecto"]]
        if not efectivos:
            continue
        ultimo = efectivos[-1]  # lo que por fin funcionó
        if ultimo["tipo"] == "atajo":
            if ultimo["accion"] == fallo["accion"]:
                continue
            alternativa = (ultimo["accion"], "atajo")
        else:
            # la ruta de clics con efecto que llevó a él (desde el último atajo del tramo)
            desde = max((k for k, x in enumerate(tramo) if x["tipo"] == "atajo"), default=-1) + 1
            clics = [limpiar(x["accion"]) for x in tramo[desde:] if x["tipo"] == "control" and x["efecto"]]
            alternativa = (" > ".join(clics[-4:]), "controles")
        registrar_alternativa(fallo["app"], fallo["accion"], *alternativa)
        guardadas.append((fallo["app"], fallo["accion"], *alternativa))
    return guardadas
