"""
Pruebas sin modelo de autocompletar_login.py, con un Chrome simulado (no hace clics ni pulsa teclas de verdad):
  1. cuándo actúa: sitio del pedido, Chrome al frente, título del sitio, sin contenido externo, campo visible;
  2. qué campo elige: con contraseña, con buscador en la cabecera, login en dos pasos, campos ambiguos;
  3. la ejecución: clic, flecha abajo y Enter; lista que no aparece, ventana que cambia, lista que sigue abierta;
  4. lo que llega al modelo: nunca el usuario, la contraseña, el título ni los campos;
  5. integración: catálogo, permiso, modo sin confirmación, voz y que esté apagada por defecto;
  6. el ejecutor del agente (extraído con ast, sin modelo): pregunta siempre y no pregunta si el plan falla.
Uso: .venv\\Scripts\\python probar_autocompletar_login.py
"""
import ast
import json
import sys
from pathlib import Path

import autocompletar_login as al
import modo_directo as md

BASE = Path(__file__).parent
resultados = []
SECRETOS = ("reizo@correo.com", "Clave-Secreta-123")


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


def campo(izq, arr, nombre="", contrasena=False, habilitado=True, ancho=300, alto=30):
    return {"rect": (izq, arr, izq + ancho, arr + alto), "es_contrasena": contrasena, "nombre": nombre,
            "habilitado": habilitado}


LOGIN = [campo(800, 20, "Buscar en GitHub"), campo(800, 300, "Nombre de usuario o correo"),
         campo(800, 360, "Contraseña", contrasena=True)]


class ChromeFalso:
    """Ventana 10 de chrome.exe con su página. La lista de cuentas (ventana 99) aparece tras el clic o la flecha
    abajo si hay cuentas guardadas; Enter elige y la cierra. Los valores de los campos existen solo aquí, para
    comprobar que nada los lee."""

    def __init__(self, titulo="Iniciar sesión en GitHub · GitHub - Google Chrome", campos=LOGIN, proceso="chrome.exe",
                 cuentas=True, menu_con="clic", cambia_en=None, enter_cierra=True):
        self.titulo_, self.campos_, self.proceso = titulo, campos, proceso
        self.cuentas, self.menu_con, self.cambia_en, self.enter_cierra = cuentas, menu_con, cambia_en, enter_cierra
        self.frente, self.menu, self.acciones = 10, False, []
        self.valores = dict(zip(SECRETOS, SECRETOS))  # lo que Chrome rellenaría; nada debe leerlo

    def _paso(self, accion):
        self.acciones.append(accion)
        if self.cambia_en == accion:
            self.frente = 20  # otra ventana pasa al frente

    def ventana_al_frente(self):
        return self.frente

    def pid_de(self, hwnd):
        return 1000 + hwnd

    def proceso_de(self, hwnd):
        return self.proceso if hwnd == 10 else "notepad.exe"

    def titulo(self, hwnd):
        return self.titulo_

    def campos(self, hwnd):
        return [dict(c) for c in self.campos_]

    def ventana_en(self, x, y):
        return 10

    def en_la_isla(self, punto):
        return False

    def emergentes(self, hwnd):
        return {99} if self.menu else set()

    def clic(self, x, y):
        self._paso(("clic", x, y))
        if self.cuentas and self.menu_con == "clic":
            self.menu = True

    def tecla(self, nombre):
        self._paso(("tecla", nombre))
        if nombre == "abajo" and self.cuentas and self.menu_con == "abajo":
            self.menu = True
        if nombre in ("enter", "esc") and (self.enter_cierra or nombre == "esc"):
            self.menu = False

    def esperar(self, s):
        pass


PEDIDO = "inicia sesión en github"


def plan(sistema, pedido=PEDIDO, sitio="github", usadas=()):
    return al.planificar(sitio, pedido, list(usadas), sistema)


