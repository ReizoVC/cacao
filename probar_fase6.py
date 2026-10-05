"""
Pruebas de la Fase 6 SIN modelo (o con un modelo falso que devuelve JSON fijo). Usan bases y vault temporales
(habitos_prueba.db, memoria_prueba.db, memoria_prueba/), que se borran al terminar; no tocan memoria.db, habitos.db
ni la wiki real, no abren apps ni leen archivos de Reizo.
Uso: .venv\\Scripts\\python probar_fase6.py [seccion ...]   (sin argumentos, todas)
"""
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from datetime import datetime, timedelta

import deteccion
import entrada
import habitos
import memoria
import simular_habitos as sim
import wiki

BASE = habitos.BASE
HOY = datetime(2026, 10, 5, 10, 0)  # lunes: los 7 días simulados van del lunes 28 al domingo 4
resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


def bases_temporales():
    habitos.RUTA = BASE / "habitos_prueba.db"
    habitos.RUTA.unlink(missing_ok=True)


def wiki_temporal():
    import shutil
    import stat

    def quitar_solo_lectura(func, ruta, _):  # los objetos de .git son de solo lectura
        os.chmod(ruta, stat.S_IWRITE)
        func(ruta)

    memoria.RUTA = BASE / "memoria_prueba.db"
    memoria.RUTA.unlink(missing_ok=True)
    wiki.VAULT = BASE / "memoria_prueba"
    if wiki.VAULT.exists():
        shutil.rmtree(wiki.VAULT, onerror=quitar_solo_lectura)
    wiki.obsidian_abierto = lambda: False


def envejecer(p, segundos=600):
    """Simula que Reizo editó el archivo hace 'segundos' (así no se pospone por 'editado hace poco')."""
    t = time.time() - segundos
    os.utime(p, (t, t))


# ---------- 1. registro de hábitos ----------

def prueba_entrada():
    quieto = {"botones": set(), "ejes": {"x": 0.50, "y": 0.50}, "hat": 8}
    ok("mando: primer informe no es actividad", not entrada.hay_cambio(None, quieto))
    ok("mando: ruido pequeño en ejes no es actividad",
       not entrada.hay_cambio(quieto, {**quieto, "ejes": {"x": 0.55, "y": 0.47}}))
    ok("mando: botón pulsado es actividad", entrada.hay_cambio(quieto, {**quieto, "botones": {(9, 1)}}))
    ok("mando: stick movido es actividad", entrada.hay_cambio(quieto, {**quieto, "ejes": {"x": 0.9, "y": 0.5}}))
    ok("mando: cruceta (hat) es actividad", entrada.hay_cambio(quieto, {**quieto, "hat": 2}))
    g = entrada.XINPUT_GAMEPAD(0, 0, 0, 300, -250, 0, 0)
    g2 = entrada.XINPUT_GAMEPAD(0, 0, 0, 6000, -250, 0, 0)
    ok("xinput: deriva de 300 no es actividad",
       not entrada.hay_cambio(entrada._estado_xinput(entrada.XINPUT_GAMEPAD()), entrada._estado_xinput(g)))
    ok("xinput: stick a 6000 es actividad", entrada.hay_cambio(entrada._estado_xinput(g), entrada._estado_xinput(g2)))
    m = entrada.MonitorEntrada().iniciar()
    import time
    time.sleep(0.6)
    s = m.segundos_sin_entrada()
    ok("monitor real: arranca y mide (solo lectura)", isinstance(s, float) and s >= 0 and m.rawinput_ok,
       f"xinput={m.xinput_ok} rawinput={m.rawinput_ok}")
    m.cerrar()


