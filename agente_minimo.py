"""
Agente mínimo (Fases 3 a 5): loop agéntico con Gemma 4 12B vía llama-cpp-python.
Herramientas activas: listar_apps, abrir_app, volumen, finalizar y el grupo 1 de la Fase 5
(listar_ventanas, enfocar_ventana, listar_carpeta, leer_archivo, buscar_web, en herramientas_grupo1.py)
el grupo 2 (ver_pantalla, en vision.py, con el mmproj), el grupo 3 (recordar, consultar_memoria, en memoria.py,
sobre memoria.db) y el grupo 4 (cerrar_app, mover_archivo, mouse, teclado, en herramientas_grupo4.py, todas con
confirmación). El atajo de emergencia (emergencia.py) detiene la tarea en cualquier paso. Las rutas del modelo y del mmproj y sus parámetros se leen de config.json.
Requiere en la misma carpeta: config.json, herramientas.json, modelo.py, muestreo_gramatica.py, vision.py,
herramientas_grupo1.py, herramientas_grupo4.py, memoria.py y emergencia.py.
Las categorías de las apps se guardan en apps_categorias.json y solo se calculan para apps nuevas.
"""
import json
import re
import subprocess
import time
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz import process, fuzz
from pycaw.pycaw import AudioUtilities

import herramientas_grupo4
import memoria
from emergencia import Detenido, Emergencia
from herramientas_grupo1 import listar_ventanas, enfocar_ventana, listar_carpeta, leer_archivo, buscar_web
from herramientas_grupo4 import cerrar_app, listar_controles, mover_archivo, mouse, teclado
from memoria import recordar, consultar_memoria
from modelo import cargar_config, crear_llm
from vision import CapturaBloqueada, ManejadorVision, PRESUPUESTOS, capturar

BASE = Path(__file__).parent
CONFIG = cargar_config()
RUTA_CATEGORIAS = BASE / "apps_categorias.json"
CATALOGO = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))
ACTIVAS = {"listar_apps", "abrir_app", "volumen", "finalizar",
           "listar_ventanas", "enfocar_ventana", "listar_carpeta", "leer_archivo", "buscar_web",
           "recordar", "consultar_memoria", "ver_pantalla", "cerrar_app", "mover_archivo", "mouse", "teclado",
           "listar_controles"}
if not CONFIG.get("mmproj"):
    ACTIVAS.discard("ver_pantalla")
HERRAMIENTAS = {h["nombre"]: h for h in CATALOGO["herramientas"] if h["nombre"] in ACTIVAS}
MAX_PASOS = CATALOGO["limites"]["max_pasos_por_tarea"]
APPS_SENSIBLES = CATALOGO["limites"]["apps_sensibles"]

# deben coincidir con las que lista la descripción de listar_apps en herramientas.json
CATEGORIAS = ["música", "video", "fotos", "diseño", "juegos", "navegador", "oficina",
              "comunicación", "desarrollo", "utilidades", "sistema", "otros"]
TAMANO_LOTE = 40
LIMITE_RESULTADO = 500  # caracteres; resultados más largos se resumen al terminar cada tarea
# palabras que no forman parte del nombre de una app ("abre el editor" -> "editor")
ARTICULOS = {"el", "la", "los", "las", "mi", "mis", "un", "una", "app", "aplicacion", "programa",
             "abre", "abrir", "abreme", "inicia", "iniciar", "ejecuta", "lanza", "pon", "ponme"}
# nombres que no identifican una app concreta: sin alias ni coincidencia exacta, abrir_app pregunta
GENERICOS = {"editor", "editor de texto", "editor de codigo", "navegador", "explorador", "reproductor",
             "juego", "chat", "correo", "notas", "consola"}


# ---------- Apps instaladas y categorías ----------

_cache_apps = []   # [{nombre, id}] tal como los devuelve Get-StartApps
_categorias = {}   # id -> {nombre, categoria}


def normalizar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower().strip()


