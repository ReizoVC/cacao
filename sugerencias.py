"""
Fase 6: sugerencias (diseno_fase6.md §5). Solo sugieren, nunca ejecutan: si Reizo dice "sí", su "sí" es un pedido
nuevo para el agente, con sus permisos normales.

  - Candidatas: las calcula el código desde el registro de hábitos: una app que se EMPIEZA a usar (≥ 5 min, sin uso
    en las 2 horas anteriores) en la misma hora en al menos apoyo_min de los últimos ventana_dias días. El modelo no
    inventa rutinas.
  - Se muestran solo cuando Reizo habla con el agente, en la hora de la rutina, como una línea al final de la
    respuesta: como mucho max_dia al día, con separacion_h entre una y otra, una vez al día cada una y nunca si la
    app ya está abierta.
  - Bloqueo permanente con la herramienta sugerencias(accion="bloquear"): se bloquea la última mostrada (el código
    la conoce). Ver con "listar" y quitar con "desbloquear" (por número o texto) o marcando la casilla en
    rutinas.md. El código comprueba los bloqueos antes de mostrar.
  - Ignorada ignoradas_para_pausa veces seguidas -> pausada pausa_dias días.
Tablas en memoria.db.
"""
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from rapidfuzz import fuzz

import memoria
import wiki
from wiki import normalizar

CFG = wiki.CONFIG["memoria_wiki"]["sugerencias"]
MINUTOS_PARA_CONTAR = 5   # en esa hora, para que el día cuente como apoyo
RECIENTE_MIN = 30         # "no me sugieras eso" se refiere a una sugerencia mostrada hace menos de esto
CATEGORIAS_EXCLUIDAS = {"sistema", "-", "otros"}
FMT = "%Y-%m-%d %H:%M"


@contextmanager
def _db():
    con = sqlite3.connect(memoria.RUTA)
    try:
        con.execute("""CREATE TABLE IF NOT EXISTS sugerencias (
                           clave TEXT PRIMARY KEY, app TEXT, nombre TEXT, hora INTEGER, apoyo INTEGER,
                           dias INTEGER, texto TEXT, activa INTEGER, actualizada TEXT, reactivada TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS sugerencias_mostradas (
                           id INTEGER PRIMARY KEY AUTOINCREMENT, clave TEXT, fecha_hora TEXT, resultado TEXT)""")
        con.execute("CREATE TABLE IF NOT EXISTS sugerencias_bloqueadas (clave TEXT PRIMARY KEY, texto TEXT, fecha TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS sugerencias_pausadas (clave TEXT PRIMARY KEY, texto TEXT, hasta TEXT)")
        yield con
        con.commit()
    finally:
        con.close()


def clave_de(nombre, hora):
    return f"abrir_app:{normalizar(nombre)}@{hora:02d}"


def texto_de(nombre, hora):
    return f"A esta hora ({hora:02d}:00) sueles abrir {nombre}. ¿Lo abro?"


# ---------- candidatas (desde la reflexión) ----------

def candidatas(actividad, hoy, clasificador):
    """actividad: {(dia, hora, app): minutos} de habitos.actividad_por_hora. Devuelve [{clave, app, nombre, hora,
    apoyo, dias, texto}] con apoyo >= apoyo_min en los últimos ventana_dias días."""
    desde = (hoy - timedelta(days=CFG["ventana_dias"])).strftime("%Y-%m-%d")
    dias_con_datos = {d for (d, _, _) in actividad if d >= desde}
    apoyo = {}
    for (dia, hora, app), minutos in actividad.items():
        # solo cuenta el INICIO de uso: la app no se usó en las 2 horas anteriores de ese día (si no, "a las 16
        # sueles abrir Chrome" saldría para cada hora en que Chrome sigue abierto)
        sigue = any(actividad.get((dia, hora - k, app), 0) > 0 for k in (1, 2))
        if dia >= desde and minutos >= MINUTOS_PARA_CONTAR and not sigue:
            apoyo.setdefault((app, hora), set()).add(dia)
    salida = []
    for (app, hora), dias in apoyo.items():
        info = clasificador.info(None, app) if "!" in app else clasificador.info(app)
        if len(dias) < CFG["apoyo_min"] or info["categoria"] in CATEGORIAS_EXCLUIDAS:
            continue
        salida.append({"clave": clave_de(info["nombre"], hora), "app": app, "nombre": info["nombre"], "hora": hora,
                       "apoyo": len(dias), "dias": len(dias_con_datos), "texto": texto_de(info["nombre"], hora)})
    return sorted(salida, key=lambda c: (c["hora"], -c["apoyo"]))


