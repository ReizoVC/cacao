"""
Fase 6: la wiki de memoria (vault de Obsidian en C:\\asistente\\memoria, con su propio git local).

El código manda (diseno_fase6.md §7):
  - páginas y secciones fijas (wiki_esquema.json), delimitadas por marcadores <!-- seccion:id ... -->;
  - el frontmatter, las fechas, index.md y log.md los escribe solo el código;
  - el modelo solo aporta frases sueltas para las secciones de autor 'modelo', que el código limpia (sin
    encabezados, marcadores ni enlaces rotos), filtra (patrones sensibles, secretos, apps privadas) y pone en viñetas;
  - se reemplaza la sección entera, por escritura atómica (temporal + os.replace) y sin tocar nada fuera de los
    marcadores.
Tus ediciones ganan (§4.4 y §11): una sección cuyo texto no coincide con el hash de lo último que escribió el código
la editaste tú; queda congelada hasta que la vacíes. Antes de escribir se pospone si el archivo cambió hace menos de
5 min o si es la pestaña activa de Obsidian, y se aborta si cambia justo antes de reemplazarlo.
Texto de Reizo: secciones 'Notas de Reizo', secciones editadas y páginas de mis_notas/. fuentes/ es contenido
externo y nada de aquí lo lee. Estado (hashes, mtimes) en memoria.db.
"""
import fnmatch
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from rapidfuzz import fuzz

import memoria

BASE = Path(__file__).parent
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
ESQUEMA = json.loads((BASE / "wiki_esquema.json").read_text(encoding="utf-8"))
LIMITES = ESQUEMA["limites"]
PAGINAS = {p["id"]: p for p in ESQUEMA["paginas"]}
VAULT = BASE / CONFIG["memoria_wiki"]["vault"]  # las pruebas la cambian por memoria_prueba/
MIS_NOTAS, FUENTES = "mis_notas", "fuentes"
TEXTO_NOTAS = "(Escribe aquí. El agente nunca toca esta sección y la reflexión lo toma como verdad.)"
TEXTO_VACIO = "(Todavía sin datos.)"
AUTOR_ASISTENTE = ["-c", "user.name=Asistente", "-c", "user.email=asistente@local"]
RE_SECCION = re.compile(r"<!-- seccion:(?P<id>\w+)(?P<meta>[^>]*?)-->\n?(?P<texto>.*?)\n?<!-- /seccion -->", re.S)
RE_ENLACE = re.compile(r"\[\[([^\]|#]+)(#[^\]|]*)?(?:\|([^\]]+))?\]\]")
_LIMITES_SEG = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))["limites"]


class Pospuesto(Exception):
    """No se escribió para no pisar a Reizo; se reintenta más tarde."""


def normalizar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in sin_tildes if not unicodedata.combining(c)).lower().split())


def _hash(texto):
    limpio = "\n".join(l.rstrip() for l in (texto or "").replace("\r\n", "\n").strip().split("\n"))
    return hashlib.sha1(limpio.encode("utf-8")).hexdigest()


def ruta(pagina):
    return VAULT / f"{pagina}.md"


# ---------- estado en memoria.db ----------

@contextmanager
def _db():
    con = sqlite3.connect(memoria.RUTA)
    try:
        con.execute("""CREATE TABLE IF NOT EXISTS wiki_secciones (
                           pagina TEXT NOT NULL, seccion TEXT NOT NULL,
                           hash TEXT NOT NULL,            -- de lo último que escribió el código
                           hash_visto TEXT,               -- última versión de Reizo ya anotada en log.md
                           congelada INTEGER NOT NULL DEFAULT 0,
                           fecha TEXT, PRIMARY KEY (pagina, seccion))""")
        con.execute("CREATE TABLE IF NOT EXISTS wiki_archivos (ruta TEXT PRIMARY KEY, mtime REAL, hash TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS wiki_estado (clave TEXT PRIMARY KEY, valor TEXT)")
        yield con
        con.commit()
    finally:
        con.close()