def leer_start_apps():
    cmd = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
           "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress")
    salida = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                            capture_output=True, text=True, encoding="utf-8").stdout
    datos = json.loads(salida) if salida.strip() else []
    if isinstance(datos, dict):
        datos = [datos]
    return [{"nombre": a["Name"], "id": a["AppID"]} for a in datos]


def categorizar_lote(nombres):
    # claves numeradas: la gramática obliga a responder una categoría válida por cada app
    claves = [str(i) for i in range(1, len(nombres) + 1)]
    esquema = {"type": "object",
               "properties": {k: {"type": "string", "enum": CATEGORIAS} for k in claves},
               "required": claves}
    instrucciones = (
        "Clasificas aplicaciones de Windows. Responde SOLO con un JSON que asigne a cada número "
        f"una categoría de esta lista: {', '.join(CATEGORIAS)}. "
        "'música' incluye escuchar, crear o editar audio; 'sistema' incluye herramientas de Windows, "
        "controladores, configuraciones y desinstaladores; usa 'otros' si ninguna encaja.")
    r = llm.create_chat_completion(
        messages=[{"role": "system", "content": instrucciones},
                  {"role": "user", "content": "\n".join(f"{k}. {n}" for k, n in zip(claves, nombres))}],
        response_format={"type": "json_object", "schema": esquema},
        temperature=0, max_tokens=24 * len(nombres) + 64,
    )
    asignadas = json.loads(r["choices"][0]["message"]["content"])
    return [asignadas.get(k) if asignadas.get(k) in CATEGORIAS else "otros" for k in claves]


def guardar_categorias():
    RUTA_CATEGORIAS.write_text(json.dumps(_categorias, ensure_ascii=False, indent=1), encoding="utf-8")


def sincronizar_apps():
    global _cache_apps, _categorias
    _cache_apps = leer_start_apps()
    guardadas = json.loads(RUTA_CATEGORIAS.read_text(encoding="utf-8")) if RUTA_CATEGORIAS.exists() else {}
    if not _cache_apps:  # si Get-StartApps falla no hay que borrar el caché
        print("Aviso: Get-StartApps no devolvió apps; uso el caché sin cambios.")
        _categorias = guardadas
        return
    actuales = {a["id"]: a["nombre"] for a in _cache_apps}
    eliminadas = [i for i in guardadas if i not in actuales]
    # una app cuyo nombre cambió se vuelve a categorizar
    nuevas = [i for i, n in actuales.items() if guardadas.get(i, {}).get("nombre") != n]
    pendientes = set(nuevas)
    _categorias = {i: d for i, d in guardadas.items() if i in actuales and i not in pendientes}
    for inicio in range(0, len(nuevas), TAMANO_LOTE):
        lote = nuevas[inicio:inicio + TAMANO_LOTE]
        print(f"  Categorizando apps {inicio + 1}-{inicio + len(lote)} de {len(nuevas)}...")
        for app_id, categoria in zip(lote, categorizar_lote([actuales[i] for i in lote])):
            _categorias[app_id] = {"nombre": actuales[app_id], "categoria": categoria}
        guardar_categorias()  # guarda el progreso por si se interrumpe
    if eliminadas and not nuevas:
        guardar_categorias()
    print(f"Apps: {len(actuales)} ({len(nuevas)} nuevas, {len(eliminadas)} eliminadas)")


# ---------- Implementación de herramientas ----------

