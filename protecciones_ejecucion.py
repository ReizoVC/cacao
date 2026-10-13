"""Protecciones deterministas del loop, independientes del modelo."""
import json
import re
import unicodedata

LECTURAS = {"listar_apps", "listar_ventanas", "listar_carpeta", "leer_archivo", "buscar_web",
            "consultar_memoria", "ver_pantalla", "listar_controles", "preguntar_usuario", "posicion_mouse"}
# caminos distintos que pueden fallar en una tarea antes de que el ejecutor pare y pida a Reizo que le explique cómo
MAX_ALTERNATIVAS = 5
_MOD = r"(?:ctrl|control|alt|shift|may[uú]s|win|windows)"
_KEY = r"(?:[a-z0-9]|f(?:1[0-2]|[1-9])|enter|intro|tab|esc|escape|supr|delete|backspace|espacio|space|inicio|fin|home|end|repag|avpag|arriba|abajo|izquierda|derecha)"
_SHORTCUT = re.compile(rf"^\s*{_MOD}(?:\s*\+\s*|\s+)(?:{_MOD}(?:\s*\+\s*|\s+))*{_KEY}\s*$", re.I)
_VOLUME_ACTION = r"(?:ajust[eé]|ajustad[oa]|cambi[eé]|cambiad[oa]|sub[ií]|subid[oa]|baj[eé]|bajad[oa]|puse|puesto|silenci[eé]|silenciad[oa]|activ[eé]|activad[oa]|desactiv[eé]|desactivad[oa])"
_APPS = r"(?:aplicaci[oó]n|app|programa|spotify|calculadora|bloc|chrome|discord)"
_TEXTOS = r"(?:archivo|documento|cambios|nota|texto)"
# Cada patrón marca con (?P<v>…) la palabra que afirma la acción y con (?P<n>…) el sustantivo del volumen. Coincidir
# no basta: _afirma() mira la frase alrededor de esa palabra (cláusula, negación, pregunta, modo y auxiliar del
# participio), así «la versión escrita», «la Grabadora de sonido está instalada» o «no he podido verificar que se
# haya cerrado» no cuentan como un «hecho».
_CLAIMS = {cat: [re.compile(p, re.I) for p in patrones] for cat, patrones in {
    "volumen": [rf"\b(?P<v>{_VOLUME_ACTION})\b.{{0,35}}?\b(?P<n>volumen|sonido)\b",
                r"\b(?P<n>volumen|sonido)\b.{0,20}\b(?P<v>est[aá]|qued[oó])\b",
                r"\b(?P<n>volumen|sonido)\b.{0,20}\b(?:al?|en)\s*\d{1,3}\s*%"],
    "abrir_app": [r"\b(?P<v>abr[ií]|inici[eé]|lanc[eé])\b", r"\bhe (?P<v>abierto)\b",
                  rf"\b{_APPS}\b.{{0,35}}\bse (?:ha )?(?P<v>abri[oó])\b",
                  rf"\b{_APPS}\b.{{0,35}}\bse ha (?P<v>abierto)\b",
                  rf"\b{_APPS}\b.{{0,35}}\best[aá] (?P<v>abiert[oa])\b",
                  r"\b(?:spotify|calculadora|bloc de notas|chrome|discord)\b.{0,20}\b(?P<v>abiert[oa])\b",
                  r"\b(?P<v>abiert[oa])\b.{0,20}\bcorrectamente\b"],
    "enfocar_ventana": [r"\b(?P<v>traje|puse)\b.{0,30}\bal frente\b", r"\bhe (?P<v>tra[ií]do)\b.{0,30}\bal frente\b",
                        r"\b(?P<v>enfoqu[eé]|enfocad[oa])\b",
                        r"\b(?:ventana|bloc|aplicaci[oó]n|app|programa|terminal)\b.{0,30}\b(?P<v>al frente)\b"],
    "cerrar": [r"\b(?P<v>cerr[eé]|cerrad[oa])\b"],
    "mover_archivo": [r"\b(?P<v>mov[ií]|movid[oa]|renombr[eé]|renombrad[oa])\b"],
    "teclado": [rf"\b(?P<v>guard[eé]|guardad[oa])\b.{{0,35}}\b{_TEXTOS}\b",
                rf"\bhe (?P<v>guardado)\b.{{0,35}}\b{_TEXTOS}\b",
                rf"\b{_TEXTOS}\b.{{0,35}}\b(?P<v>guardad[oa])\b",
                rf"\b{_TEXTOS}\b.{{0,35}}\bse (?P<v>guard[oó])\b",
                r"\b(?P<v>escrib[ií]|escrit[oa]|puls[eé]|presion[eé])\b"],
    "mouse": [r"\b(?P<v>hice|realic[eé])\b.{0,12}\bclic\b", r"\bhe (?P<v>hecho)\b.{0,12}\bclic\b",
              r"\bclic\b.{0,12}\b(?P<v>hecho|realizado)\b", r"\b(?P<v>desplac[eé]|desplazad[oa])\b"],
    "registro_habitos": [r"\b(?:registro|h[aá]bitos)\b.*(?P<v>paus|reanuda)"],
}.items()}
# Análisis de la frase con clases cerradas del español (conjunciones, negadores, auxiliares), no con sinónimos de
# las acciones.
_LIMITE_CLAUSULA = re.compile(r"[.;:!?¿¡\n,]|\b(?:pero|sino|aunque|y|e|luego|entonces)\b", re.I)
_NEGADORES = {"no", "nunca", "tampoco", "jamás", "jamas", "ni", "sin"}
# «no puedo / no he podido verificar» en la frase: lo dicho en ella queda como no comprobado, no como hecho
_SIN_COMPROBAR = re.compile(r"\b(?:no|ni)\b(?:\s+\w+){0,3}?\s+(?:verific|comprob|confirm|asegur)\w*", re.I)
_PARTICIPIO = re.compile(r"(?:ad|[ií]d|it|iert|uest|ech)[oa]s?$", re.I)
_INFINITIVO_GERUNDIO = re.compile(r"(?:ar|er|ir|ando|iendo)$", re.I)
_AUX_HECHO = {"he", "has", "ha", "hemos", "han", "había", "habían", "está", "esta", "están", "estan", "estaba",
              "estaban", "estuvo", "quedó", "quedo", "quedaron", "queda", "quedan", "fue", "fueron", "sido", "dejé"}