def pruebas_cuando():
    p, e = plan(ChromeFalso())
    ok("actúa: sitio del pedido, Chrome al frente con ese sitio", p and not e, e)
    ok("el clic va al centro del campo de usuario", p and p["punto"] == (950, 315), p)
    p, e = plan(ChromeFalso(), pedido="abre mi correo", sitio="github")
    ok("sitio que Reizo no nombró: bloqueado", e and e.get("bloqueado"), e)
    p, e = plan(ChromeFalso(), sitio="gi")
    ok("sitio vacío o de 2 letras: error", e and not e.get("bloqueado"), e)
    for fuente in ("leer_archivo", "buscar_web", "ejecutar_powershell"):
        p, e = plan(ChromeFalso(), usadas=["listar_ventanas", fuente])
        ok(f"tras {fuente}: bloqueado", e and e.get("bloqueado"), e)
    p, e = plan(ChromeFalso(), usadas=["listar_ventanas", "enfocar_ventana"])
    ok("tras listar_ventanas y enfocar_ventana: sí actúa", p and not e, e)
    p, e = plan(ChromeFalso(proceso="msedge.exe"))
    ok("Edge al frente: error (solo Chrome)", e and "no es Chrome" in e["error"], e)
    s = ChromeFalso()
    s.frente = 20
    p, e = plan(s)
    ok("otra app al frente: error que pide enfocar", e and "enfocar_ventana" in e["error"], e)
    p, e = plan(ChromeFalso(titulo="Banco - Google Chrome"))
    ok("Chrome al frente con otro sitio: error", e and "no es de github" in e["error"], e)
    p, e = plan(ChromeFalso(titulo="GitHub - Google Chrome"), pedido="entra a github.com con mi cuenta",
                sitio="github.com")
    ok("'github.com' en el pedido vale para el título 'GitHub'", p and not e, e)
    p, e = plan(ChromeFalso(titulo="Sign in · GitLab - Google Chrome"), pedido="inicia sesión en git", sitio="git")
    ok("título de 'GitLab' no vale para 'git' (palabras completas)", e and "no es de git" in e["error"], e)

    class Tapado(ChromeFalso):
        def ventana_en(self, x, y):
            return 30
    p, e = plan(Tapado())
    ok("campo tapado por otra ventana: error", e and "tapado" in e["error"], e)

    class EnIsla(ChromeFalso):
        def en_la_isla(self, punto):
            return True
    p, e = plan(EnIsla())
    ok("punto dentro de la isla: bloqueado", e and e.get("bloqueado"), e)


def pruebas_campo():
    elegido = al.elegir_campo_usuario(LOGIN)
    ok("con contraseña: el campo justo antes (no el buscador de la cabecera)",
       elegido and elegido["nombre"].startswith("Nombre de usuario"))
    lado = [campo(100, 300, "Correo"), campo(500, 300, "Contraseña", contrasena=True), campo(100, 20, "Buscar")]
    ok("usuario y contraseña en la misma fila", al.elegir_campo_usuario(lado)["nombre"] == "Correo")
    ok("login en dos pasos con un solo campo", al.elegir_campo_usuario([campo(800, 300, "")])["rect"][1] == 300)
    dos = [campo(800, 20, "Buscar"), campo(800, 300, "Correo electrónico o teléfono")]
    ok("dos pasos con buscador: el de etiqueta de correo", al.elegir_campo_usuario(dos)["nombre"].startswith("Correo"))
    ambiguo = [campo(800, 20, "Buscar"), campo(800, 300, "Nombre")]
    ok("dos campos sin etiqueta de usuario: ninguno (no adivina)", al.elegir_campo_usuario(ambiguo) is None)
    solo_clave = [campo(800, 360, "Contraseña", contrasena=True)]
    ok("solo el campo de contraseña: ninguno", al.elegir_campo_usuario(solo_clave) is None)
    ok("sin campos: ninguno", al.elegir_campo_usuario([]) is None)
    oculto = [campo(800, 300, "Correo", habilitado=False), campo(800, 360, "Contraseña", contrasena=True)]
    ok("campo deshabilitado: no cuenta", al.elegir_campo_usuario(oculto) is None)
    p, e = plan(ChromeFalso(campos=ambiguo))
    ok("página ambigua: error que pide a Reizo hacer clic", e and "único campo" in e["error"], e)


def pruebas_ejecucion():
    s = ChromeFalso()
    p, _ = plan(s)
    r = al.ejecutar(p, s)
    ok("clic, flecha abajo y Enter: ok", r.get("ok") and [a[0] if a[0] == "clic" else a[1] for a in s.acciones]
       == ["clic", "abajo", "enter"], s.acciones)
    s = ChromeFalso(menu_con="abajo")
    p, _ = plan(s)
    r = al.ejecutar(p, s)
    ok("lista que se abre con la flecha (campo ya enfocado): abajo, abajo, Enter",
       r.get("ok") and [a[1] for a in s.acciones[1:]] == ["abajo", "abajo", "enter"], s.acciones)
    s = ChromeFalso(cuentas=False)
    p, _ = plan(s)
    r = al.ejecutar(p, s)
    ok("sin cuentas guardadas: error y sin Enter", not r["ok"] and ("tecla", "enter") not in s.acciones, r)
    s = ChromeFalso()
    p, _ = plan(s)
    s.frente = 20
    r = al.ejecutar(p, s)
    ok("la ventana cambió antes de actuar: nada", not r["ok"] and s.acciones == [], r)
    s = ChromeFalso(cambia_en=("clic", 950, 315))
    p, _ = plan(s)
    r = al.ejecutar(p, s)
    ok("la ventana cambió con la lista abierta: Esc y sin Enter",
       not r["ok"] and ("tecla", "esc") in s.acciones and ("tecla", "enter") not in s.acciones, s.acciones)
    s = ChromeFalso(enter_cierra=False)
    p, _ = plan(s)
    r = al.ejecutar(p, s)
    ok("la lista sigue abierta tras Enter: error", not r["ok"], r)

    class Detenido(Exception):
        pass

    def emergencia():
        raise Detenido()
    s = ChromeFalso()
    p, _ = plan(s)
    anterior, al.comprobar_emergencia = al.comprobar_emergencia, emergencia
    try:
        al.ejecutar(p, s)
        cortado = False
    except Detenido:
        cortado = True
    finally:
        al.comprobar_emergencia = anterior
    ok("atajo de emergencia: corta antes del clic", cortado and s.acciones == [], s.acciones)