def listar_apps(filtro: str = ""):
    apps = [d for i, d in _categorias.items() if nivel_app(i) != "bloqueadas"]  # las bloqueadas ni se muestran
    if not filtro:
        conteo = Counter(d["categoria"] for d in apps)
        return {"total": len(apps), "por_categoria": dict(conteo.most_common()),
                "nota": "Pasa en 'filtro' una categoría o un nombre para ver las apps."}
    f = normalizar(filtro)
    categorias = [c for c in CATEGORIAS if len(f) >= 3 and (normalizar(c) in f or f in normalizar(c))]
    encontradas = [d for d in apps if d["categoria"] in categorias]
    # si el filtro ya es una categoría, solo se suman nombres muy parecidos para no meter ruido
    umbral = 80 if categorias else 60
    for _, puntaje, i in process.extract(filtro, [d["nombre"] for d in apps], scorer=fuzz.WRatio, limit=10):
        if puntaje >= umbral and apps[i] not in encontradas:
            encontradas.append(apps[i])
    encontradas = list({d["nombre"]: d for d in encontradas}.values())  # accesos directos repetidos
    # las bloqueadas no se listan, pero se avisa si coinciden, para que el modelo no diga "no la encontré"
    bloqueadas = [d["nombre"] for i, d in _categorias.items() if nivel_app(i) == "bloqueadas"
                  and (normalizar(d["nombre"]) == f or (len(f) >= 4 and f in normalizar(d["nombre"]))
                       or f.rsplit(".", 1)[0] in i.lower().rsplit("\\", 1)[-1])]
    if bloqueadas:
        return {"apps": encontradas, "bloqueadas": sorted(set(bloqueadas)),
                "nota": "Las de 'bloqueadas' están instaladas pero bloqueadas por seguridad: no las abras ni busques "
                        "otro camino; si Reizo las necesita, que las abra él."}
    if encontradas:
        return encontradas
    return {"coincidencias": [],
            "nota": f"Nada coincide por nombre ni por categoría. Categorías: {', '.join(CATEGORIAS)}."}


def coincide_por_siglas(buscado, nombre):
    """True si cada palabra buscada es igual a una palabra del nombre o son las siglas de varias seguidas,
    cubriendo todo el nombre salvo lo que va entre paréntesis: 'vs code' -> 'Visual Studio Code',
    'obs studio' -> 'OBS Studio (64bit)'; 'obs' no coincide con 'OBS Studio' (sobra Studio)."""
    q = normalizar(buscado).split()
    n = re.sub(r"\(.*?\)", " ", normalizar(nombre)).split()

    def cubre(i, j):
        if i == len(q):
            return j == len(n)
        t = q[i]
        if j < len(n) and n[j] == t and cubre(i + 1, j + 1):
            return True
        k = len(t)
        return (k > 1 and j + k <= len(n) and "".join(w[0] for w in n[j:j + k]) == t and cubre(i + 1, j + k))

    return cubre(0, 0)


def nivel_app(app_id):
    """'bloqueadas', 'confirmar' o None según apps_sensibles de herramientas.json. Compara el ejecutable (lo que
    va tras la última barra del AppID) o el AppID completo, sin mayúsculas."""
    ident = app_id.lower()
    ejecutable = ident.replace("/", "\\").rsplit("\\", 1)[-1]
    for nivel in ("bloqueadas", "confirmar"):
        lista = APPS_SENSIBLES[nivel]
        if (ejecutable in {e.lower() for e in lista["ejecutables"]}
                or ident in {a["id"].lower() for a in lista["appids"]}):
            return nivel
    return None


def _sin_articulos(nombre):
    texto = " ".join(p for p in normalizar(nombre).split() if p not in ARTICULOS)
    return texto, (texto[:-1] if texto.endswith("s") else texto)


def es_generico(nombre):
    texto, singular = _sin_articulos(nombre)
    return bool(texto) and (texto in GENERICOS or singular in GENERICOS
                            or any(normalizar(c) in (texto, singular) for c in CATEGORIAS))


def opciones_genericas(nombre, permitidas):
    """Apps de la categoría que nombra el genérico ('navegador') o cuyo nombre contiene la palabra ('editor')."""
    texto, singular = _sin_articulos(nombre)
    categorias = {c for c in CATEGORIAS if normalizar(c) in (texto, singular)}
    opciones = [a["nombre"] for a in permitidas
                if _categorias.get(a["id"], {}).get("categoria") in categorias
                or re.search(rf"\b{re.escape(singular)}", normalizar(a["nombre"]))]
    return list(dict.fromkeys(opciones))


def cubre_bien(buscado, nombre):
    """True si cada palabra buscada aparece (con erratas leves) en el nombre y al nombre le sobra como mucho
    una palabra: 'chrome' -> 'Google Chrome' sí; 'registro' -> 'Registro de telemetría para Office' no."""
    q = buscado.split()
    n = re.sub(r"\(.*?\)", " ", normalizar(nombre)).split()
    return (len(n) <= len(q) + 1
            and all(any(fuzz.ratio(t, w) >= 85 for w in n) for t in q))  # 85: "teams" no es "steam" (80)