def estado(clave, defecto=None):
    with _db() as con:
        fila = con.execute("SELECT valor FROM wiki_estado WHERE clave = ?", (clave,)).fetchone()
    return json.loads(fila[0]) if fila else defecto


def fijar_estado(clave, valor):
    with _db() as con:
        con.execute("INSERT OR REPLACE INTO wiki_estado VALUES (?, ?)", (clave, json.dumps(valor, ensure_ascii=False)))


def _registrar_archivo(p):
    with _db() as con:
        con.execute("INSERT OR REPLACE INTO wiki_archivos VALUES (?, ?, ?)",
                    (str(p.relative_to(VAULT)), p.stat().st_mtime, _hash(p.read_text(encoding="utf-8"))))


# ---------- formato de las páginas ----------

def _frontmatter(texto):
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    if not m:
        return {}, texto
    datos = {}
    for linea in m.group(1).split("\n"):
        if ":" in linea:
            k, v = linea.split(":", 1)
            datos[k.strip()] = v.strip()
    return datos, texto[m.end():]


def _linea_fm(valor):
    return " ".join(str(valor).replace("---", "–").split())


def _render_frontmatter(datos):
    return "---\n" + "".join(f"{k}: {_linea_fm(v)}\n" for k, v in datos.items()) + "---\n"


def leer(pagina):
    """{'frontmatter', 'secciones': {id: {'texto', 'meta'}}, 'raw'} o None si no existe."""
    p = ruta(pagina)
    if not p.exists():
        return None
    raw = p.read_text(encoding="utf-8").replace("\r\n", "\n")
    fm, _ = _frontmatter(raw)
    secciones = {m.group("id"): {"texto": m.group("texto").strip(), "meta": m.group("meta").strip()}
                 for m in RE_SECCION.finditer(raw)}
    return {"frontmatter": fm, "secciones": secciones, "raw": raw}


def _meta(seccion, ahora=None):
    meta = f"autor:{seccion['autor']}"
    if ahora is not None and seccion["autor"] != "reizo":
        meta += f" actualizado:{ahora:%Y-%m-%d}"
    return meta


def _texto_inicial(seccion):
    return TEXTO_NOTAS if seccion["autor"] == "reizo" else TEXTO_VACIO


def _crear_pagina(pagina, ahora):
    esquema = PAGINAS[pagina]
    fm = {"pagina": pagina, "resumen": esquema["resumen_inicial"], "actualizado": f"{ahora:%Y-%m-%d %H:%M}",
          "fuentes": "[]"}
    partes = [_render_frontmatter(fm), f"# {esquema['titulo']}\n"]
    for s in esquema["secciones"]:
        partes.append(f"\n## {s['titulo']}\n<!-- seccion:{s['id']} {_meta(s, ahora)} -->\n{_texto_inicial(s)}\n"
                      "<!-- /seccion -->\n")
    p = ruta(pagina)
    _escribir_atomico(p, "".join(partes))
    with _db() as con:
        for s in esquema["secciones"]:
            con.execute("INSERT OR REPLACE INTO wiki_secciones (pagina, seccion, hash, congelada, fecha) "
                        "VALUES (?, ?, ?, 0, ?)", (pagina, s["id"], _hash(_texto_inicial(s)), f"{ahora:%Y-%m-%d %H:%M}"))
    _registrar_archivo(p)


def _escribir_atomico(p, texto):
    tmp = p.with_name(f".~{p.name}.tmp")
    tmp.write_text(texto, encoding="utf-8", newline="\n")
    os.replace(tmp, p)


# ---------- texto del modelo: limpieza y filtros ----------

def _nombres_validos():
    nombres = set(PAGINAS)
    carpeta = VAULT / MIS_NOTAS
    if carpeta.exists():
        nombres |= {f.stem for f in carpeta.rglob("*.md")}
    return {normalizar(n) for n in nombres}