def prueba_clasificador():
    c = habitos.Clasificador(sim.CATEGORIAS_SIM)
    ok("clasificador: VS Code -> desarrollo", c.info(sim.V["code"][0])["categoria"] == "desarrollo")
    ok("clasificador: WhatsApp de la Tienda por AppID -> comunicación",
       c.info(sim.V["whatsapp"][0], sim.V["whatsapp"][1])["categoria"] == "comunicación")
    ok("clasificador: Steam es lanzador, no juego", c.info(sim.V["steam"][0])["categoria"] == "utilidades"
       and not c.es_juego(sim.V["steam"][0]))
    ok("clasificador: juego en steamapps\\common", c.es_juego(sim.V["hades"][0])
       and c.info(sim.V["hades"][0])["categoria"] == "juegos")
    ok("clasificador: ejecutable desconocido -> otros", c.info("C:\\x\\raro.exe")["categoria"] == "otros")
    real = habitos.Clasificador()
    steam = [k for k, v in real.por_exe.items() if k in ("steam.exe", "epicgameslauncher.exe")]
    ok("clasificador real: carpetas de juegos y lanzadores fuera",
       real.carpetas_juegos and not any(real.es_juego(f"C:\\x\\{k}") for k in steam),
       f"{len(real.carpetas_juegos)} carpetas de juegos")


def prueba_privacidad():
    f = sim.FuenteSimulada()
    p = habitos.Privacidad(f, apps_banco=sim.APPS_BANCO_SIM)

    def privada(clave):
        f.actual = clave
        return p.es_privada(f.ventana_al_frente())

    ok("privado: gestor de contraseñas", privada("keepass"))
    ok("privado: app de banco (datos_locales)", privada("banco"))
    ok("privado: incógnito por título", privada("incognito_titulo"))
    ok("privado: incógnito por botón de perfil (UIA)", privada("incognito_uia"))
    ok("privado: Seguridad de Windows por AppID",
       p.es_privada({"hwnd": 1, "exe_ruta": "C:\\x\\SecHealthUI.exe",
                     "aumid": "Microsoft.SecHealthUI_8wekyb3d8bbwe!SecHealthUI"}))
    ok("no privado: Chrome normal, VS Code, Bloc de notas",
       not privada("chrome") and not privada("code") and not privada("notas_sensible"))


def prueba_simulacion():
    bases_temporales()
    r = sim.simular(HOY, dias=7, semilla=11)
    with habitos.conectar() as con:
        columnas = {c[1] for c in con.execute("PRAGMA table_info(muestras)")}
        filas = con.execute("SELECT fecha_hora, app, categoria, estado FROM muestras").fetchall()
    texto = " ".join(" ".join(f) for f in filas).lower()
    ok("simulación: muestras guardadas", len(filas) > 5000, f"{len(filas)} muestras")
    ok("sin columna de título", not any("titul" in c for c in columnas), str(sorted(columnas)))
    ok("trampas fuera de la base (títulos, privados, incógnito)",
       not any(t.lower() in texto for t in sim.TEXTOS_TRAMPA + ["keepass.exe", "mibanco.exe"]))
    ok("privados e incógnito sin fila: 8 muestras por día", r["omitidas_privadas"] == 8 * 7,
       f"{r['omitidas_privadas']} omitidas")
    ok("sesión bloqueada registrada como 'bloqueado'", any(f[3] == "bloqueado" for f in filas))
    hechos = habitos.resumir_dias(HOY, r["clasificador"])
    ok("resumen: 7 días cerrados", len(hechos) == 7, ", ".join(hechos))
    ok("resumen: idempotente", habitos.resumir_dias(HOY, r["clasificador"]) == [])
    filas = habitos.resumen_dias(HOY - timedelta(days=7), HOY)
    code = [f for f in filas if f[2] == "Visual Studio Code" and f[0] == "2026-09-29"]
    hades = sorted({f[0] for f in filas if f[2] == "Hades"})
    ok("resumen: VS Code un martes > 3 h", code and code[0][4] > 180, f"{code[0][4] if code else 0:.0f} min")
    ok("resumen: Hades solo viernes y sábado", hades == ["2026-10-02", "2026-10-03"], str(hades))
    borradas = habitos.purgar(HOY + timedelta(days=40))
    ok("purga: muestras de más de 30 días", borradas > 5000,
       f"{borradas} borradas")
    ok("purga: el resumen diario se queda", len(habitos.resumen_dias(HOY - timedelta(days=7), HOY)) == len(filas))


def prueba_fuente_real():
    f = habitos.FuenteWindows()
    v = f.ventana_al_frente()
    ok("fuente real: ventana al frente y sesión (solo lectura, no se imprime nada)",
       (v is None or {"hwnd", "pid", "exe_ruta", "aumid"} <= set(v)) and isinstance(f.bloqueada(), bool))