def pruebas_lo_que_ve_el_modelo():
    salidas = []
    for s, kw in ((ChromeFalso(), {}), (ChromeFalso(cuentas=False), {}), (ChromeFalso(titulo="Banco"), {}),
                  (ChromeFalso(), {"pedido": "abre algo"})):
        p, e = plan(s, **kw)
        salidas.append(e if e else al.ejecutar(p, s))
    texto = json.dumps(salidas, ensure_ascii=False)
    ok("ningún resultado trae usuario ni contraseña", not any(x in texto for x in SECRETOS))
    ok("ningún resultado trae el título de la ventana", "Iniciar sesión en GitHub" not in texto and "Banco" not in texto)
    ok("ningún resultado trae los campos de la página", "Nombre de usuario o correo" not in texto)
    claves = {k for r in salidas for k in r}
    ok("solo ok, error, bloqueado y nota", claves <= {"ok", "error", "bloqueado", "nota"}, sorted(claves))
    codigo = (BASE / "autocompletar_login.py").read_text(encoding="utf-8")
    ok("el módulo no lee el valor de ningún campo (ValuePattern, get_value, window_text de un Edit)",
       not any(x in codigo for x in ("ValuePattern", "get_value", "CurrentValue", "legacy_properties")))


def pruebas_integracion():
    catalogo = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))
    h = next((h for h in catalogo["herramientas"] if h["nombre"] == "autocompletar_login"), None)
    ok("en herramientas.json con permiso 'confirmar'", h and h["permiso"] == "confirmar")
    ok("su único parámetro es 'sitio'", h and list(h["parametros"]["properties"]) == ["sitio"])
    config = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    ok("apagada por defecto en config.json", config.get("autocompletar_login", {}).get("activa") is False)
    arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
    activas = next(ast.literal_eval(n.value) for n in arbol.body
                   if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "ACTIVAS")
    ok("no está en ACTIVAS fijas (el prompt no cambia mientras esté apagada)", "autocompletar_login" not in activas)
    p = md.Politica(app_en_punto=lambda x, y: None, app_al_frente=lambda: None, posicion_cursor=lambda: (0, 0),
                    planificar_mouse=lambda *a, **k: (None, "x"))
    d = p.decidir("autocompletar_login", {"sitio": "github"}, PEDIDO, [])
    ok("con el modo sin confirmación, sigue preguntando", not d[0], d[1])
    voz = (BASE / "voz.py").read_text(encoding="utf-8")
    solo_lectura = voz.split("SOLO_LECTURA = ", 1)[1].split("\n\n", 1)[0]
    ok("en voz no es de solo lectura (se confirma)", "autocompletar_login" not in solo_lectura)


def pruebas_ejecutor():
    """ejecutar() de agente_minimo.py (extraído con ast, sin modelo), con el modo sin confirmación encendido."""
    import probar_modo_directo as pmd
    ns = pmd.cargar_ejecutor()
    catalogo = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))
    ns["HERRAMIENTAS"] = {h["nombre"]: h for h in catalogo["herramientas"]}
    planes = {"error": None}
    ns["PLANIFICADORES"]["autocompletar_login"] = lambda args: (None, planes["error"]) if planes["error"]         else ({"hwnd": 10}, None)
    ns["_modos"]["sin_confirmacion"] = True
    ns["_tarea"].update(pedido=PEDIDO, herramientas=[], movidos=0)
    r = ns["ejecutar"]("autocompletar_login", {"sitio": "github"})
    ok("agente: con el modo activo pregunta igual, y sin un sí no se ejecuta",
       len(ns["preguntas"]) == 1 and not ns["llamadas"] and r.get("rechazado"), r)
    ns["preguntas"].clear()
    planes["error"] = {"ok": False, "bloqueado": True, "error": "x"}
    r = ns["ejecutar"]("autocompletar_login", {"sitio": "github"})
    ok("agente: si el plan falla, no pregunta por algo que se va a rechazar", not ns["preguntas"] and r["bloqueado"])
    fuente = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
    ok("agente: el sitio se comprueba con el pedido de la tarea, no con lo que diga el modelo",
       'autocompletar_login.obtener_tarea = lambda: (_tarea["pedido"]' in fuente)
    ok("agente: solo entra en ACTIVAS con config.json -> autocompletar_login.activa",
       'if CONFIG.get("autocompletar_login", {}).get("activa"):\n    ACTIVAS.add("autocompletar_login")' in fuente)


if __name__ == "__main__":
    pruebas_cuando()
    pruebas_campo()
    pruebas_ejecucion()
    pruebas_lo_que_ve_el_modelo()
    pruebas_integracion()
    pruebas_ejecutor()
    bien = sum(1 for _, c, _ in resultados if c)
    print(f"\n{bien}/{len(resultados)} pruebas correctas")
    sys.exit(0 if bien == len(resultados) else 1)