_AUX_SUPUESTO = {"haya", "hayas", "hayan", "hayamos", "hubiera", "hubieran", "hubiese", "hubiesen", "esté", "estén",
                 "quede", "queden"}
_COPULA = {"es", "son", "era", "eran", "será", "sería", "hay"}  # «la versión escrita es…» describe, no informa
_ATONAS = {"se", "lo", "la", "los", "las", "le", "les", "me", "te", "ya", "bien", "todo", "también", "ahora",
           "correctamente"}


def _palabras(texto):
    return [m.group().lower() for m in re.finditer(r"\w+", texto)]


def _afirma(texto, m):
    """True si la coincidencia m afirma la acción como hecha: no la niega, no pregunta, no la supone (subjuntivo) y,
    si es un participio, no lo usa solo como adjetivo («la versión escrita»)."""
    grupo = "v" if "v" in m.re.groupindex else None
    inicio, fin = m.span(grupo) if grupo else m.span()
    frase_ini = max(texto.rfind(s, 0, inicio) for s in ".!?\n") + 1
    frase_fin = min((i for i in (texto.find(s, fin) for s in ".!?\n") if i >= 0), default=len(texto))
    frase = texto[frase_ini:frase_fin + 1]
    if "¿" in frase or frase.rstrip().endswith("?") or _SIN_COMPROBAR.search(frase):
        return False
    # la cláusula que contiene la palabra: de la última pausa o conjunción anterior a la siguiente
    claus_ini = max([frase_ini] + [x.end() for x in _LIMITE_CLAUSULA.finditer(texto, frase_ini, inicio)])
    siguiente = _LIMITE_CLAUSULA.search(texto, fin)
    claus_fin = siguiente.start() if siguiente else len(texto)
    antes = _palabras(texto[claus_ini:inicio])
    if _NEGADORES & set(antes + _palabras(texto[inicio:max(fin, m.end())])):
        return False
    # «grabadora de sonido», «tarjeta de sonido»: el sustantivo sin artículo tras «de» complementa a otro
    if "n" in m.re.groupindex:
        previas = _palabras(texto[claus_ini:m.start("n")])
        if previas and previas[-1] == "de":
            return False
    if not grupo:
        return True
    palabra = re.search(r"\w*$", texto[:inicio]).group() + m.group(grupo) + re.match(r"\w*", texto[fin:]).group()
    if " " in palabra:
        return True  # «al frente»
    if _INFINITIVO_GERUNDIO.search(palabra):
        return False  # «pausar», «cerrando»
    if not _PARTICIPIO.search(palabra):
        return True  # forma personal: «cerré», «se abrió», «moví»
    # participio: hecho con auxiliar («he escrito», «quedó guardado», «está cerrada»), supuesto en subjuntivo
    # («se haya cerrado»), o elíptico al final de una cláusula corta («Calculadora abierta.», «Texto escrito.»)
    for p in reversed(antes):
        if p in _ATONAS:
            continue
        if p in _AUX_SUPUESTO:
            return False
        if p in _AUX_HECHO:
            return True
        break
    resto = [p for p in _palabras(texto[fin:claus_fin]) if p not in _ATONAS]
    clausula = _palabras(texto[claus_ini:claus_fin])
    return not resto and len(clausula) <= 5 and not _COPULA & set(clausula)


# cerrar_app con forzar=true termina el proceso (puede perder trabajo sin guardar): solo si el pedido de Reizo lo pide
# con palabras explícitas. Se compara sin tildes y en minúsculas.
_PIDE_FORZAR = re.compile(r"\b(?:forz\w*|fuerz\w*|a la fuerza|no (?:me )?(?:responde|contesta|reacciona)\w*|"
                          r"colgad[oa]s?|se (?:ha )?colg\w*|congelad[oa]s?|se (?:ha )?congel\w*|trabad[oa]s?|"
                          r"se (?:ha )?trab[oóa]\w*|bloquead[oa]s?|matal[oa]|mata(?:r)? (?:el|la|ese|esa) "
                          r"(?:proceso|programa|app|aplicacion)|kill)\b")


