"""
Camino rápido: pedidos simples que el código entiende sin ninguna ambigüedad y que no necesitan al modelo
(cerebro/decisiones/camino-rapido.md; decisión del usuario del 2026-10-11).

Solo sustituye la ELECCIÓN de la herramienta: la acción pasa por el mismo ejecutor (permisos, protecciones,
confirmaciones físicas, registro y respuesta verificada) en agente_minimo.atender(). Reconoce solo frases ENTERAS de
una lista blanca; cualquier palabra de más (negación, condición, otra acción, rutas, URLs, números fuera de rango) no
coincide y el pedido va al modelo. Solo mira el pedido del usuario, nunca texto externo.

Entran: volumen (subir, bajar, fijar 0–100 con cifras o palabras, máximo, silenciar, activar, consultar), abrir una
app que el resolvedor actual da sin dudas, y pausar o reanudar el registro de hábitos. En la pausa del modo juego,
solo el volumen (sin cargar el modelo ni usar la GPU).
"""
import re
import unicodedata

VOLUMEN = r"(?:el )?(?:volumen|sonido|audio)(?: del (?:equipo|sistema|pc|ordenador|computador|computadora))?"
UNIDADES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
            "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
            "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
            "veintiun": 21, "veintiuno": 21, "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24,
            "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29}
DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80,
           "noventa": 90}
_NUMERO = (r"(?P<n>\d{1,3}|cien|[a-z]+(?: y [a-z]+)?)(?: ?%| por ?ciento)?")
# palabras que nunca aparecen en un nombre de app pedido sin ambigüedad: el pedido va al modelo
_NO_EN_NOMBRE = {"y", "e", "o", "u", "ni", "no", "si", "luego", "despues", "tambien", "pero", "con", "en", "para",
                 "que", "cuando", "mientras", "antes", "sin", "por", "otra", "otro", "vez"}

PATRONES = [  # (expresión de la frase entera, herramienta, argumentos o función de los grupos)
    (rf"(?:baja|bajale)(?: un poco)? {VOLUMEN}(?: un poco)?", "volumen", {"accion": "bajar", "cantidad": 10}),
    (rf"(?:sube|subele)(?: un poco)? {VOLUMEN}(?: un poco)?", "volumen", {"accion": "subir", "cantidad": 10}),
    (rf"(?:pon|ponme|deja|dejame|ajusta|fija) {VOLUMEN} (?:al|a|en) maximo", "volumen", {"accion": "fijar", "cantidad": 100}),
    (rf"(?:pon|ponme|deja|dejame|ajusta|fija) {VOLUMEN} (?:al|a|en) {_NUMERO}", "volumen", "fijar"),
    (rf"(?:silencia|mutea)(?: {VOLUMEN}| el equipo)?", "volumen", {"accion": "silenciar"}),
    (rf"(?:quita|quitale) el silencio|(?:vuelve a )?(?:activar?|reactiva) {VOLUMEN}|desilencia(?: {VOLUMEN})?",
     "volumen", {"accion": "activar"}),
    (rf"(?:a cuanto|en cuanto|a que nivel) esta {VOLUMEN}", "volumen", {"accion": "consultar"}),
    (r"(?:abre|abreme|inicia|iniciame|lanza|arranca) (?:la (?:aplicacion|app) (?:de )?|el programa (?:de )?)?"
     r"(?P<app>[a-z0-9][a-z0-9 .+-]{0,40})", "abrir_app", "app"),
    (r"deja de registrar lo que hago|(?:pausa|deten|para) el registro(?: de (?:mis )?habitos)?", "registro_habitos",
     {"accion": "pausar"}),
    (r"(?:reanuda|retoma|vuelve a activar|activa) el registro(?: de (?:mis )?habitos)?|vuelve a registrar lo que hago",
     "registro_habitos", {"accion": "reanudar"}),
]
_COMPILADOS = [(re.compile(p), h, a) for p, h, a in PATRONES]


def normalizar(texto):
    """Minúsculas, sin tildes, sin «Cacao» delante, sin «por favor», sin puntuación al principio ni al final."""
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", t).strip(" .!?¡¿,;:")
    t = re.sub(r"^(?:oye )?cacao[ ,]+", "", t)
    t = re.sub(r"^(?:por favor[ ,]+)|(?:[ ,]+por favor)$", "", t).strip(" .!?¡¿,;:")
    return t


def numero(texto):
    """0–100 con cifras («30») o palabras («cuarenta y cinco», «cien»); None si no es exacto o está fuera de rango."""
    t = texto.strip()
    if t.isdigit():
        n = int(t)
    elif t == "cien":
        n = 100
    elif t in UNIDADES:
        n = UNIDADES[t]
    elif t in DECENAS:
        n = DECENAS[t]
    else:
        partes = t.split(" y ")
        if len(partes) != 2 or partes[0] not in DECENAS or partes[1] not in UNIDADES or UNIDADES[partes[1]] > 9 \
                or UNIDADES[partes[1]] == 0:
            return None
        n = DECENAS[partes[0]] + UNIDADES[partes[1]]
    return n if 0 <= n <= 100 else None


def reconocer(pedido, resolver_app=None, solo=None):
    """(herramienta, argumentos) si el pedido entero es uno de la lista blanca; si no, None (va al modelo).
    resolver_app(nombre) -> True solo si el resolvedor actual da una única app sin dudas (sin él, abrir_app no entra).
    solo: herramientas permitidas (en la pausa del modo juego, {"volumen"})."""
    texto = normalizar(pedido)
    if not texto or len(texto) > 80:
        return None
    for patron, herramienta, argumentos in _COMPILADOS:
        if solo is not None and herramienta not in solo:
            continue
        m = patron.fullmatch(texto)
        if not m:
            continue
        if argumentos == "fijar":
            n = numero(m.group("n"))
            return (herramienta, {"accion": "fijar", "cantidad": n}) if n is not None else None
        if argumentos == "app":
            nombre = m.group("app").strip()
            palabras = nombre.split()
            if not palabras or len(palabras) > 4 or _NO_EN_NOMBRE & set(palabras) or "www" in nombre \
                    or re.search(r"\.(?:com|net|org|exe|txt|es|io)\b", nombre) or resolver_app is None \
                    or not resolver_app(nombre):
                return None
            return herramienta, {"nombre": nombre}
        return herramienta, dict(argumentos)
    return None


def respuesta(herramienta, argumentos, resultado):
    """Texto fijo con el resultado YA verificado por el ejecutor."""
    accion = argumentos.get("accion")
    if herramienta == "volumen":
        if accion == "silenciar":
            return "Listo, silencié el sonido."
        if accion == "consultar":
            return (f"El volumen está al {resultado.get('volumen_actual')}%"
                    + (", pero silenciado." if resultado.get("silenciado") else "."))
        if accion == "activar":
            return f"Listo, volví a activar el sonido; está al {resultado.get('volumen_actual')}%."
        return f"Listo, puse el volumen al {resultado.get('volumen_actual')}%."
    if herramienta == "abrir_app":
        return f"Listo, abrí {resultado.get('app_abierta')}."
    if herramienta == "registro_habitos":
        return ("Listo, pausé el registro de hábitos." if accion == "pausar"
                else "Listo, reanudé el registro de hábitos.")
    return "Listo."