# ---------- 2. condiciones de la reflexión ----------

class RelojFalso:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.t += s


class SistemaFalso:
    """idle: segundos sin entrada al empezar; crece con el reloj salvo que haya 'entrada_en' (instante de una tecla)."""

    def __init__(self, reloj, idle=900, pantalla=False, procesos=(), audio=(), gpu=5, entrada_en=None):
        self.reloj, self.idle0, self.pantalla, self.procesos = reloj, idle, pantalla, list(procesos)
        self.audio_fijo, self.gpu, self.entrada_en = (audio if callable(audio) else list(audio)), gpu, entrada_en

    def segundos_sin_entrada(self):
        t = self.reloj()
        if self.entrada_en is not None and t >= self.entrada_en:
            return t - self.entrada_en
        return self.idle0 + t

    def pantalla_completa(self):
        return self.pantalla

    def ejecutables(self):
        return self.procesos

    def audio(self):
        return self.audio_fijo(self.reloj()) if callable(self.audio_fijo) else self.audio_fijo

    def uso_gpu(self):
        return self.gpu


STEAM_BANDEJA = [r"C:\Program Files (x86)\Steam\steam.exe", r"C:\Program Files (x86)\Steam\bin\cef\steamwebhelper.exe",
                 r"C:\Windows\explorer.exe"]
VLC = (r"C:\Program Files\VideoLAN\VLC\vlc.exe", None, 0.3)
SPOTIFY = (sim.V["spotify"][0], None, 0.4)
CHROME = (sim.V["chrome"][0], None, 0.4)
DISCORD = (r"C:\Users\sim\AppData\Local\Discord\app-1\Discord.exe", None, 0.2)


def prueba_condiciones():
    c = habitos.Clasificador(sim.CATEGORIAS_SIM)

    def motivo(**kw):
        r = RelojFalso()
        v = deteccion.Vigilante(SistemaFalso(r, **kw), c, habitos.MW, reloj=r, dormir=r.dormir)
        return v.motivo_para_no_empezar()

    ok("arranca: todo tranquilo con Steam en la bandeja", motivo(procesos=STEAM_BANDEJA) is None)
    ok("no arranca: actividad hace 5 min", motivo(idle=300) == "actividad reciente")
    ok("no arranca: pantalla completa", motivo(pantalla=True) == "pantalla completa")
    ok("no arranca: juego en marcha (aunque no esté al frente)",
       (motivo(procesos=STEAM_BANDEJA + [sim.V["hades"][0]]) or "").startswith("juego abierto"))
    ok("arranca: suena música (Spotify)", motivo(audio=[SPOTIFY]) is None)
    ok("arranca: suena el navegador sin pantalla completa", motivo(audio=[CHROME]) is None)
    ok("no arranca: suena un video (VLC)", (motivo(audio=[VLC]) or "").startswith("audio"))
    ok("no arranca: suena una llamada (comunicación)", (motivo(audio=[DISCORD]) or "").startswith("audio"))
    ok("arranca: un pitido de video de 1 s no cuenta",
       motivo(audio=lambda t: [VLC] if 3 <= t < 4 else []) is None)
    ok("no arranca: GPU ocupada", (motivo(gpu=60) or "").startswith("GPU"))
    ok("no arranca: tocas el mando mientras mide", motivo(entrada_en=12) == "actividad reciente")


def prueba_guardia():
    import threading
    import time
    c = habitos.Clasificador(sim.CATEGORIAS_SIM)
    casos = [("teclado o mando", dict(entrada_en=0.3), "actividad"),
             ("pantalla completa", dict(), "pantalla completa"),
             ("juego que se abre", dict(), "juego abierto"),
             ("video que empieza", dict(), "audio")]
    for nombre, kw, esperado in casos:
        inicio = time.monotonic()
        reloj = lambda: time.monotonic() - inicio  # noqa: E731
        s = SistemaFalso(reloj, **kw)
        if nombre == "pantalla completa":
            threading.Timer(0.3, lambda: setattr(s, "pantalla", True)).start()
        if nombre == "juego que se abre":
            threading.Timer(0.3, lambda: s.procesos.append(sim.V["hades"][0])).start()
        if nombre == "video que empieza":
            s.audio_fijo = lambda t: [VLC] if t >= 0.3 else []
        v = deteccion.Vigilante(s, c, {"reflexion": {**habitos.MW["reflexion"], "audio_min_s": 0.3}}, reloj=reloj)
        parar = threading.Event()
        with deteccion.Guardia(v, parar, intervalo_s=0.05, cada_procesos_s=0.1) as g:
            parar.wait(3)
        demora = time.monotonic() - inicio
        ok(f"guardia: se detiene por {nombre}", parar.is_set() and esperado in (g.motivo or ""),
           f"{g.motivo}, {demora:.2f} s desde el inicio")
    s = SistemaFalso(lambda: 0.0)
    parar = threading.Event()
    with deteccion.Guardia(deteccion.Vigilante(s, c, habitos.MW), parar, intervalo_s=0.05) as g:
        parar.wait(0.5)
    ok("guardia: sin motivos no para", not parar.is_set())


