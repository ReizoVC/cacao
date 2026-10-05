"""
Pruebas de la Fase 6 SIN modelo (o con un modelo falso que devuelve JSON fijo). Usan bases y vault temporales
(habitos_prueba.db, memoria_prueba.db, memoria_prueba/), que se borran al terminar; no tocan memoria.db, habitos.db
ni la wiki real, no abren apps ni leen archivos de Reizo.
Uso: .venv\\Scripts\\python probar_fase6.py [seccion ...]   (sin argumentos, todas)
"""
import sqlite3
import sys
import traceback
from datetime import datetime, timedelta

import deteccion
import entrada
import habitos
import simular_habitos as sim

BASE = habitos.BASE
HOY = datetime(2026, 10, 5, 10, 0)  # lunes: los 7 días simulados van del lunes 28 al domingo 4
resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


def bases_temporales():
    habitos.RUTA = BASE / "habitos_prueba.db"
    habitos.RUTA.unlink(missing_ok=True)


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


SECCIONES = {"entrada": prueba_entrada, "clasificador": prueba_clasificador, "privacidad": prueba_privacidad,
             "simulacion": prueba_simulacion, "fuente_real": prueba_fuente_real,
             "condiciones": prueba_condiciones, "guardia": prueba_guardia, "sistema_real": prueba_sistema_real}

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
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