def elegir_app(nombre, apps):
    """Elige una app de 'apps' ([{nombre, id}]). Devuelve (app, None) o (None, error para el modelo). Orden:
    alias de memoria.db; coincidencia exacta (sin mayúsculas ni tildes), que gana aunque haya otras parecidas
    ('WhatsApp' frente a 'WhatsApp Beta'); una única coincidencia por siglas ('VS Code'); si el nombre es
    genérico ('el editor'), las opciones para que el modelo pregunte; al final, la búsqueda aproximada.
    Las apps bloqueadas en herramientas.json nunca se eligen."""
    buscado = memoria.resolver_alias(nombre) or nombre
    limpio = _sin_articulos(buscado)[0] or normalizar(buscado)
    exactas = [a for a in apps if normalizar(a["nombre"]) in (normalizar(buscado), limpio)]
    permitidas = [a for a in apps if nivel_app(a["id"]) != "bloqueadas"]
    # también se reconoce el ejecutable de una bloqueada ("regedit", "services.msc")
    ejecutables = {e.lower().rsplit(".", 1)[0] for e in APPS_SENSIBLES["bloqueadas"]["ejecutables"]}
    if (exactas and not any(a in permitidas for a in exactas)) or limpio.rsplit(".", 1)[0] in ejecutables:
        app = exactas[0]["nombre"] if exactas else limpio
        return None, {"ok": False, "bloqueado": True,
                      "error": f"La app «{app}» está bloqueada por seguridad; si la necesitas, ábrela tú."}
    exactas = [a for a in exactas if a in permitidas]
    if exactas:
        return exactas[0], None  # nombres repetidos son accesos directos a lo mismo
    nombres = list(dict.fromkeys(a["nombre"] for a in permitidas))
    por_nombre = {}
    for a in permitidas:
        por_nombre.setdefault(a["nombre"], a)
    por_siglas = [n for n in nombres if coincide_por_siglas(limpio, n)]
    if len(por_siglas) == 1:
        return por_nombre[por_siglas[0]], None
    if es_generico(buscado):
        opciones = opciones_genericas(buscado, permitidas)
        if len(opciones) == 1:
            return por_nombre[opciones[0]], None
        # sin categoría ni nombre que lo contenga no se ofrecen parecidos sueltos ("editor" -> "Edition"):
        # mejor una pregunta abierta
        return None, {"ok": False, "error": f"'{nombre}' es genérico; pregunta a Reizo cuál quiere",
                      "coincidencias": opciones[:8]}
    candidatos = [c for c in process.extract(limpio, nombres, scorer=fuzz.WRatio, processor=normalizar, limit=10)
                  if c[1] >= 70]
    if not candidatos:
        return None, {"ok": False, "error": "No encontré esa app",
                      "coincidencias": [c[0] for c in process.extract(limpio, nombres, scorer=fuzz.WRatio,
                                                                      processor=normalizar, limit=3)]}
    # solo se abre sin preguntar si una única app "cubre bien" lo buscado; las variantes de arquitectura
    # ("Windows PowerShell (x86)") cuentan como la misma, pero "Outlook (classic)" y "(new)" no
    buenas = {}
    for n, _, _ in candidatos:
        if cubre_bien(limpio, n):
            buenas.setdefault(re.sub(r"\s*\((x86|x64|64 ?bits?|32 ?bits?)\)", "", n, flags=re.I), n)
    if len(buenas) == 1:
        return por_nombre[next(iter(buenas.values()))], None
    return None, {"ok": False, "error": "No estoy seguro de cuál es; pregunta a Reizo",
                  "coincidencias": [c[0] for c in candidatos[:5]]}