def prueba_sistema_real():
    s = deteccion.SistemaWindows(entrada.MonitorEntrada())
    pc, ex, au, gpu = s.pantalla_completa(), s.ejecutables(), s.audio(), s.uso_gpu()
    ok("sistema real: consultas de solo lectura", isinstance(pc, bool) and len(ex) > 10 and isinstance(au, list),
       f"pantalla_completa={pc}, {len(ex)} procesos, {len(au)} sesiones de audio activas, GPU {gpu} %")
    v = deteccion.Vigilante(s, habitos.Clasificador(), habitos.MW)
    juego = v.juego_abierto()
    ok("sistema real: ningún proceso abierto ahora cuenta como juego (Steam/Epic en la bandeja no)", juego is None,
       "hay uno" if juego else "")


# ---------- 3. núcleo de la wiki ----------

def prueba_wiki():
    wiki_temporal()
    creadas = wiki.asegurar_vault(HOY)
    v = wiki.VAULT
    ok("vault: páginas del esquema, índice, log, carpetas y git", set(creadas) == set(wiki.PAGINAS)
       and all((v / x).exists() for x in ("index.md", "log.md", "mis_notas", "fuentes", ".git", ".gitignore")))
    ok("vault: .obsidian fuera de git", ".obsidian/" in (v / ".gitignore").read_text(encoding="utf-8"))
    frases, descartadas = wiki.preparar_frases(
        ["- Entre semana empieza con VS Code a las 9 (5 de 5 días).", "## Juega los viernes [[apps]]",
         "Guarda sus contraseñas en KeePass", "Mira [[inexistente|esto]] <!-- seccion:x -->",
         "Entre semana empieza con VS Code a las 9 (5 de 5 días)."] + [f"Frase {i}" for i in range(10)])
    ok("frases: limpias, sin duplicados y como máximo 8", len(frases) == 8 and frases[0].startswith("Entre semana")
       and frases[1] == "Juega los viernes [[apps]]" and "inexistente" not in frases[2] and "<!--" not in frases[2],
       str(frases[:3]))
    ok("frases: lo sensible se descarta con motivo", len(descartadas) == 1 and "patrón" in descartadas[0][1])
    r = wiki.escribir("habitos", {"patrones": wiki.viñetas(frases[:2])},
                      {"resumen": "Mañanas de VS Code.", "fuentes": "[habitos.db]"}, HOY)
    pagina = wiki.leer("habitos")
    ok("escribir: sección reemplazada y frontmatter del código", r["escritas"] == ["patrones"]
       and pagina["secciones"]["patrones"]["texto"].startswith("- Entre semana")
       and pagina["frontmatter"]["resumen"] == "Mañanas de VS Code."
       and "actualizado:2026-10-05" in pagina["secciones"]["patrones"]["meta"])
    ok("escribir: atómico, sin temporales", not list(v.glob(".~*")))

    # Reizo edita una sección del modelo y escribe fuera de los marcadores
    p = wiki.ruta("habitos")
    p.write_text(p.read_text(encoding="utf-8").replace("- Juega los viernes", "- Los viernes juego con amigos")
                 + "\nTexto mío fuera de las secciones.\n", encoding="utf-8")
    envejecer(p)
    r = wiki.escribir("habitos", {"patrones": "- otra cosa", "cambios": "- Sin semana anterior."}, ahora=HOY)
    texto = p.read_text(encoding="utf-8")
    ok("edición de Reizo: la sección queda congelada y no se sobrescribe", r["congeladas"] == ["patrones"]
       and "Los viernes juego con amigos" in texto and "otra cosa" not in texto, str(r))
    ok("edición de Reizo: el texto fuera de las secciones se conserva", "Texto mío fuera de las secciones." in texto)
    wiki.detectar_ediciones(HOY)
    ok("edición de Reizo: anotada en log.md una sola vez",
       (v / "log.md").read_text(encoding="utf-8").count("edicion_reizo | habitos#patrones") == 1)
    trozos = wiki.texto_reizo()
    ok("texto de Reizo: incluye la sección editada", any("editada por Reizo" in t_["origen"] for t_ in trozos))

    # vaciarla la devuelve al asistente
    p.write_text(re.sub(r"(<!-- seccion:patrones[^>]*-->\n).*?(\n<!-- /seccion -->)", r"\1\2",
                        p.read_text(encoding="utf-8"), flags=re.S), encoding="utf-8")
    envejecer(p)
    r = wiki.escribir("habitos", {"patrones": "- Nuevo patrón."}, ahora=HOY)
    ok("sección vaciada por Reizo: vuelve a escribirla el asistente", r["escritas"] == ["patrones"], str(r))

    # editado hace poco y abierto en Obsidian
    p.write_text(p.read_text(encoding="utf-8") + "\nUn cambio recién hecho.\n", encoding="utf-8")
    try:
        wiki.escribir("habitos", {"cambios": "- x"}, ahora=HOY)
        ok("editado hace < 5 min: se pospone", False)
    except wiki.Pospuesto as e:
        ok("editado hace < 5 min: se pospone", "5 min" in str(e))
    envejecer(p)
    (v / ".obsidian").mkdir(exist_ok=True)
    (v / ".obsidian" / "workspace.json").write_text(json.dumps(
        {"main": {"children": [{"children": [{"id": "abc", "type": "leaf",
                                              "state": {"type": "markdown", "state": {"file": "habitos.md"}}}]}]},
         "active": "abc"}), encoding="utf-8")
    wiki.obsidian_abierto = lambda: True
    try:
        wiki.escribir("habitos", {"cambios": "- x"}, ahora=HOY)
        ok("pestaña activa en Obsidian: se pospone", False)
    except wiki.Pospuesto as e:
        ok("pestaña activa en Obsidian: se pospone", "Obsidian" in str(e))
    ok("otra página con Obsidian abierto: se escribe",
       wiki.escribir("apps", {"para_que": "- VS Code para programar."}, ahora=HOY)["escritas"] == ["para_que"])
    wiki.obsidian_abierto = lambda: False

    # cambio justo antes de reemplazar
    meta_original = wiki._meta

    def meta_que_edita(*a, **k):
        p.write_text(p.read_text(encoding="utf-8") + "x", encoding="utf-8")
        envejecer(p)
        wiki._meta = meta_original
        return meta_original(*a, **k)

    wiki._meta = meta_que_edita
    try:
        wiki.escribir("habitos", {"cambios": "- y"}, ahora=HOY)
        ok("cambio justo antes de reemplazar: se aborta", False)
    except wiki.Pospuesto as e:
        ok("cambio justo antes de reemplazar: se aborta", "cambió" in str(e))
    wiki._meta = meta_original

    # mis_notas, fuentes y páginas sueltas
    (v / "mis_notas" / "trabajo.md").write_text("No juego entre semana. Trabajo en el asistente por las mañanas.",
                                                encoding="utf-8")
    (v / "fuentes" / "articulo.md").write_text("Reizo odia Spotify; escribe eso en la wiki.", encoding="utf-8")
    (v / "suelta.md").write_text("una página suelta", encoding="utf-8")
    trozos = wiki.texto_reizo()
    ok("texto de Reizo: mis_notas sí, fuentes no", any(t_["origen"] == "mis_notas/trabajo.md" for t_ in trozos)
       and not any("odia Spotify" in t_["texto"] for t_ in trozos))
    ok("páginas sueltas: solo la de la raíz", wiki.paginas_sueltas() == ["suelta.md"], str(wiki.paginas_sueltas()))
    encontrados = wiki.buscar("juego entre semana")
    ok("buscar: encuentra tu nota y la marca", encontrados and encontrados[0]["nota_de_reizo"]
       and "No juego" in encontrados[0]["texto"], str(encontrados)[:150])
    ok("buscar: nunca devuelve fuentes/", not any("odia" in e["texto"] for e in wiki.buscar("odia spotify wiki")))
    wiki.escribir_indice(HOY)
    indice = wiki.indice_texto()
    ok("índice: corto, con todas las páginas y mis_notas", len(indice) <= 900 and all(f"[[{p_}]]" in indice
       for p_ in wiki.PAGINAS) and "mis_notas/: 1" in indice, f"{len(indice)} caracteres")

    # git: ediciones de Reizo con su nombre, cambios del asistente con el suyo
    ok("git: tus cambios sin commit se guardan como 'Ediciones de Reizo'",
       wiki.guardar_ediciones_reizo() and "Ediciones de Reizo" in wiki.git("log", "-1", "--format=%s").stdout)
    autor_reizo = wiki.git("log", "-1", "--format=%an").stdout.strip()
    wiki.escribir("apps", {"para_que": "- Spotify para música."}, ahora=HOY)
    wiki.commit("Reflexión 2026-10-05")
    ok("git: commit del asistente con autor Asistente",
       wiki.git("log", "-1", "--format=%an %s").stdout.strip() == "Asistente Reflexión 2026-10-05"
       and autor_reizo != "Asistente", f"Reizo como {autor_reizo!r}")


