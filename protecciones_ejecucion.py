"""Protecciones deterministas del loop, independientes del modelo."""
import json
import re
import unicodedata

LECTURAS = {"listar_apps", "listar_ventanas", "listar_carpeta", "leer_archivo", "buscar_web",
            "consultar_memoria", "ver_pantalla", "listar_controles", "preguntar_usuario"}
_MOD = r"(?:ctrl|control|alt|shift|may[uú]s|win|windows)"
_KEY = r"(?:[a-z0-9]|f(?:1[0-2]|[1-9])|enter|intro|tab|esc|escape|supr|delete|backspace|espacio|space|inicio|fin|home|end|repag|avpag|arriba|abajo|izquierda|derecha)"
_SHORTCUT = re.compile(rf"^\s*{_MOD}(?:\s*\+\s*|\s+)(?:{_MOD}(?:\s*\+\s*|\s+))*{_KEY}\s*$", re.I)
_VOLUME_ACTION = r"(?:ajust[eé]|ajustad[oa]|cambi[eé]|cambiad[oa]|sub[ií]|subid[oa]|baj[eé]|bajad[oa]|puse|puesto|silenci[eé]|silenciad[oa]|activ[eé]|activad[oa]|desactiv[eé]|desactivad[oa])"
_CLAIMS = {
    "volumen": re.compile(rf"(?:\b{_VOLUME_ACTION}\b.{{0,35}}\b(?:volumen|sonido)\b|\b(?:volumen|sonido)\b.{{0,20}}\b(?:est[aá]|qued[oó])\b)", re.I),
    "abrir_app": re.compile(r"(?:\b(?:abr[ií]|inici[eé]|lanc[eé])\b|\bhe abierto\b|"
                             r"\b(?:aplicaci[oó]n|app|programa|spotify|calculadora|bloc|chrome|discord)\b.{0,35}"
                             r"\b(?:se (?:ha )?abri[oó]|se ha abierto|est[aá] abiert[oa])\b|"
                             r"\babiert[oa]\b.{0,20}\bcorrectamente\b)", re.I),
    "enfocar_ventana": re.compile(r"(?:\b(?:traje|puse)\b.{0,30}\bal frente\b|\bhe tra[ií]do\b.{0,30}\bal frente\b|"
                                  r"\b(?:enfoqu[eé]|enfocad[oa])\b|\b(?:ventana|bloc|aplicaci[oó]n|app|programa|terminal)\b.{0,30}\bal frente\b)", re.I),
    "cerrar": re.compile(r"\b(cerr[eé]|cerrad[oa])\b", re.I),
    "mover_archivo": re.compile(r"\b(mov[ií]|movid[oa]|renombr[eé]|renombrad[oa])\b", re.I),
    "teclado": re.compile(r"(?:\b(?:guard[eé]|he guardado|guardad[oa])\b.{0,35}\b(?:archivo|documento|cambios|nota|texto)\b|"
                           r"\b(?:archivo|documento|cambios|nota|texto)\b.{0,35}\b(?:guardad[oa]|se guard[oó])\b|"
                           r"\b(?:escrib[ií]|escrit[oa]|puls[eé]|presion[eé])\b)", re.I),
    "mouse": re.compile(r"(?:\b(?:hice|realic[eé])\b.{0,12}\bclic\b|\bhe hecho\b.{0,12}\bclic\b|"
                        r"\bclic\b.{0,12}\b(?:hecho|realizado)\b|\b(?:desplac[eé]|desplazad[oa])\b)", re.I),
    "registro_habitos": re.compile(r"\b(registro|h[aá]bitos).*(paus|reanuda)", re.I),
}

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
    """Registra evidencia; True al acumular dos alternativas fallidas en esta tarea."""
    if resultado_verificado(nombre, args, resultado):
        estado["verificadas"].add(categoria(nombre, args))
        return False
    fallo = isinstance(resultado, dict) and (resultado.get("ok") is False or resultado.get("efecto_visible") is False)
    if not fallo or nombre in LECTURAS - {"listar_controles"} or resultado.get("bloqueado") or resultado.get("rechazado"):
        return False
    estado["fallos"].add(nombre + ":" + json.dumps(args, sort_keys=True, ensure_ascii=False))
    return len(estado["fallos"]) >= 2

def afirmaciones_sin_evidencia(mensaje, verificadas):
    texto = unicodedata.normalize("NFC", str(mensaje or ""))
    afirmadas = {cat for cat, patron in _CLAIMS.items() if patron.search(texto)}
    return sorted(afirmadas - set(verificadas))

def validar_finalizacion(estado, mensaje, exito):
    faltan = afirmaciones_sin_evidencia(mensaje, estado["verificadas"]) if exito else []
    if not faltan:
        return True, ""
    estado["correcciones"] += 1
    lista = ", ".join(faltan)
    return False, (f"No puedo confirmar que esté hecho: el código no verificó el efecto de {lista}. "
                   "Ejecuta y verifica la acción, o explica que no pudiste comprobarla.")