def limpiar_frase(frase, validos=None):
    """Una frase del modelo -> una línea limpia, o '' si no queda nada. Quita viñetas, encabezados, marcadores,
    bloques de código y saltos de línea; los [[enlaces]] a páginas que no existen pasan a texto."""
    validos = _nombres_validos() if validos is None else validos
    t = " ".join(str(frase).replace("<!--", " ").replace("-->", " ").replace("```", " ").split())
    t = re.sub(r"^(?:[-*•]+|\d+[.)]|#+|>)\s*", "", t).strip().strip('"').strip()
    t = re.sub(r"(?<!\S)#+\s", "", t).replace("---", "–")

    def enlace(m):
        destino = m.group(1).strip()
        if normalizar(destino) in validos:
            return m.group(0)
        return m.group(3) or destino

    t = RE_ENLACE.sub(enlace, t)
    if len(t) > LIMITES["frase_max"]:
        t = t[:LIMITES["frase_max"] - 1].rsplit(" ", 1)[0] + "…"
    return t


def _patrones_palabra():
    """Patrones sensibles de herramientas.json como expresiones de palabra completa (con plurales):
    '*token*' bloquea 'token' y 'tokens' pero no 'tokenizer'; '*.env' bloquea 'x.env'."""
    regex = []
    for patron in _LIMITES_SEG["patrones_sensibles"]:
        p = normalizar(patron)
        if p.startswith("*.") or p.startswith(".env"):
            regex.append(r"\S*" + re.escape(p.lstrip("*")).replace(r"\*", r"\S*") + r"\b")
        elif p.endswith("*") and not p.startswith("*"):  # id_rsa*
            regex.append(r"\b" + re.escape(p[:-1]) + r"\S*")
        else:
            partes = [re.escape(x[:-1]) + "s?" if x.endswith("s") else re.escape(x) for x in p.strip("*").split("*")]
            regex.append(r"\b" + r"\W?\w{0,12}\W?".join(partes) + r"(?:s|es)?\b")
    return re.compile("|".join(regex))


_SENSIBLE = _patrones_palabra()
_SECRETO = re.compile(r"\b[0-9a-fA-F]{32,}\b|\b[A-Za-z0-9+/_-]{40,}={0,2}|\bsk-[A-Za-z0-9_-]{16,}|\bghp_\w{20,}|"
                      r"\bAKIA[0-9A-Z]{16}\b|-----BEGIN")


def _apps_privadas():
    mw = CONFIG["memoria_wiki"]
    nombres = [x.rsplit(".", 1)[0] for x in mw["procesos_privados"]]
    locales = BASE / "datos_locales.json"
    if locales.exists():
        nombres += [x.split("!")[0].rsplit(".", 1)[0] for x in
                    json.loads(locales.read_text(encoding="utf-8")).get("apps_banco", [])]
    nombres += ["Seguridad de Windows", "Windows Security"]
    return [normalizar(n) for n in nombres if len(n) >= 3]


def motivo_sensible(texto):
    """Por qué no puede ir a la wiki (patrón sensible, posible secreto o app privada), o None."""
    n = normalizar(texto)
    m = _SENSIBLE.search(n)
    if m:
        return f"patrón sensible ({m.group(0)})"
    if _SECRETO.search(texto):
        return "posible secreto"
    for app in _apps_privadas():
        if re.search(r"\b" + re.escape(app) + r"\b", n):
            return "app privada"
    return None


def preparar_frases(frases, maximo=None):
    """Limpia y filtra las frases del modelo. Devuelve (frases aceptadas, [(frase, motivo)] descartadas)."""
    validos = _nombres_validos()
    aceptadas, descartadas = [], []
    for f in frases:
        limpia = limpiar_frase(f, validos)
        if not limpia:
            continue
        motivo = motivo_sensible(limpia)
        if motivo:
            descartadas.append((limpia, motivo))
        elif normalizar(limpia) not in {normalizar(a) for a in aceptadas}:
            aceptadas.append(limpia)
    return aceptadas[:maximo or LIMITES["frases_max"]], descartadas


def viñetas(frases):
    return "\n".join(f"- {f}" for f in frases) if frases else TEXTO_VACIO