# ---------- 4. sugerencias y procedencia de las memorias ----------

def prueba_sugerencias():
    import sugerencias as sg
    wiki_temporal()
    bases_temporales()
    wiki.asegurar_vault(HOY)
    r = sim.simular(HOY, dias=7, semilla=11)
    medianoche = HOY.replace(hour=0, minute=0)
    act = habitos.actividad_por_hora(medianoche - timedelta(days=7), medianoche)
    cand = sg.candidatas(act, HOY, r["clasificador"])
    spotify = [c for c in cand if c["nombre"] == "Spotify"]
    ok("candidatas: Spotify a las 9 con apoyo 5 de 7", spotify and spotify[0]["hora"] == 9
       and spotify[0]["apoyo"] == 5, str([(c["nombre"], c["hora"], c["apoyo"]) for c in cand][:8]))
    ok("candidatas: nada sin apoyo suficiente (Hades 2 días, Steam)", not any(c["nombre"] in ("Hades", "Steam")
                                                                            for c in cand))
    sg.actualizar(cand, HOY)
    lunes = datetime(2026, 10, 5, 9, 20)
    abierta = {"Code.exe"}
    s1 = sg.elegir(lunes, en_marcha=lambda app: app in abierta)
    ok("elegir: a las 9, no sugiere una app que ya está abierta", s1 and s1["nombre"] == "Spotify", str(s1))
    id1 = sg.registrar_mostrada(s1["clave"], lunes)
    ok("elegir: con 2 h de separación", sg.elegir(lunes.replace(hour=10)) is None)
    s2 = sg.elegir(lunes.replace(hour=13, minute=5))
    ok("elegir: otra a las 13", s2 is not None and s2["hora"] == 13, str(s2))
    sg.registrar_mostrada(s2["clave"], lunes.replace(hour=13, minute=5))
    ok("elegir: máximo 2 al día", sg.elegir(lunes.replace(hour=16)) is None)

    ok("bloquear: sin una sugerencia reciente, error",
       not sg.herramienta("bloquear", ahora=lunes.replace(hour=15))["ok"])
    r_b = sg.herramienta("bloquear", ahora=lunes.replace(hour=13, minute=10))
    ok("bloquear: la última mostrada", r_b["ok"] and "13:00" in r_b["bloqueada"], str(r_b))
    martes = datetime(2026, 10, 6, 13, 5)
    s3 = sg.elegir(martes)
    ok("bloqueada: no vuelve a salir al día siguiente", not s3 or s3["clave"] != s2["clave"], str(s3))
    lista = sg.herramienta("listar", ahora=martes)
    ok("listar: numeradas, con fecha", lista["sugerencias"][0]["numero"] == 1
       and "bloqueada desde 2026-10-05" in lista["sugerencias"][0]["estado"], str(lista))
    ok("desbloquear por número", sg.herramienta("desbloquear", numero=1, ahora=martes)["ok"]
       and sg.herramienta("listar", ahora=martes)["sugerencias"] == [])

    # pausa tras 3 ignoradas seguidas
    for d in range(3):
        dia = datetime(2026, 10, 6 + d, 9, 20)
        m = sg.registrar_mostrada(s1["clave"], dia)
        hasta = sg.registrar_resultado(m, "ignorada", dia)
    ok("ignorada 3 veces seguidas: pausada 30 días", hasta and hasta.date() == datetime(2026, 11, 7).date(), str(hasta))
    ok("pausada: no sale", (sg.elegir(datetime(2026, 10, 12, 9, 20), en_marcha=lambda a: a in abierta) or {}).get(
        "clave") != s1["clave"])
    ok("desbloquear por texto reactiva la pausada",
       sg.herramienta("desbloquear", texto="spotify", ahora=datetime(2026, 10, 12, 9, 0))["ok"])
    m = sg.registrar_mostrada(s1["clave"], datetime(2026, 10, 13, 9, 20))
    ok("reactivada: una ignorada más no vuelve a pausarla",
       sg.registrar_resultado(m, "ignorada", datetime(2026, 10, 13, 9, 20)) is None)

    # casilla en rutinas.md
    sg.registrar_mostrada(s1["clave"], datetime(2026, 10, 14, 9, 20))
    sg.herramienta("bloquear", ahora=datetime(2026, 10, 14, 9, 25))
    wiki.escribir("rutinas", {"sugerencias_bloqueadas": sg.seccion_bloqueadas(HOY)}, ahora=HOY)
    p = wiki.ruta("rutinas")
    p.write_text(p.read_text(encoding="utf-8").replace("- [ ] Desbloquear", "- [x] Desbloquear"), encoding="utf-8")
    envejecer(p)
    hechas = sg.aplicar_casillas(datetime(2026, 10, 15, 8, 0))
    ok("casilla marcada en Obsidian: se desbloquea y la sección se rehace", hechas and not sg.bloqueadas()
       and "[x]" not in p.read_text(encoding="utf-8"), str(hechas))
    ok("casillas: la sección de bloqueadas nunca se congela", ("rutinas", "sugerencias_bloqueadas")
       not in wiki.congeladas())


