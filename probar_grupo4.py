"""
Pruebas sin modelo del grupo 4. No cierra apps, no mueve archivos del usuario, no toca mouse ni teclado:
  - cerrar_app, mover_archivo, mouse y teclado se prueban con sus planificar_* (validan y calculan, sin efectos);
  - mover_archivo real se prueba solo con archivos de prueba en una carpeta temporal que pasa a ser la única
    "permitida" durante la prueba;
  - la interrupción de teclado se prueba con el envío de teclas reemplazado por una función que solo cuenta.
Uso: .venv\\Scripts\\python probar_grupo4.py
"""
import json
import tempfile
import time
from pathlib import Path

import psutil

import herramientas_grupo1 as g1
import herramientas_grupo4 as g4
from emergencia import Detenido

fallos = []
# nombres reales de archivos sensibles de este PC: en datos_locales.json (excluido de git), nunca en el código
_ruta_locales = Path(__file__).with_name("datos_locales.json")
LOCALES = json.loads(_ruta_locales.read_text(encoding="utf-8")) if _ruta_locales.exists() else {}
TITULO_SENSIBLE = LOCALES.get("titulo_ventana_sensible", "claves-prueba.env: Bloc de notas")


def comprobar(nombre, condicion, detalle=""):
    print(f"{'OK ' if condicion else 'MAL'} {nombre}{': ' + str(detalle) if detalle else ''}")
    if not condicion:
        fallos.append(nombre)


def resultado(plan_error):
    plan, error = plan_error
    if error:
        return "bloqueado" if error.get("bloqueado") else "error", error
    return "plan", plan