def actualizar(lista, ahora):
    """Guarda las candidatas de la última reflexión; las que ya no aparecen quedan inactivas ('ya no se ve')."""
    with _db() as con:
        con.execute("UPDATE sugerencias SET activa = 0")
        for c in lista:
            con.execute("""INSERT INTO sugerencias (clave, app, nombre, hora, apoyo, dias, texto, activa, actualizada)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                           ON CONFLICT(clave) DO UPDATE SET app=excluded.app, nombre=excluded.nombre,
                           apoyo=excluded.apoyo, dias=excluded.dias, texto=excluded.texto, activa=1,
                           actualizada=excluded.actualizada""",
                        (c["clave"], c["app"], c["nombre"], c["hora"], c["apoyo"], c["dias"], c["texto"],
                         ahora.strftime(FMT)))


def activas():
    with _db() as con:
        return [dict(zip(("clave", "app", "nombre", "hora", "apoyo", "dias", "texto"), f)) for f in
                con.execute("SELECT clave, app, nombre, hora, apoyo, dias, texto FROM sugerencias WHERE activa = 1 "
                            "ORDER BY hora")]


# ---------- mostrar ----------

def bloqueadas():
    with _db() as con:
        return [{"clave": c, "texto": t, "fecha": f} for c, t, f in
                con.execute("SELECT clave, texto, fecha FROM sugerencias_bloqueadas ORDER BY fecha")]


def pausadas(ahora):
    with _db() as con:
        return [{"clave": c, "texto": t, "hasta": h} for c, t, h in
                con.execute("SELECT clave, texto, hasta FROM sugerencias_pausadas WHERE hasta > ? ORDER BY hasta",
                            (ahora.strftime(FMT),))]


def elegir(ahora, en_marcha=lambda app: False):
    """La sugerencia para mostrar ahora, o None. Todas las reglas las aplica el código."""
    hoy = ahora.strftime("%Y-%m-%d")
    with _db() as con:
        hoy_mostradas = con.execute("SELECT clave, fecha_hora FROM sugerencias_mostradas WHERE fecha_hora >= ? "
                                    "ORDER BY fecha_hora", (hoy,)).fetchall()
        fuera = {c for (c,) in con.execute("SELECT clave FROM sugerencias_bloqueadas")}
        fuera |= {c for (c,) in con.execute("SELECT clave FROM sugerencias_pausadas WHERE hasta > ?",
                                            (ahora.strftime(FMT),))}
        filas = con.execute("SELECT clave, app, nombre, texto, hora FROM sugerencias WHERE activa = 1 AND hora = ? "
                            "ORDER BY apoyo DESC", (ahora.hour,)).fetchall()
    if len(hoy_mostradas) >= CFG["max_dia"]:
        return None
    if hoy_mostradas and ahora - datetime.strptime(hoy_mostradas[-1][1], FMT) < timedelta(hours=CFG["separacion_h"]):
        return None
    ya_hoy = {c for c, _ in hoy_mostradas}
    for clave, app, nombre, texto, hora in filas:
        if clave in fuera or clave in ya_hoy or en_marcha(app):
            continue
        return {"clave": clave, "app": app, "nombre": nombre, "texto": texto, "hora": hora}
    return None


def registrar_mostrada(clave, ahora):
    with _db() as con:
        return con.execute("INSERT INTO sugerencias_mostradas (clave, fecha_hora) VALUES (?, ?)",
                           (clave, ahora.strftime(FMT))).lastrowid