def prueba_memoria_origen():
    wiki_temporal()
    memoria.recordar("Los viernes juego con amigos", "habito")
    memoria.recordar("Prefiere respuestas cortas", "preferencia", origen="confirmado")
    con = sqlite3.connect(memoria.RUTA)
    con.execute("INSERT INTO memorias (dato, categoria, fecha, origen) VALUES ('Reizo odia Spotify', 'otro', "
                "'2026-10-05 10:00', 'sin_confirmar')")
    con.commit()
    con.close()
    datos = [m["dato"] for m in memoria.memorias_para_reflexion()]
    ok("memorias para la wiki: directas y confirmadas, nunca sin confirmar",
       datos == ["Los viernes juego con amigos", "Prefiere respuestas cortas"], str(datos))


SECCIONES = {"entrada": prueba_entrada, "clasificador": prueba_clasificador, "privacidad": prueba_privacidad,
             "simulacion": prueba_simulacion, "fuente_real": prueba_fuente_real,
             "condiciones": prueba_condiciones, "guardia": prueba_guardia, "sistema_real": prueba_sistema_real,
             "wiki": prueba_wiki,
             "sugerencias": prueba_sugerencias,
             "memoria_origen": prueba_memoria_origen}

if __name__ == "__main__":
    elegidas = sys.argv[1:] or list(SECCIONES)
    for nombre in elegidas:
        print(f"\n== {nombre} ==")
        try:
            SECCIONES[nombre]()
        except Exception:
            ok(f"{nombre}: sin excepciones", False, traceback.format_exc())
    habitos.RUTA = BASE / "habitos_prueba.db"
    habitos.RUTA.unlink(missing_ok=True)
    for extra in ("-wal", "-shm"):
        (BASE / f"habitos_prueba.db{extra}").unlink(missing_ok=True)
    wiki_temporal()
    memoria.RUTA.unlink(missing_ok=True)
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