if __name__ == "__main__":
    print("-- cerrar_app (solo planes; lee las ventanas reales)")
    ventanas = g1.listar_ventanas()
    print("   ventanas abiertas:", [(v["proceso"], v["titulo"][:30]) for v in ventanas])
    explorer = next((p.pid for p in psutil.process_iter(["name"]) if p.info["name"] == "explorer.exe"), None)
    tipo, r = resultado(g4.planificar_cierre(pid=explorer))
    comprobar("explorer.exe (pid) está protegido", tipo == "bloqueado", r.get("error"))
    propias = [v for v in ventanas if v["pid"] in g4._ancestros_propios()]
    if propias:
        tipo, r = resultado(g4.planificar_cierre(proceso=propias[0]["proceso"]))
        comprobar(f"la ventana donde corre el asistente ({propias[0]['proceso']}) está protegida",
                  tipo == "bloqueado", r.get("error"))
    if any(v["proceso"].lower() == "windowsterminal.exe" for v in ventanas):
        anterior = g4.os.environ.get("WT_SESSION")
        g4.os.environ["WT_SESSION"] = anterior or "prueba"  # como si el agente corriera dentro de la terminal
        wt = next(v for v in ventanas if v["proceso"].lower() == "windowsterminal.exe")
        tipo, r = resultado(g4.planificar_cierre(id_ventana=wt["id_ventana"]))  # por id: vale con 1 o varias ventanas
        comprobar("Windows Terminal protegida si el asistente corre dentro (WT_SESSION)", tipo == "bloqueado",
                  r.get("error"))
        if anterior is None:
            del g4.os.environ["WT_SESSION"]
    tipo, r = resultado(g4.planificar_cierre(proceso="app_que_no_existe"))
    comprobar("app que no está abierta -> error con la lista de ventanas", tipo == "error", r.get("error"))
    tipo, r = resultado(g4.planificar_cierre())
    comprobar("sin proceso ni pid -> error", tipo == "error")
    por_pid = {}
    for v in ventanas:
        por_pid.setdefault(v["pid"], []).append(v)
    varias = next((vs for vs in por_pid.values() if len(vs) > 1), None)
    if varias:  # p. ej. dos ventanas del Bloc de notas en un solo proceso
        tipo, r = resultado(g4.planificar_cierre(pid=varias[0]["pid"]))
        comprobar("varias ventanas del mismo proceso -> pide id_ventana", tipo == "error" and "coincidencias" in r)
        tipo, r = resultado(g4.planificar_cierre(id_ventana=varias[0]["id_ventana"]))
        comprobar("con id_ventana cierra solo esa ventana", tipo == "plan" and r["ventanas"] == [varias[0]["id_ventana"]]
                  and r["otras_del_proceso"], r)
    otras = [v for v in ventanas if v["pid"] not in g4._ancestros_propios()
             and v["proceso"].lower() not in g4.PROTEGIDOS]
    if otras:
        tipo, r = resultado(g4.planificar_cierre(proceso=otras[0]["proceso"]))
        comprobar(f"plan para {otras[0]['proceso']} (no se cierra)", tipo in ("plan", "error"), r)

    print("\n-- mover_archivo (solo planes sobre las carpetas reales)")
    casos = [("Descargas/Spark.txt", "Documentos", "plan"),
             ("Descargas/Spark.txt", "spark_notas.txt", "plan"),
             ("Descargas/Spark.txt", "Descargas/Libro1.csv", "error"),           # destino existe: no sobrescribe
             ("Descargas/Spark.txt", "Escritorio/passwords.txt", "bloqueado"),  # patrón sensible en el destino
             ("Descargas/Spark.txt", "C:/Windows/Spark.txt", "bloqueado"),      # fuera de las permitidas
             ("C:/Windows/win.ini", "Documentos", "bloqueado"),
             ("Documentos", "Escritorio", "bloqueado"),                          # carpeta raíz permitida
             ("Descargas/no_existe_123.txt", "Documentos", "error")]
    if LOCALES.get("sensible_en_descargas"):  # un archivo sensible real: patrón sensible en el origen
        casos.append((f"Descargas/{LOCALES['sensible_en_descargas']}", "Escritorio", "bloqueado"))
    else:
        print("SALTA archivo sensible real en Descargas (falta datos_locales.json)")
    for origen, destino, esperado in casos:
        tipo, r = resultado(g4.planificar_movimiento(origen, destino))
        detalle = r.get("error") if isinstance(r, dict) else f"{r[0]} -> {r[1]}"
        comprobar(f"{origen} -> {destino} = {esperado}", tipo == esperado, detalle)

    print("\n-- mover_archivo real, solo en una carpeta temporal con archivos de prueba")
    with tempfile.TemporaryDirectory() as tmp:
        caja = Path(tmp).resolve()
        originales = g1.CARPETAS_PERMITIDAS, g4.CARPETAS_PERMITIDAS
        g1.CARPETAS_PERMITIDAS = g4.CARPETAS_PERMITIDAS = [caja]
        try:
            (caja / "a.txt").write_text("A", encoding="utf-8")
            (caja / "b.txt").write_text("B", encoding="utf-8")
            (caja / "sub").mkdir()
            r = g4.mover_archivo(str(caja / "a.txt"), str(caja / "b.txt"))
            comprobar("no sobrescribe un archivo existente", not r["ok"] and
                      (caja / "b.txt").read_text(encoding="utf-8") == "B" and (caja / "a.txt").exists(), r)
            r = g4.mover_archivo(str(caja / "a.txt"), "c.txt")
            comprobar("renombra con solo un nombre nuevo", r["ok"] and (caja / "c.txt").exists(), r)
            r = g4.mover_archivo(str(caja / "c.txt"), str(caja / "sub"))
            comprobar("mueve dentro de una carpeta existente", r["ok"] and (caja / "sub" / "c.txt").exists(), r)
            r = g4.mover_archivo(str(caja / "sub"), str(caja / "sub" / "dentro"))
            comprobar("no mueve una carpeta dentro de sí misma", not r["ok"], r.get("error"))
            (caja / "token_api.txt").write_text("x", encoding="utf-8")
            r = g4.mover_archivo(str(caja / "token_api.txt"), "otro.txt")
            comprobar("no mueve un archivo sensible", r.get("bloqueado") and (caja / "token_api.txt").exists(), r)
        finally:
            g1.CARPETAS_PERMITIDAS, g4.CARPETAS_PERMITIDAS = originales

    print("\n-- mouse: conversión de coordenadas (capturas sintéticas, sin mover el cursor)")
    ahora = time.time()
    pantalla_4k = {"ancho": 1920, "alto": 1080, "origen": (0, 0), "escala": 0.5, "momento": ahora}
    ventana = {"ancho": 800, "alto": 600, "origen": (500, 300), "escala": 1.0, "momento": ahora}
    izquierda = {"ancho": 1920, "alto": 1080, "origen": (-1920, 0), "escala": 0.5, "momento": ahora}
    conversiones = [
        ("4K reducida a 1920, proceso DPI-aware", (100, 50, pantalla_4k, True, None), (200, 100)),
        ("4K reducida, proceso NO DPI-aware con escalado 150 %", (100, 50, pantalla_4k, False, 144), (133, 67)),
        ("4K reducida, NO DPI-aware con escalado 125 %", (960, 540, pantalla_4k, False, 120), (1536, 864)),
        ("ventana activa con origen (500, 300), sin reducir", (10, 20, ventana, True, None), (510, 320)),
        ("monitor a la izquierda del principal (origen negativo)", (100, 100, izquierda, True, None), (-1720, 200)),
    ]
    for nombre, (x, y, cap, consciente, dpi), esperado in conversiones:
        obtenido = g4.a_pantalla(x, y, cap, consciente=consciente, dpi=dpi)
        comprobar(nombre, obtenido == esperado, f"{obtenido} (esperado {esperado})")
    tipo, r = resultado(g4.planificar_mouse("clic", 100, 50, captura=pantalla_4k))
    comprobar("plan de clic (con el modo DPI real de este proceso)", tipo == "plan", r)
    for nombre, args, esperado in [
            ("clic sin captura previa", dict(accion="clic", x=1, y=1, captura=None), "error"),
            ("clic fuera de la captura", dict(accion="clic", x=2000, y=10, captura=pantalla_4k), "error"),
            ("captura de hace 3 minutos", dict(accion="clic", x=1, y=1, captura=pantalla_4k, ahora=ahora + 180),
             "error"),
            ("clic sin coordenadas", dict(accion="clic", captura=pantalla_4k), "error"),
            ("desplazar sin coordenadas", dict(accion="desplazar", cantidad=-3), "plan"),
            ("desplazar sin cantidad", dict(accion="desplazar"), "error"),
            ("acción desconocida", dict(accion="arrastrar", x=1, y=1, captura=pantalla_4k), "error")]:
        if args.get("captura", "x") is None:
            g4.vision.ultima_captura = None
        tipo, r = resultado(g4.planificar_mouse(**args))
        comprobar(nombre, tipo == esperado, r.get("error") if isinstance(r, dict) and "error" in r else r)
    print(f"   este proceso DPI-aware: {g4.proceso_dpi_aware()}; DPI del monitor principal: {g4.dpi_en(0, 0)}")

    print("\n-- teclado (solo planes)")
    for nombre, args, esperado in [
            ("escribir texto con tildes", dict(accion="escribir", texto="hola, ¿qué tal? ñandú"), "plan"),
            ("rechaza Ctrl+G como texto", dict(accion="escribir", texto="Ctrl+G"), "error"),
            ("rechaza Alt+F4 como texto", dict(accion="escribir", texto="Alt + F4"), "error"),
            ("permite una frase que menciona Ctrl+G", dict(accion="escribir", texto="Presiona Ctrl+G para guardar"), "plan"),
            ("atajo ctrl+s", dict(accion="atajo", teclas=["ctrl", "s"]), "plan"),
            ("tecla Enter (mayúsculas)", dict(accion="tecla", teclas=["Enter"]), "plan"),
            ("atajo con 'Mayús' y 'Control'", dict(accion="atajo", teclas=["Control", "Mayús", "t"]), "plan"),
            ("win+r (Ejecutar) bloqueado", dict(accion="atajo", teclas=["win", "r"]), "bloqueado"),
            ("win+x bloqueado", dict(accion="atajo", teclas=["win", "x"]), "bloqueado"),
            ("el propio atajo de emergencia bloqueado", dict(accion="atajo", teclas=["ctrl", "alt", "shift", "q"]),
             "bloqueado"),
            ("tecla desconocida", dict(accion="tecla", teclas=["hyper"]), "error"),
            ("texto demasiado largo", dict(accion="escribir", texto="x" * 2001), "error"),
            ("escribir sin texto", dict(accion="escribir"), "error")]:
        tipo, r = resultado(g4.planificar_teclado(**args))
        comprobar(nombre, tipo == esperado, r.get("error") if isinstance(r, dict) and "error" in r else "")

    print("\n-- teclado: el atajo de emergencia corta a mitad de un texto (sin enviar teclas)")
    enviadas = []
    enviar_real, par_real, comprobar_real, modo_real = g4._enviar, g4._enviar_par, g4.comprobar_emergencia, g4.MODO_ESCRIBIR
    g4._enviar = lambda **kw: enviadas.append(kw)
    g4._enviar_par = lambda scan: enviadas.extend([scan, scan])  # bajar y subir
    g4.MODO_ESCRIBIR, g4.PAUSA_TECLEO = "teclear", 0

    def corta_tras_40():
        if len(enviadas) >= 80:  # 40 caracteres = 80 eventos (bajar y subir)
            raise Detenido("atajo simulado")

    g4.comprobar_emergencia = corta_tras_40
    try:
        g4.teclado("escribir", texto="a" * 200)
        comprobar("se detuvo a mitad del texto", False, "no se detuvo")
    except Detenido:
        comprobar("se detuvo a mitad del texto", len(enviadas) < 400, f"{len(enviadas) // 2} de 200 caracteres")
    finally:
        g4._enviar, g4._enviar_par, g4.comprobar_emergencia, g4.MODO_ESCRIBIR = (enviar_real, par_real,
                                                                                  comprobar_real, modo_real)

    print("\n-- listar_controles y clic por nombre (UI Automation, solo lectura)")
    terminal = next((v for v in g1.listar_ventanas() if v["proceso"].lower() == "windowsterminal.exe"), None)
    if terminal:
        controles = g4.listar_controles(terminal["id_ventana"])
        nombres = [c["nombre"] for c in controles] if isinstance(controles, list) else controles
        # el botón de minimizar no sale con algunas ventanas (ajustadas o maximizadas): vale cualquiera de estos
        objetivo = next((n for n in ("Minimizar", "Nueva pestaña", "Maximizar") if n in nombres), None)
        comprobar("lista los controles de Windows Terminal", isinstance(controles, list) and objetivo, nombres)
        tipo, r = resultado(g4.planificar_mouse("clic", control=objetivo, id_ventana=terminal["id_ventana"]))
        boton = next(c for c in controles if c["nombre"] == objetivo)
        comprobar("clic por nombre: apunta al centro del botón, sin captura", tipo == "plan" and
                  r["pantalla"] == tuple(boton["centro"]), r)
        tipo, r = resultado(g4.planificar_mouse("clic", control="Cerrar", id_ventana=terminal["id_ventana"]))
        comprobar("'Cerrar' exacto gana a 'Cerrar pestaña'", tipo == "plan" and r["control"].startswith("Cerrar ("), r)
        tipo, r = resultado(g4.planificar_mouse("clic", control="Botón que no existe", id_ventana=terminal["id_ventana"]))
        comprobar("control inexistente -> error", tipo == "error", r.get("error"))
        # ambigüedad con controles sintéticos: no depende de qué botones tenga la terminal abierta
        controles_reales = g4._controles
        g4._controles = lambda _h: ([{"nombre": "Aumentar zoom", "tipo": "Button", "centro": [10, 10],
                                      "habilitado": True},
                                     {"nombre": "Aumentar tamaño de fuente", "tipo": "Button", "centro": [50, 10],
                                      "habilitado": True}], None)
        try:
            tipo, r = resultado(g4.planificar_mouse("clic", control="Aumentar", id_ventana=terminal["id_ventana"]))
        finally:
            g4._controles = controles_reales
        comprobar("nombre ambiguo -> error con opciones", tipo == "error" and "coincidencias" in r, r.get("coincidencias"))
        original = g4.es_titulo_sensible
        g4.es_titulo_sensible = lambda _t: True  # como si la ventana se llamara "claves.kdbx - KeePass"
        r = g4.listar_controles(terminal["id_ventana"])
        g4.es_titulo_sensible = original
        comprobar("ventana con título sensible -> no se inspecciona", isinstance(r, dict) and r.get("bloqueado"), r)
    r = g4.listar_controles(123456789)
    comprobar("ventana inexistente -> error", isinstance(r, dict) and not r.get("ok", True), r.get("error"))

    print("\n-- ver_pantalla con ventanas sensibles (imágenes y ventanas sintéticas)")
    from PIL import Image
    import vision
    zona = {"left": 0, "top": 0, "width": 400, "height": 300}
    imagen = Image.new("RGB", (400, 300), (255, 255, 255))
    ventanas = [(1, "claves.kdbx - KeePass", (50, 50, 150, 150)), (2, "Calculadora", (0, 0, 400, 300))]
    tapadas = vision.tapar_sensibles(imagen, zona, ventanas)
    comprobar("pantalla completa: tapa la ventana sensible", tapadas == ["claves.kdbx - KeePass"]
              and imagen.getpixel((140, 140)) == (0, 0, 0) and imagen.getpixel((300, 200)) == (255, 255, 255))
    imagen = Image.new("RGB", (400, 300), (255, 255, 255))
    ventanas = [(9, "Calculadora", (0, 0, 400, 300)), (1, TITULO_SENSIBLE, (50, 50, 150, 150))]
    tapadas = vision.tapar_sensibles(imagen, zona, ventanas, hwnd_capturada=9)
    comprobar("ventana activa: no tapa las sensibles que quedan debajo (no se ven)", tapadas == [])
    imagen = Image.new("RGB", (400, 300), (255, 255, 255))
    ventanas = [(1, "id_rsa - Visual Studio Code", (300, 200, 600, 500)), (9, "Calculadora", (0, 0, 400, 300))]
    tapadas = vision.tapar_sensibles(imagen, zona, ventanas, hwnd_capturada=9)
    comprobar("ventana activa: tapa la parte de una sensible que está encima", tapadas == ["id_rsa - Visual Studio Code"]
              and imagen.getpixel((350, 250)) == (0, 0, 0) and imagen.getpixel((100, 100)) == (255, 255, 255))
    titulo_real = vision.win32gui.GetWindowText
    vision.win32gui.GetWindowText = lambda _h: TITULO_SENSIBLE
    try:
        vision.capturar("ventana_activa")
        comprobar("ventana activa sensible -> rechaza la captura", False, "capturó")
    except vision.CapturaBloqueada as e:
        comprobar("ventana activa sensible -> rechaza la captura", True, e)
    finally:
        vision.win32gui.GetWindowText = titulo_real
    _, info = vision.capturar("completa")
    comprobar("captura real de la pantalla: sin ventanas sensibles abiertas, no tapa nada",
              info["ventanas_tapadas"] == 0, info["ventanas_tapadas"])

    # ---------- mouse: ni la bandeja de Windows ni los menús de la isla (ventanas simuladas) ----------
    print("\n-- mouse: bandeja de Windows y menús de la isla --")
    ISLA, BARRA, OTRA = 101, 202, 303
    NOTIFICACION = (1694, 1078, 1920, 1126)
    clases = {ISLA: "#32768", BARRA: "Shell_TrayWnd", OTRA: "Notepad"}
    raiz_en_punto = {"valor": OTRA}
    guardado_bandeja = g4._raiz_en, g4._rects_bandeja, g4.es_de_la_isla, g4._nombre_clase
    g4._raiz_en = lambda _p: raiz_en_punto["valor"]
    g4._rects_bandeja = lambda: [NOTIFICACION]
    g4.es_de_la_isla = lambda h: h == ISLA
    g4._nombre_clase = lambda h: clases[h]
    try:
        raiz_en_punto["valor"] = BARRA
        comprobar("bandeja: un ícono del área de notificación, bloqueado",
                  "bandeja de Windows" in (g4.bandeja_o_isla_en_punto((1800, 1100)) or ""))
        comprobar("bandeja: el resto de la barra de tareas sigue permitido",
                  g4.bandeja_o_isla_en_punto((900, 1100)) is None)
        for clase in g4.CLASES_DESBORDAMIENTO:
            clases[BARRA] = clase
            comprobar(f"bandeja: el desbordamiento de íconos ({clase}), bloqueado",
                      "bandeja de Windows" in (g4.bandeja_o_isla_en_punto((1600, 950)) or ""))
        clases[BARRA] = "Shell_TrayWnd"
        raiz_en_punto["valor"] = ISLA
        comprobar("bandeja: un menú contextual de la isla (ventana de su proceso), bloqueado",
                  "isla de Cacao" in (g4.bandeja_o_isla_en_punto((1500, 900)) or ""))
        raiz_en_punto["valor"] = OTRA
        comprobar("bandeja: una ventana normal, permitida", g4.bandeja_o_isla_en_punto((500, 500)) is None)
        g4._raiz_en = lambda _p: 1 / 0
        comprobar("bandeja: si no se puede comprobar, bloqueado",
                  "por seguridad" in (g4.bandeja_o_isla_en_punto((500, 500)) or ""))
        g4._raiz_en = lambda _p: raiz_en_punto["valor"]
        # de punta a punta: planificar_mouse llama a prohibida_en_punto, que mira la bandeja antes que la ventana
        zonas, captura, cursor = g4.zonas_isla, g4.vision.ultima_captura, g4.win32api.GetCursorPos
        g4.zonas_isla = lambda: []
        g4.vision.ultima_captura = {"momento": time.time() + 3600, "ancho": 1920, "alto": 1080, "escala": 1.0,
                                    "origen": (0, 0)}
        try:
            px, py = g4.a_pantalla(1800, 1070, g4.vision.ultima_captura)
            g4._rects_bandeja = lambda: [(px - 5, py - 5, px + 5, py + 5)]
            raiz_en_punto["valor"] = BARRA
            for accion in ("clic", "clic_derecho", "doble_clic", "mover"):
                estado, error = resultado(g4.planificar_mouse(accion, 1800, 1070))
                comprobar(f"planificar_mouse {accion} sobre la bandeja: bloqueado", estado == "bloqueado", error)
            g4.win32api.GetCursorPos = lambda: (px, py)
            estado, _ = resultado(g4.planificar_mouse("desplazar", cantidad=-3))
            comprobar("planificar_mouse desplazar con el cursor en la bandeja: bloqueado", estado == "bloqueado")
            raiz_en_punto["valor"] = ISLA
            g4._rects_bandeja = lambda: []
            estado, _ = resultado(g4.planificar_mouse("clic", 100, 100))
            comprobar("planificar_mouse clic en un menú de la isla (fuera de su forma): bloqueado", estado == "bloqueado")
        finally:
            g4.zonas_isla, g4.vision.ultima_captura, g4.win32api.GetCursorPos = zonas, captura, cursor
    finally:
        g4._raiz_en, g4._rects_bandeja, g4.es_de_la_isla, g4._nombre_clase = guardado_bandeja
    raices = g4._rects_bandeja()
    comprobar("bandeja real: se encuentra el área de notificación de esta barra de tareas", len(raices) >= 1, raices)

    print(f"\n{'TODO OK' if not fallos else f'{len(fallos)} fallos: {fallos}'}")