def preparar_apertura(nombre, apps):
    """elegir_app más la confirmación de las apps sensibles (consolas). Devuelve (app, None) o (None, error)."""
    app, error = elegir_app(nombre, apps)
    if error:
        return None, error
    if nivel_app(app["id"]) == "confirmar":
        pregunta = f"  ¿Abrir {app['nombre']}? Es una consola que puede ejecutar comandos. (s/n) "
        if input(pregunta).strip().lower() != "s":
            return None, {"ok": False, "error": f"Reizo no autorizó abrir {app['nombre']}."}
    return app, None


def abrir_app(nombre: str, argumentos: str = ""):
    app, error = preparar_apertura(nombre, _cache_apps)
    if error:
        return error
    subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app['id']}"])
    return {"ok": True, "app_abierta": app["nombre"]}


def volumen(accion: str, cantidad: int | None = None):
    vol = AudioUtilities.GetSpeakers().EndpointVolume
    actual = round(vol.GetMasterVolumeLevelScalar() * 100)
    if accion in ("subir", "bajar"):
        delta = cantidad if cantidad is not None else 10
        nuevo = max(0, min(100, actual + (delta if accion == "subir" else -delta)))
        vol.SetMasterVolumeLevelScalar(nuevo / 100, None)
    elif accion == "fijar" and cantidad is not None:
        vol.SetMasterVolumeLevelScalar(max(0, min(100, cantidad)) / 100, None)
    elif accion == "silenciar":
        vol.SetMute(1, None)
    elif accion == "activar":
        vol.SetMute(0, None)
    return {"ok": True,
            "volumen_actual": round(vol.GetMasterVolumeLevelScalar() * 100),
            "silenciado": bool(vol.GetMute())}


def ver_pantalla(region: str = "ventana_activa", presupuesto_tokens: int = 560, cuadricula: bool = False):
    global _presupuesto_imagen
    presupuesto = min(PRESUPUESTOS, key=lambda p: abs(p - int(presupuesto_tokens)))  # el admitido más cercano
    # vision.ultima_captura guarda info para convertir coordenadas del mouse
    try:
        data_url, info = capturar(region, cuadricula=bool(cuadricula))
    except CapturaBloqueada as e:
        return {"ok": False, "bloqueado": True, "error": str(e)}
    _presupuesto_imagen = presupuesto
    # "_imagen" no va al texto del historial: atender la convierte en una parte de imagen del mensaje
    resultado = {"ok": True, "ancho": info["ancho"], "alto": info["alto"], "presupuesto_tokens": presupuesto,
                 "cuadricula": bool(cuadricula), "_imagen": data_url}
    if info["ventanas_tapadas"]:
        resultado["nota"] = f"{info['ventanas_tapadas']} ventana(s) con contenido sensible aparecen tapadas en negro."
    return resultado


IMPLEMENTACIONES = {"listar_apps": listar_apps, "abrir_app": abrir_app, "volumen": volumen,
                    "listar_ventanas": listar_ventanas, "enfocar_ventana": enfocar_ventana,
                    "listar_carpeta": listar_carpeta, "leer_archivo": leer_archivo, "buscar_web": buscar_web,
                    "recordar": recordar, "consultar_memoria": consultar_memoria, "ver_pantalla": ver_pantalla,
                    "cerrar_app": cerrar_app, "mover_archivo": mover_archivo, "mouse": mouse, "teclado": teclado,
                    "listar_controles": listar_controles}
# acciones cuyo efecto hay que comprobar antes de darlas por hechas, y herramientas que sirven para comprobarlo
ACCIONES_A_VERIFICAR = {"mouse": {"clic", "doble_clic", "clic_derecho"}, "teclado": {"atajo", "tecla"}}
VERIFICADORAS = {"ver_pantalla", "listar_controles", "listar_ventanas"}
MAX_RECORDATORIOS = 2


# ---------- Modelo y prompt ----------

# parámetros y avisos de versión en modelo.py y config.json (LlamaRapida sobrescribe un método interno
# de llama-cpp-python 0.3.36). La visión usa el handler multimodal solo cuando el historial tiene una imagen.
llm = crear_llm(CONFIG)
vision = ManejadorVision(CONFIG["mmproj"]) if CONFIG.get("mmproj") else None
_presupuesto_imagen = 560
emergencia = Emergencia(CATALOGO["limites"]["atajo_emergencia"])
llm.interrumpir = emergencia.comprobar  # se comprueba en cada token que genera el modelo
herramientas_grupo4.comprobar_emergencia = emergencia.comprobar  # y dentro de las herramientas largas
sincronizar_apps()