def ultima_mostrada(ahora):
    with _db() as con:
        fila = con.execute("SELECT m.id, m.clave, m.fecha_hora, s.texto, s.nombre FROM sugerencias_mostradas m "
                           "LEFT JOIN sugerencias s ON s.clave = m.clave ORDER BY m.id DESC LIMIT 1").fetchone()
    if not fila or ahora - datetime.strptime(fila[2], FMT) > timedelta(minutes=RECIENTE_MIN):
        return None
    return {"id": fila[0], "clave": fila[1], "texto": fila[3] or fila[1], "nombre": fila[4]}


def registrar_resultado(id_mostrada, resultado, ahora):
    """resultado: 'aceptada', 'ignorada' o 'bloqueada'. Tras ignoradas_para_pausa ignoradas seguidas, pausa."""
    with _db() as con:
        con.execute("UPDATE sugerencias_mostradas SET resultado = ? WHERE id = ? AND resultado IS NULL",
                    (resultado, id_mostrada))
        clave = con.execute("SELECT clave FROM sugerencias_mostradas WHERE id = ?", (id_mostrada,)).fetchone()
        if not clave or resultado != "ignorada":
            return None
        clave = clave[0]
        reactivada = (con.execute("SELECT reactivada FROM sugerencias WHERE clave = ?", (clave,)).fetchone()
                      or [None])[0] or ""
        ultimos = [r for (r,) in con.execute(
            "SELECT resultado FROM sugerencias_mostradas WHERE clave = ? AND resultado IS NOT NULL AND fecha_hora > ? "
            "ORDER BY id DESC LIMIT ?", (clave, reactivada, CFG["ignoradas_para_pausa"]))]
        if len(ultimos) == CFG["ignoradas_para_pausa"] and all(r == "ignorada" for r in ultimos):
            texto = (con.execute("SELECT texto FROM sugerencias WHERE clave = ?", (clave,)).fetchone() or [clave])[0]
            hasta = ahora + timedelta(days=CFG["pausa_dias"])
            con.execute("INSERT OR REPLACE INTO sugerencias_pausadas VALUES (?, ?, ?)", (clave, texto, hasta.strftime(FMT)))
            return hasta
    return None


# ---------- bloquear, listar, desbloquear ----------

def _desbloquear(clave, ahora):
    with _db() as con:
        n = con.execute("DELETE FROM sugerencias_bloqueadas WHERE clave = ?", (clave,)).rowcount
        n += con.execute("DELETE FROM sugerencias_pausadas WHERE clave = ?", (clave,)).rowcount
        con.execute("UPDATE sugerencias SET reactivada = ? WHERE clave = ?", (ahora.strftime(FMT), clave))
    return n > 0


