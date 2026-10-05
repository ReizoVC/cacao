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


SECCIONES = {"entrada": prueba_entrada, "clasificador": prueba_clasificador, "privacidad": prueba_privacidad,
             "simulacion": prueba_simulacion, "fuente_real": prueba_fuente_real}

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