ESQUEMA_ACCION = {
    "type": "object",
    "properties": {
        "pensamiento": {"type": "string", "maxLength": 120},
        "herramienta": {"type": "string", "enum": sorted(HERRAMIENTAS)},
        "argumentos": {"type": "object"},
        "mensaje_final": {"type": "string"},  # opcional: respuesta directa en tareas de un paso
    },
    "required": ["pensamiento", "herramienta", "argumentos"],
}
# herramientas cuyo resultado se puede citar en mensaje_final con {campo}
CON_MARCADORES = {"abrir_app", "volumen"}

def prompt_sistema():
    lineas = [
        "Eres el asistente de escritorio de Reizo en Windows. Hablas en español, breve y cercano.",
        "En cada turno respondes SOLO con un JSON: {pensamiento, herramienta, argumentos} y, a veces, mensaje_final.",
        "'pensamiento' es una frase corta (máximo 120 caracteres) sobre qué vas a hacer y por qué.",
        "Cuando termines o si solo es conversación, usa 'finalizar' con tu respuesta en 'mensaje'.",
        "Usa 'mensaje_final' solo en tareas de un paso: si una sola herramienta resuelve el pedido (por ejemplo "
        "'pon el volumen al 30'), escribe ahí la respuesta para Reizo; si la herramienta tiene éxito se le mostrará "
        "sin consultarte de nuevo. Puedes incluir campos del resultado entre llaves, tal como aparecen en 'Devuelve'; "
        "úsalos siempre que no sepas el valor final, por ejemplo al subir o bajar el volumen: 'Listo, subí el volumen "
        "a {volumen_actual}%' o 'Abrí {app_abierta}'. No lo uses en tareas de "
        "varios pasos, cuando tengas que interpretar el resultado (por ejemplo con listar_apps) ni con 'finalizar'.",
        "Ejemplo para 'baja un poco el volumen': " + json.dumps(
            {"pensamiento": "Bajo el volumen 10 puntos; el nivel final lo pone el marcador.",
             "herramienta": "volumen", "argumentos": {"accion": "bajar", "cantidad": 10},
             "mensaje_final": "Listo, bajé el volumen a {volumen_actual}%."}, ensure_ascii=False),
        "Si una herramienta responde que algo está bloqueado o que Reizo no lo autorizó, no lo intentes por otro "
        "camino (otra app, Ejecutar, búsquedas): explícaselo y usa 'finalizar'.",
        "Para hacer clic en una app, usa primero listar_controles y luego mouse con 'control' (el nombre exacto) e "
        "'id_ventana'; usa ver_pantalla con cuadrícula y coordenadas solo si el control no aparece. Después de un "
        "clic o un atajo, comprueba el resultado con listar_controles, ver_pantalla o listar_ventanas antes de decir "
        "que funcionó; si no cambió lo esperado, dilo.",
        "Herramientas disponibles:",
    ]
    for h in HERRAMIENTAS.values():
        linea = f"- {h['nombre']}: {h['descripcion']} Parámetros: {json.dumps(h['parametros'], ensure_ascii=False)}"
        if h["nombre"] in CON_MARCADORES:
            linea += f" Devuelve: {h['retorno']}"
        lineas.append(linea)
    # memorias de tipo preferencia y alias guardadas en sesiones anteriores
    recuerdos = memoria.memorias_para_prompt()
    if recuerdos:
        lineas.append("Lo que ya sabes de Reizo (tenlo en cuenta al interpretar sus pedidos):")
        lineas += [f"- {r}" for r in recuerdos]
    return "\n".join(lineas)