def herramienta(accion, numero=None, texto=None, ahora=None):
    """Implementación de la herramienta 'sugerencias' del agente."""
    ahora = ahora or datetime.now()
    if accion == "bloquear":
        ultima = ultima_mostrada(ahora)
        if not ultima:
            return {"ok": False, "error": "No te mostré ninguna sugerencia en los últimos 30 minutos; dime cuál "
                                          "quieres bloquear o pide la lista."}
        with _db() as con:
            con.execute("INSERT OR REPLACE INTO sugerencias_bloqueadas VALUES (?, ?, ?)",
                        (ultima["clave"], ultima["texto"], ahora.strftime(FMT)))
        registrar_resultado(ultima["id"], "bloqueada", ahora)
        wiki.anotar("sugerencia_bloqueada", ultima["clave"], ahora)
        return {"ok": True, "bloqueada": ultima["texto"], "nota": "No volveré a sugerirlo."}
    if accion == "listar":
        lista = [{"clave": b["clave"], "texto": b["texto"], "estado": f"bloqueada desde {b['fecha'][:10]}"}
                 for b in bloqueadas()]
        lista += [{"clave": p["clave"], "texto": p["texto"], "estado": f"pausada hasta {p['hasta'][:10]}"}
                  for p in pausadas(ahora)]
        wiki.fijar_estado("ultima_lista_sugerencias", [x["clave"] for x in lista])
        if not lista:
            return {"sugerencias": [], "nota": "No hay sugerencias bloqueadas ni pausadas."}
        return {"sugerencias": [{"numero": i, "texto": x["texto"], "estado": x["estado"]}
                                for i, x in enumerate(lista, 1)]}
    if accion == "desbloquear":
        candidatas_ = bloqueadas() + pausadas(ahora)
        if numero is not None:
            lista = wiki.estado("ultima_lista_sugerencias", [])
            if not 1 <= int(numero) <= len(lista):
                return {"ok": False, "error": "Ese número no está en la última lista; usa accion 'listar'."}
            clave = lista[int(numero) - 1]
        elif texto:
            q = normalizar(texto)
            puntos = [(max(fuzz.partial_ratio(q, normalizar(c["texto"])), fuzz.partial_ratio(q, normalizar(c["clave"]))),
                       c) for c in candidatas_]
            buenas = [c for p, c in puntos if p >= 75]
            if len(buenas) != 1:
                return {"ok": False, "error": "No sé cuál es; pregunta a Reizo o usa accion 'listar'.",
                        "coincidencias": [c["texto"] for c in (buenas or candidatas_)][:5]}
            clave = buenas[0]["clave"]
        else:
            return {"ok": False, "error": "Indica 'numero' (de la lista) o 'texto'."}
        texto_c = next((c["texto"] for c in candidatas_ if c["clave"] == clave), clave)
        if not _desbloquear(clave, ahora):
            return {"ok": False, "error": "Esa sugerencia ya no estaba bloqueada."}
        wiki.anotar("sugerencia_desbloqueada", clave, ahora)
        return {"ok": True, "desbloqueada": texto_c}
    return {"ok": False, "error": "accion debe ser 'bloquear', 'listar' o 'desbloquear'."}


# ---------- secciones de rutinas.md ----------

RE_CASILLA = re.compile(r"^- \[[xX]\] (?:Desbloquear|Reactivar): (.*?) · ", re.M)


def seccion_activas():
    lineas = [f"- {s['texto']} (apoyo {s['apoyo']} de {s['dias']} días)" for s in activas()]
    return "\n".join(lineas) if lineas else "(Ninguna por ahora.)"


def seccion_bloqueadas(ahora):
    lineas = [f"- [ ] Desbloquear: {b['texto']} · bloqueada {b['fecha'][:10]}" for b in bloqueadas()]
    lineas += [f"- [ ] Reactivar: {p['texto']} · pausada hasta {p['hasta'][:10]}" for p in pausadas(ahora)]
    if not lineas:
        return "(Ninguna.)"
    return "Marca una casilla para desbloquearla; se aplica al iniciar el agente o en la siguiente reflexión.\n" + \
        "\n".join(lineas)


def aplicar_casillas(ahora):
    """Desbloquea las sugerencias cuya casilla marcó Reizo en rutinas.md y vuelve a escribir la sección.
    Solo lee esa sección, sin modelo. Devuelve los textos desbloqueados."""
    pagina = wiki.leer("rutinas")
    if not pagina or "sugerencias_bloqueadas" not in pagina["secciones"]:
        return []
    marcadas = RE_CASILLA.findall(pagina["secciones"]["sugerencias_bloqueadas"]["texto"])
    hechas = []
    for texto in marcadas:
        for c in bloqueadas() + pausadas(ahora):
            if c["texto"].strip() == texto.strip() and _desbloquear(c["clave"], ahora):
                wiki.anotar("sugerencia_desbloqueada", f"{c['clave']} (casilla en rutinas.md)", ahora)
                hechas.append(c["texto"])
    if hechas:
        try:
            wiki.escribir("rutinas", {"sugerencias_bloqueadas": seccion_bloqueadas(ahora)}, ahora=ahora)
        except wiki.Pospuesto:
            pass  # la sección se rehace más tarde; el desbloqueo ya está hecho
    return hechas