def pide_forzar(pedido):
    return bool(_PIDE_FORZAR.search(_sin_tildes(pedido)))


def quitar_forzar_no_pedido(nombre, args, pedido):
    """(args, nota). Si el modelo pide cerrar_app con forzar=true y el pedido no lo pide, devuelve args sin forzar
    (cierre normal) y una nota para el registro; si no, (args, None). La confirmación del cierre forzado no cambia."""
    if nombre != "cerrar_app" or not args.get("forzar") or pide_forzar(pedido):
        return args, None
    return {**args, "forzar": False}, "forzar=true ignorado: el pedido no pide forzar el cierre; cierre normal"


# cerrar_app solo si el pedido de Reizo expresa intención de cerrar (Qwen cerró apps que nadie pidió cerrar cuando
# algo no funcionaba: #19 s33, #43 s22, #58 s22). Se compara sin tildes y en minúsculas.
_PIDE_CERRAR = re.compile(r"\b(?:cierr\w*|cerr\w*|sal(?:ir|te)? de|quita(?:lo|la|r)?|termin(?:a|ar|alo|ala)|"
                          r"mat(?:a|ar|alo|ala)|apag\w* (?:la|el|esa|ese) (?:app|aplicacion|programa|ventana)|"
                          r"close|kill)\b")
CIERRE_NO_PEDIDO = ("El usuario no pidió cerrar ninguna app; no cierres nada. Si no puedes hacer lo pedido, "
                    "explícalo y pregunta.")


def _sin_tildes(texto):
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def pide_cerrar(pedido):
    return bool(_PIDE_CERRAR.search(_sin_tildes(pedido)))


def cierre_no_pedido(nombre, pedido):
    """Resultado para el modelo si es cerrar_app y el pedido no expresa intención de cerrar; si no, None. No ejecuta
    nada ni pregunta al usuario. Sin 'bloqueado': el modelo sigue y puede explicarlo y preguntar."""
    if nombre != "cerrar_app" or pide_cerrar(pedido):
        return None
    return {"ok": False, "cierre_no_pedido": True, "error": CIERRE_NO_PEDIDO}


def parece_atajo(texto):
    return isinstance(texto, str) and bool(_SHORTCUT.fullmatch(texto))

def nueva_proteccion():
    return {"verificadas": set(), "fallos": set(), "correcciones": 0}

def categoria(nombre, args=None):
    return "cerrar" if nombre == "cerrar_app" else nombre

def resultado_verificado(nombre, args, resultado):
    if nombre in LECTURAS or not isinstance(resultado, dict) or resultado.get("ok") is False:
        return False
    if "efecto_visible" in resultado:
        return bool(resultado["efecto_visible"])
    requisitos = {
        "volumen": ("volumen_actual", "silenciado"), "abrir_app": ("app_abierta",),
        "enfocar_ventana": ("ok",), "cerrar_app": ("cerrada",), "mover_archivo": ("ruta_final",),
        "ejecutar_powershell": ("codigo_salida",), "registro_habitos": ("registrando",),
        "recordar": ("id",), "deshacer_movimiento": ("deshechos",),
    }
    campos = requisitos.get(nombre)
    return bool(campos and all(c in resultado for c in campos))

def registrar_resultado(estado, nombre, args, resultado):
    """Registra evidencia; True al acumular MAX_ALTERNATIVAS alternativas fallidas en esta tarea."""
    if resultado_verificado(nombre, args, resultado):
        estado["verificadas"].add(categoria(nombre, args))
        return False
    fallo = isinstance(resultado, dict) and (resultado.get("ok") is False or resultado.get("efecto_visible") is False)
    if not fallo or nombre in LECTURAS - {"listar_controles"} or resultado.get("bloqueado") or resultado.get("rechazado"):
        return False
    estado["fallos"].add(nombre + ":" + json.dumps(args, sort_keys=True, ensure_ascii=False))
    return len(estado["fallos"]) >= MAX_ALTERNATIVAS

def afirmaciones_sin_evidencia(mensaje, verificadas):
    texto = unicodedata.normalize("NFC", str(mensaje or ""))
    afirmadas = set()
    for cat, patrones in _CLAIMS.items():
        if any(_afirma(texto, m) for patron in patrones for m in patron.finditer(texto)):
            afirmadas.add(cat)
    return sorted(afirmadas - set(verificadas))

def validar_finalizacion(estado, mensaje, exito):
    faltan = afirmaciones_sin_evidencia(mensaje, estado["verificadas"]) if exito else []
    if not faltan:
        return True, ""
    estado["correcciones"] += 1
    lista = ", ".join(faltan)
    return False, (f"No puedo confirmar que esté hecho: el código no verificó el efecto de {lista}. "
                   "Ejecuta y verifica la acción, o explica que no pudiste comprobarla.")