def pedir_accion(historial):
    parametros = dict(messages=historial, response_format={"type": "json_object", "schema": ESQUEMA_ACCION},
                      temperature=0.3, top_p=0.95, top_k=64, max_tokens=512)
    if vision is not None and any(isinstance(m["content"], list) for m in historial):
        # hay una captura en el historial: va por el handler multimodal (reevalúa todo el prompt)
        vision.fijar_presupuesto(_presupuesto_imagen)
        r = vision(llama=llm, **parametros)
    else:
        r = llm.create_chat_completion(**parametros)
    return json.loads(r["choices"][0]["message"]["content"])


def ejecutar(nombre, args):
    h = HERRAMIENTAS[nombre]
    if h["permiso"] == "confirmar":
        respuesta = input(f"  ¿Ejecutar {nombre} {args}? (s/n) ").strip().lower()
        emergencia.comprobar()  # el atajo pudo pulsarse mientras se esperaba la respuesta
        if respuesta != "s":
            return {"ok": False, "error": "El usuario rechazó la acción"}
    try:
        return IMPLEMENTACIONES[nombre](**args)
    except Detenido:
        raise
    except Exception as e:  # el error vuelve al modelo para que se corrija
        return {"ok": False, "error": str(e)}


def rellenar_marcadores(texto, resultado):
    """Cambia {campo} por resultado[campo]. Devuelve None si algún campo no existe en el resultado,
    para no mostrar una llave suelta; entonces el modelo redacta la respuesta en otro turno."""
    faltan = []

    def valor(m):
        campo = m.group(1)
        if campo not in resultado:
            faltan.append(campo)
            return m.group(0)
        v = resultado[campo]
        return ("sí" if v else "no") if isinstance(v, bool) else str(v)

    rellenado = re.sub(r"\{(\w+)\}", valor, texto)
    return None if faltan else rellenado


def resumir_resultado(nombre, resultado):
    if isinstance(resultado, list):
        nombres = [r.get("nombre", "") if isinstance(r, dict) else str(r) for r in resultado]
        muestra = ", ".join(nombres[:8]) + ("…" if len(nombres) > 8 else "")
        return f"Resultado de {nombre} (resumido): {len(resultado)} elementos: {muestra}"
    texto = resultado if isinstance(resultado, str) else json.dumps(resultado, ensure_ascii=False)
    return f"Resultado de {nombre} (resumido): {texto[:200]}…"


def compactar_historial(historial):
    for m in historial:
        if isinstance(m["content"], list):  # las capturas no se guardan: ocupan contexto y obligan al handler lento
            texto = " ".join(p["text"] for p in m["content"] if p.get("type") == "text")
            m["content"] = texto + " [captura omitida]"
        c = m["content"]
        if m["role"] == "user" and c.startswith("Resultado de ") and len(c) > LIMITE_RESULTADO:
            cabecera, _, cuerpo = c.partition(": ")
            try:
                resultado = json.loads(cuerpo)
            except json.JSONDecodeError:
                resultado = cuerpo
            m["content"] = resumir_resultado(cabecera.removeprefix("Resultado de "), resultado)


def terminar(historial, mensaje, exito, pensamiento):
    """Cierra la tarea sin otra llamada al modelo, dejando en el historial un 'finalizar' coherente."""
    historial.append({"role": "assistant", "content": json.dumps(
        {"pensamiento": pensamiento, "herramienta": "finalizar",
         "argumentos": {"mensaje": mensaje, "exito": exito}}, ensure_ascii=False)})
    return mensaje


MENSAJE_DETENIDO = "Estoy detenido por el atajo de emergencia; no haré nada hasta que escribas 'reanudar'."