# ---------- Obsidian: no pisar a Reizo ----------

def obsidian_abierto():
    import psutil
    return any((p.info["name"] or "").lower() == "obsidian.exe" for p in psutil.process_iter(["name"]))


def archivo_activo_obsidian():
    """Ruta (relativa al vault) de la pestaña activa de Obsidian, si Obsidian está abierto; si no, None.
    Solo lee .obsidian/workspace.json."""
    ws = VAULT / ".obsidian" / "workspace.json"
    if not ws.exists() or not obsidian_abierto():
        return None
    try:
        datos = json.loads(ws.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    activo = datos.get("active")

    def buscar(nodo):
        if isinstance(nodo, dict):
            if nodo.get("id") == activo and nodo.get("type") == "leaf":
                return (nodo.get("state") or {}).get("state", {}).get("file")
            for v in nodo.values():
                r = buscar(v)
                if r:
                    return r
        elif isinstance(nodo, list):
            for v in nodo:
                r = buscar(v)
                if r:
                    return r
        return None

    return buscar(datos)


def motivo_para_posponer(p):
    if p.exists():
        with _db() as con:
            fila = con.execute("SELECT mtime FROM wiki_archivos WHERE ruta = ?",
                               (str(p.relative_to(VAULT)),)).fetchone()
        mtime = p.stat().st_mtime
        propio = fila and abs(fila[0] - mtime) < 0.001
        if not propio and time.time() - mtime < LIMITES["posponer_si_editado_hace_s"]:
            return "editado hace menos de 5 min"
    activo = archivo_activo_obsidian()
    if activo and Path(activo).as_posix() == p.relative_to(VAULT).as_posix():
        return "abierto en Obsidian"
    return None


# ---------- ediciones de Reizo ----------

def es_texto_reizo_vacio(texto):
    t = (texto or "").strip()
    return not t or t in (TEXTO_NOTAS, TEXTO_VACIO)


def detectar_ediciones(ahora=None):
    """Recorre las páginas: congela las secciones que editó Reizo, descongela las que vació y anota en log.md
    cada edición nueva una sola vez. Devuelve [(pagina, seccion)] congeladas."""
    congeladas, nuevas = [], []
    with _db() as con:
        guardadas = {(p, s): (h, v, c) for p, s, h, v, c in
                     con.execute("SELECT pagina, seccion, hash, hash_visto, congelada FROM wiki_secciones")}
        for pid, esquema in PAGINAS.items():
            pagina = leer(pid)
            if not pagina:
                continue
            for s in esquema["secciones"]:
                if s["autor"] == "reizo" or s["id"] == "sugerencias_bloqueadas" or s["id"] not in pagina["secciones"]:
                    continue  # las notas siempre son de Reizo; en la de bloqueadas solo cuentan las casillas
                texto = pagina["secciones"][s["id"]]["texto"]
                h_codigo, h_visto, congelada = guardadas.get((pid, s["id"]), (None, None, 0))
                h = _hash(texto)
                if congelada and es_texto_reizo_vacio(texto):
                    con.execute("UPDATE wiki_secciones SET congelada = 0, hash = ?, hash_visto = NULL "
                                "WHERE pagina = ? AND seccion = ?", (h, pid, s["id"]))
                    nuevas.append(("descongelada", pid, s["id"]))
                elif h_codigo is not None and h != h_codigo:
                    if not congelada or h != h_visto:
                        con.execute("UPDATE wiki_secciones SET congelada = 1, hash_visto = ? "
                                    "WHERE pagina = ? AND seccion = ?", (h, pid, s["id"]))
                        nuevas.append(("edicion_reizo", pid, s["id"]))
                    congeladas.append((pid, s["id"]))
    for tipo, pid, sid in nuevas:
        detalle = (f"{pid}#{sid} (se respeta, no se sobrescribe)" if tipo == "edicion_reizo"
                   else f"{pid}#{sid} (vaciada: vuelve a escribirla el asistente)")
        anotar(tipo, detalle, ahora)
    return congeladas


def congeladas():
    with _db() as con:
        return {(p, s) for p, s in con.execute("SELECT pagina, seccion FROM wiki_secciones WHERE congelada = 1")}


def texto_reizo():
    """Todo el texto de Reizo: [{'origen', 'pagina', 'texto', 'mtime'}]. Notas, secciones editadas por él y
    páginas de mis_notas/. Nunca fuentes/."""
    trozos = []
    fijas = congeladas()
    for pid, esquema in PAGINAS.items():
        pagina = leer(pid)
        if not pagina:
            continue
        mtime = ruta(pid).stat().st_mtime
        for s in esquema["secciones"]:
            texto = pagina["secciones"].get(s["id"], {}).get("texto", "")
            if es_texto_reizo_vacio(texto):
                continue
            if s["autor"] == "reizo":
                trozos.append({"origen": f"{pid}#{s['id']}", "pagina": pid, "texto": texto, "mtime": mtime})
            elif (pid, s["id"]) in fijas:
                trozos.append({"origen": f"{pid}#{s['id']} (editada por Reizo)", "pagina": pid, "texto": texto,
                               "mtime": mtime})
    carpeta = VAULT / MIS_NOTAS
    if carpeta.exists():
        for f in sorted(carpeta.rglob("*.md")):
            texto = _frontmatter(f.read_text(encoding="utf-8").replace("\r\n", "\n"))[1].strip()
            if texto:
                trozos.append({"origen": f"{MIS_NOTAS}/{f.relative_to(carpeta).as_posix()}", "pagina": None,
                               "texto": texto, "mtime": f.stat().st_mtime})
    return trozos


def paginas_sueltas():
    """Páginas .md del vault que no son del esquema ni están en mis_notas/ o fuentes/."""
    propias = {f"{p}.md" for p in PAGINAS} | {"index.md", "log.md"}
    sueltas = []
    for f in VAULT.rglob("*.md"):
        rel = f.relative_to(VAULT).as_posix()
        if rel.startswith((f"{MIS_NOTAS}/", f"{FUENTES}/", ".obsidian/", ".git/")) or rel in propias:
            continue
        sueltas.append(rel)
    return sorted(sueltas)


# ---------- escritura ----------

def escribir(pagina, secciones=None, frontmatter=None, ahora=None):
    """Reemplaza el texto de las secciones dadas ({id: texto}) y actualiza el frontmatter. Las congeladas (editadas
    por Reizo) y las de autor 'reizo' no se tocan. Devuelve {'escritas', 'congeladas'}; lanza Pospuesto si no es
    buen momento para escribir el archivo."""
    ahora = ahora or datetime.now()
    secciones = secciones or {}
    p = ruta(pagina)
    if not p.exists():
        _crear_pagina(pagina, ahora)
    motivo = motivo_para_posponer(p)
    if motivo:
        raise Pospuesto(f"{pagina}.md: {motivo}")
    detectar_ediciones(ahora)
    fijas = congeladas()
    esquema = {s["id"]: s for s in PAGINAS[pagina]["secciones"]}
    original = p.read_text(encoding="utf-8").replace("\r\n", "\n")
    texto = original
    escritas, saltadas = [], []
    for sid, nuevo in secciones.items():
        s = esquema[sid]
        if s["autor"] == "reizo" or (pagina, sid) in fijas:
            saltadas.append(sid)
            continue
        patron = re.compile(r"(<!-- seccion:" + sid + r")[^>]*?-->\n?.*?\n?<!-- /seccion -->", re.S)
        if not patron.search(texto):
            saltadas.append(sid)  # Reizo borró los marcadores: no se adivina dónde iba (lo anota el lint)
            continue
        bloque = f"<!-- seccion:{sid} {_meta(s, ahora)} -->\n{nuevo.strip()}\n<!-- /seccion -->"
        texto = patron.sub(lambda _: bloque, texto, count=1)
        escritas.append(sid)
    if frontmatter:
        fm, cuerpo = _frontmatter(texto)
        fm.update({k: v for k, v in frontmatter.items() if v is not None})
        texto = _render_frontmatter(fm) + cuerpo
    if texto != original:
        if p.read_text(encoding="utf-8").replace("\r\n", "\n") != original:
            raise Pospuesto(f"{pagina}.md cambió mientras se preparaba")
        _escribir_atomico(p, texto)
        _registrar_archivo(p)
        with _db() as con:
            for sid in escritas:
                h = _hash(leer(pagina)["secciones"][sid]["texto"])
                con.execute("INSERT OR REPLACE INTO wiki_secciones (pagina, seccion, hash, hash_visto, congelada, fecha)"
                            " VALUES (?, ?, ?, NULL, 0, ?)", (pagina, sid, h, f"{ahora:%Y-%m-%d %H:%M}"))
    return {"escritas": escritas, "congeladas": saltadas}


def resumen_de(pagina):
    p = leer(pagina)
    return (p or {}).get("frontmatter", {}).get("resumen") or PAGINAS[pagina]["resumen_inicial"]


def indice_texto():
    """Catálogo para el prompt y para index.md: una línea por página, con tope de indice_max caracteres."""
    lineas = []
    for pid, esquema in PAGINAS.items():
        resumen = resumen_de(pid)[:LIMITES["resumen_max"]]
        lineas.append(f"- [[{pid}]] {esquema['titulo']}: {resumen}")
    texto, total = [], 0
    for l in lineas:
        if total + len(l) + 1 > LIMITES["indice_max"]:
            break
        texto.append(l)
        total += len(l) + 1
    n = len(list((VAULT / MIS_NOTAS).rglob("*.md"))) if (VAULT / MIS_NOTAS).exists() else 0
    extra = f"- {MIS_NOTAS}/: {n} notas de Reizo"
    if n and total + len(extra) <= LIMITES["indice_max"]:
        texto.append(extra)
    return "\n".join(texto)


def escribir_indice(ahora=None):
    ahora = ahora or datetime.now()
    p = VAULT / "index.md"
    if p.exists():
        motivo = motivo_para_posponer(p)
        if motivo:
            raise Pospuesto(f"index.md: {motivo}")
    _escribir_atomico(p, _render_frontmatter({"actualizado": f"{ahora:%Y-%m-%d %H:%M}"}) +
                      "# Índice\n\nGenerado por el asistente; no lo edites (se reescribe).\n\n" + indice_texto() + "\n")
    _registrar_archivo(p)


def anotar(tipo, detalle, ahora=None):
    """Añade una línea a log.md: '## [AAAA-MM-DD HH:MM] tipo | detalle'. Solo añade, nunca reescribe."""
    ahora = ahora or datetime.now()
    p = VAULT / "log.md"
    nuevo = not p.exists()
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        if nuevo:
            f.write("# Registro\n\nLo escribe solo el asistente, añadiendo al final.\n\n")
        f.write(f"## [{ahora:%Y-%m-%d %H:%M}] {tipo} | {' '.join(str(detalle).split())}\n\n")
    _registrar_archivo(p)


# ---------- búsqueda (consultar_memoria) ----------

def buscar(consulta, limite=None):
    """Secciones de la wiki y páginas de mis_notas/ que mejor coinciden. Nunca fuentes/, index ni log."""
    limite = limite or LIMITES["consulta_max_caracteres"]
    if not VAULT.exists() or not consulta.strip():
        return []
    q = normalizar(consulta)
    candidatos = []
    fijas = congeladas()
    for pid, esquema in PAGINAS.items():
        if pid == "revision":
            continue
        pagina = leer(pid)
        if not pagina:
            continue
        for s in esquema["secciones"]:
            texto = pagina["secciones"].get(s["id"], {}).get("texto", "")
            if es_texto_reizo_vacio(texto):
                continue
            puntaje = fuzz.token_set_ratio(q, normalizar(f"{esquema['titulo']} {s['titulo']} {texto}"))
            candidatos.append((puntaje, {"pagina": pid, "seccion": s["titulo"], "texto": texto,
                                         "nota_de_reizo": s["autor"] == "reizo" or (pid, s["id"]) in fijas}))
    for nota in texto_reizo():
        if nota["pagina"] is None:
            puntaje = fuzz.token_set_ratio(q, normalizar(f"{nota['origen']} {nota['texto']}"))
            candidatos.append((puntaje, {"pagina": nota["origen"], "seccion": "", "texto": nota["texto"],
                                         "nota_de_reizo": True}))
    elegidos, total = [], 0
    for puntaje, c in sorted(candidatos, key=lambda x: -x[0]):
        if puntaje < 50 or len(elegidos) >= 2:
            break
        c = {**c, "texto": c["texto"][:limite - total]}
        if not c["texto"]:
            break
        elegidos.append(c)
        total += len(c["texto"])
    return elegidos


# ---------- git del vault ----------

def git(*args, autor=None):
    cmd = ["git", *(AUTOR_ASISTENTE if autor == "asistente" else []), "-C", str(VAULT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          creationflags=subprocess.CREATE_NO_WINDOW)


def asegurar_vault(ahora=None):
    """Crea el vault (carpetas, páginas del esquema, índice, log y repositorio git) si falta algo."""
    ahora = ahora or datetime.now()
    for carpeta in (VAULT, VAULT / MIS_NOTAS, VAULT / FUENTES):
        carpeta.mkdir(parents=True, exist_ok=True)
    for carpeta, texto in ((MIS_NOTAS, "Tus páginas: la reflexión las toma como verdad. El asistente nunca escribe "
                                       "aquí."),
                           (FUENTES, "Contenido externo (Web Clipper, etc.): nada del asistente lo lee.")):
        leeme = VAULT / carpeta / "LEEME.txt"
        if not leeme.exists():
            leeme.write_text(texto + "\n", encoding="utf-8")
    ignorar = VAULT / ".gitignore"
    if not ignorar.exists():
        ignorar.write_text(".obsidian/\n*.tmp\n", encoding="utf-8")
    nuevas = [pid for pid in PAGINAS if not ruta(pid).exists()]
    for pid in nuevas:
        _crear_pagina(pid, ahora)
    if not (VAULT / "index.md").exists():
        escribir_indice(ahora)
    if not (VAULT / "log.md").exists():
        anotar("inicio", "wiki creada", ahora)
    if not (VAULT / ".git").exists():
        git("init", "-q")
        git("add", "-A")
        git("commit", "-q", "-m", "Inicio de la wiki", autor="asistente")
    return nuevas


def guardar_ediciones_reizo():
    """Antes de escribir: lo que está sin commit y no coincide con lo último que escribió el código es de Reizo."""
    estado_git = git("status", "--porcelain", "-uall").stdout
    if not estado_git.strip():
        return []
    with _db() as con:
        propios = {r: h for r, h in con.execute("SELECT ruta, hash FROM wiki_archivos")}
    de_reizo, del_asistente = [], []
    for linea in estado_git.splitlines():
        rel = linea[3:].strip().strip('"')
        p = VAULT / rel
        if p.exists() and p.is_file() and propios.get(rel) == _hash(p.read_text(encoding="utf-8", errors="replace")):
            del_asistente.append(rel)
        else:
            de_reizo.append(rel)
    if del_asistente:
        git("add", "--", *del_asistente)
        git("commit", "-q", "-m", "Cambios pendientes del asistente", autor="asistente")
    if de_reizo:
        git("add", "-A", "--", *de_reizo)
        r = git("commit", "-q", "-m", "Ediciones de Reizo")
        if r.returncode != 0:  # sin identidad de git configurada
            git("-c", "user.name=Reizo", "-c", "user.email=reizo@local", "commit", "-q", "-m", "Ediciones de Reizo")
    return de_reizo


def commit(mensaje):
    git("add", "-A")
    if git("diff", "--cached", "--quiet").returncode != 0:
        git("commit", "-q", "-m", mensaje, autor="asistente")
        return True
    return False