def atender(pedido, historial):
    if emergencia.detenido():
        # el atajo se pulsó antes o entre tareas: no se descarta, la tarea nueva no empieza
        print("  [emergencia] agente detenido: la tarea no se ejecuta")
        return MENSAJE_DETENIDO
    historial.append({"role": "user", "content": pedido})
    sin_verificar, recordatorios = None, 0  # último clic o atajo que el modelo aún no comprobó
    try:
        for _ in range(MAX_PASOS):
            emergencia.comprobar()
            accion = pedir_accion(historial)
            historial.append({"role": "assistant", "content": json.dumps(accion, ensure_ascii=False)})
            nombre, args = accion["herramienta"], accion.get("argumentos", {})
            print(f"  [{nombre}] {accion['pensamiento']}")
            if nombre == "finalizar":
                if sin_verificar and args.get("exito", True) and recordatorios < MAX_RECORDATORIOS:
                    # no se da por hecho un clic o atajo sin mirar su efecto
                    recordatorios += 1
                    print("  [verificación] el ejecutor pide comprobar el resultado antes de confirmar")
                    historial.append({"role": "user", "content": f"Todavía no comprobaste el efecto de {sin_verificar}. "
                                      "Usa listar_controles, ver_pantalla o listar_ventanas antes de confirmar que "
                                      "funcionó."})
                    continue
                return args.get("mensaje", "")
            emergencia.comprobar()
            resultado = ejecutar(nombre, args)
            imagen = resultado.pop("_imagen", None) if isinstance(resultado, dict) else None
            texto = f"Resultado de {nombre}: {json.dumps(resultado, ensure_ascii=False)}"
            historial.append({"role": "user", "content": [{"type": "text", "text": texto},
                                                          {"type": "image_url", "image_url": {"url": imagen}}]
                              if imagen else texto})
            if isinstance(resultado, dict) and resultado.get("bloqueado"):
                # el ejecutor corta: el modelo no recibe más pasos para buscar otro camino
                memoria.registrar_bloqueo(pedido, nombre, args, resultado.get("error", ""))
                print("  [bloqueado] tarea terminada por el ejecutor")
                return terminar(historial, f"No lo hice: {resultado.get('error', 'está bloqueado por seguridad.')}",
                                False, "Acción bloqueada; el ejecutor terminó la tarea")
            if nombre in VERIFICADORAS:
                sin_verificar = None
            elif args.get("accion") in ACCIONES_A_VERIFICAR.get(nombre, ()) and isinstance(resultado, dict) \
                    and resultado.get("ok"):
                sin_verificar = f"{nombre} {json.dumps(args, ensure_ascii=False)}"
            mensaje_final = accion.get("mensaje_final", "").strip()
            if imagen or sin_verificar:
                mensaje_final = None  # tiene que mirar la captura o comprobar el clic/atajo antes de responder
            elif isinstance(resultado, dict) and resultado.get("ok"):
                mensaje_final = rellenar_marcadores(mensaje_final, resultado)
            else:
                mensaje_final = None
            if mensaje_final:
                # tarea de un paso: se responde sin otra llamada al modelo
                print("  [mensaje_final] respuesta directa, sin volver a llamar al modelo")
                return terminar(historial, mensaje_final, True, "Tarea de un paso completada")
        return terminar(historial, "Me pasé del límite de pasos para esta tarea; mejor dime de otra forma qué "
                        "necesitas.", False, "Límite de pasos alcanzado")
    except Detenido as e:
        demora = (time.perf_counter() - emergencia.momento) * 1000 if emergencia.momento else None
        print(f"  [emergencia] tarea detenida" + (f" ({demora:.0f} ms después del atajo)" if demora else ""))
        return terminar(historial, f"{e} No seguí con la tarea ni haré otras hasta que escribas 'reanudar'.",
                        False, "Detenido por Reizo")
    finally:
        compactar_historial(historial)


if __name__ == "__main__":
    if emergencia.iniciar():
        print(f"Atajo de emergencia activo: {emergencia.atajo}")
    else:
        print(f"Aviso: no pude registrar {emergencia.atajo} (¿lo usa otro programa?); para cortar usa Ctrl+C.")
    historial = [{"role": "system", "content": prompt_sistema()}]
    print("Asistente listo. Escribe 'salir' para terminar.")
    while (pedido := input("\nTú: ").strip()).lower() != "salir":
        if pedido.lower() == "reanudar":
            emergencia.reanudar()
            print("Asistente: Listo, vuelvo a atender pedidos.")
        elif pedido:
            print("Asistente:", atender(pedido, historial))
            historial = historial[:1] + historial[1:][-20:]  # memoria corta: últimos 20 mensajes
