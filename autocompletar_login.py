"""
autocompletar_login: activa el autocompletado del gestor de contraseñas de Chrome en la ventana al frente.

Qué hace: en la ventana de Chrome que está al frente, y solo si su título es del sitio que Reizo nombró en el
pedido, hace clic en el campo de usuario (UI Automation) y elige la primera cuenta guardada con el teclado (flecha
abajo + Enter). Chrome rellena usuario y contraseña; con "Usar Windows Hello al completar contraseñas" activado,
Windows pide antes la huella, la cara o el PIN: esa es la autorización real, y no se puede aprobar con teclas
inyectadas. No envía el formulario.

Lo que nunca hace:
  - leer el valor de un campo (ni el usuario ni la contraseña): solo usa la posición, la etiqueta y si es de
    contraseña (IsPassword de UI Automation);
  - devolver al modelo el título, la URL, los campos o las cuentas: solo { ok } o { ok: false, error };
  - actuar si el sitio no sale del pedido de Reizo, si la ventana al frente no es Chrome o no es de ese sitio, si en
    la tarea entró contenido externo (leer_archivo, buscar_web, ejecutar_powershell) o si la ventana cambió desde
    que se decidió.
Siempre pide confirmación (permiso "confirmar"), también con el modo sin confirmación.

planificar() valida y calcula sin efectos; ejecutar() actúa. Las pruebas (probar_autocompletar_login.py) pasan un
sistema falso; SistemaWindows es el real (Win32 + UI Automation). Estado: probado en simulación; en real, pendiente
de que Reizo active Windows Hello en Chrome (config.json -> autocompletar_login.activa).
"""
import time

from modo_directo import EXTERNO, nombrada_en, normalizar

CHROME = "chrome.exe"
# etiquetas habituales del campo de usuario cuando la página no tiene un campo de contraseña visible (login en dos
# pasos, como el de Google)
ETIQUETAS_USUARIO = ("usuario", "user", "username", "email", "e mail", "correo", "login", "cuenta", "account",
                     "identificador", "telefono", "phone", "nombre de usuario", "dni", "documento")
ESPERA_MENU_S = 1.5   # lo que se espera a que Chrome muestre su lista de cuentas
PASO_S = 0.1

# el agente las reemplaza: la tarea en curso (pedido y herramientas usadas) y el atajo de emergencia
obtener_tarea = lambda: ("", [])  # noqa: E731
comprobar_emergencia = lambda: None  # noqa: E731


def _bloqueado(motivo):
    return None, {"ok": False, "bloqueado": True, "error": motivo}


def _error(motivo):
    return None, {"ok": False, "error": motivo}


def nombre_del_sitio(sitio):
    """'github.com' o 'www.github.com' -> 'github': los títulos de Chrome suelen traer el nombre, no el dominio."""
    partes = [p for p in sitio.strip().lower().split(".") if p and p != "www"]
    return partes[0] if len(partes) > 1 else sitio


def _orden_lectura(campo):
    izq, arr, _, _ = campo["rect"]
    return arr, izq


def _centro(rect):
    izq, arr, der, aba = rect
    return (izq + der) // 2, (arr + aba) // 2


def elegir_campo_usuario(campos):
    """El campo de usuario entre los campos de texto de la página, o None. Con un campo de contraseña: el último
    campo que no es de contraseña antes del primero de contraseña (en orden de lectura; así un buscador de la
    cabecera no cuenta). Sin él (login en dos pasos): el único campo, o el único con etiqueta de usuario."""
    visibles = sorted((c for c in campos if c["habilitado"] and c["rect"][2] > c["rect"][0]
                       and c["rect"][3] > c["rect"][1]), key=_orden_lectura)
    claves = [c for c in visibles if c["es_contrasena"]]
    texto = [c for c in visibles if not c["es_contrasena"]]
    if claves:
        antes = [c for c in texto if _orden_lectura(c) < _orden_lectura(claves[0])]
        return antes[-1] if antes else None
    if len(texto) == 1:
        return texto[0]
    etiquetados = [c for c in texto
                   if any(f" {e} " in f" {normalizar(c['nombre'])} " for e in ETIQUETAS_USUARIO)]
    return etiquetados[0] if len(etiquetados) == 1 else None


def planificar(sitio, pedido, usadas, sistema):
    """({hwnd, pid, punto}, None) o (None, error). Sin efectos."""
    s = normalizar(sitio)
    if len(s) < 3:
        return _error("Indica en 'sitio' el sitio que nombró Reizo (por ejemplo 'github').")
    if not nombrada_en([sitio], pedido):
        return _bloqueado("Solo autocompleto el inicio de sesión en un sitio que Reizo nombró en su pedido.")
    externo = sorted(set(usadas) & EXTERNO)
    if externo:
        return _bloqueado(f"En esta tarea entró contenido externo ({', '.join(externo)}): no autocompleto "
                          "contraseñas. Que Reizo lo pida en una tarea nueva.")
    hwnd = sistema.ventana_al_frente()
    if not hwnd or sistema.proceso_de(hwnd) != CHROME:
        return _error(f"La ventana al frente no es Chrome. Busca la de {sitio} con listar_ventanas, tráela con "
                      "enfocar_ventana y vuelve a intentarlo.")
    if not nombrada_en([sitio, nombre_del_sitio(sitio)], sistema.titulo(hwnd)):
        return _error(f"La ventana de Chrome al frente no es de {sitio}. Busca la correcta con listar_ventanas y "
                      "enfocar_ventana.")
    campo = elegir_campo_usuario(sistema.campos(hwnd))
    if campo is None:
        return _error("No encontré un único campo de usuario en esa página. Que Reizo haga clic en él y lo elija.")
    punto = _centro(campo["rect"])
    if sistema.ventana_en(*punto) != hwnd:
        return _error("El campo de usuario está tapado por otra ventana.")
    if sistema.en_la_isla(punto):
        return _bloqueado("Esa posición es la isla de Cacao: no hago clic ahí.")
    return {"hwnd": hwnd, "pid": sistema.pid_de(hwnd), "punto": punto}, None


def _esperar_menu(sistema, hwnd, antes):
    limite = time.monotonic() + ESPERA_MENU_S
    while True:
        if sistema.emergentes(hwnd) - antes:
            return True
        if time.monotonic() >= limite:
            return False
        sistema.esperar(PASO_S)


def ejecutar(plan, sistema):
    """Clic en el campo de usuario, flecha abajo y Enter sobre la lista de Chrome. Devuelve { ok } o un error."""
    hwnd = plan["hwnd"]

    def sigue_igual():
        return sistema.ventana_al_frente() == hwnd and sistema.pid_de(hwnd) == plan["pid"]

    comprobar_emergencia()
    if not sigue_igual():
        return {"ok": False, "error": "La ventana cambió desde que lo decidí: no hago nada."}
    antes = sistema.emergentes(hwnd)
    sistema.clic(*plan["punto"])
    abierto = _esperar_menu(sistema, hwnd, antes)
    if not abierto:  # con el campo ya enfocado, Chrome abre la lista con la flecha abajo
        comprobar_emergencia()
        if not sigue_igual():
            return {"ok": False, "error": "La ventana cambió: no sigo."}
        sistema.tecla("abajo")
        abierto = _esperar_menu(sistema, hwnd, antes)
        if not abierto:
            return {"ok": False, "error": "Chrome no ofreció ninguna cuenta guardada para este sitio (o su "
                                          "autocompletado está desactivado)."}
    comprobar_emergencia()
    if not sigue_igual():
        sistema.tecla("esc")
        return {"ok": False, "error": "La ventana cambió con la lista abierta: la cerré sin elegir nada."}
    sistema.tecla("abajo")  # primera cuenta de la lista
    sistema.tecla("enter")
    sistema.esperar(0.5)
    if sistema.emergentes(hwnd) - antes:
        return {"ok": False, "error": "La lista de cuentas de Chrome sigue abierta: no sé si eligió una."}
    return {"ok": True, "nota": "Elegí la primera cuenta guardada. Si Chrome pide Windows Hello, Reizo tiene que "
                                "confirmarlo. No envié el formulario."}


# ---------- sistema real (Win32 + UI Automation) ----------

class SistemaWindows:
    def ventana_al_frente(self):
        import win32gui
        return win32gui.GetForegroundWindow()

    def pid_de(self, hwnd):
        import win32process
        return win32process.GetWindowThreadProcessId(hwnd)[1]

    def proceso_de(self, hwnd):
        import psutil
        try:
            return psutil.Process(self.pid_de(hwnd)).name().lower()
        except psutil.Error:
            return ""

    def titulo(self, hwnd):  # solo se compara aquí con el sitio; nunca sale de este módulo
        import win32gui
        return win32gui.GetWindowText(hwnd)

    def campos(self, hwnd):
        """Campos de texto de la página: posición, etiqueta y si son de contraseña. Nunca su valor."""
        from pywinauto import Desktop
        campos = []
        for e in Desktop(backend="uia").window(handle=hwnd).descendants(control_type="Edit"):
            info = e.element_info
            r = info.rectangle
            try:
                es_contrasena = bool(info.element.CurrentIsPassword)
            except Exception:
                es_contrasena = False
            campos.append({"rect": (r.left, r.top, r.right, r.bottom), "es_contrasena": es_contrasena,
                           "nombre": info.name or "", "habilitado": bool(info.enabled)})
        return campos

    def ventana_en(self, x, y):
        import win32gui
        return win32gui.GetAncestor(win32gui.WindowFromPoint((x, y)), 2)  # GA_ROOT

    def en_la_isla(self, punto):
        import herramientas_grupo4 as g4
        return g4._en_la_isla(punto)

    def emergentes(self, hwnd):
        """Ventanas visibles del mismo proceso que no son la principal: la lista de cuentas de Chrome es una."""
        import win32gui
        pid = self.pid_de(hwnd)
        encontradas = set()

        def agregar(h, _):
            if h != hwnd and win32gui.IsWindowVisible(h) and self.pid_de(h) == pid:
                encontradas.add(h)
            return True

        win32gui.EnumWindows(agregar, None)
        return encontradas

    def clic(self, x, y):
        import win32api
        import win32con
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def tecla(self, nombre):
        import herramientas_grupo4 as g4
        vk = g4.TECLAS[nombre]
        g4._enviar(vk=vk)
        g4._enviar(vk=vk, flags=g4.KEYEVENTF_KEYUP)

    def esperar(self, segundos):
        time.sleep(segundos)


_sistema = None


def _sistema_real():
    global _sistema
    if _sistema is None:
        _sistema = SistemaWindows()
    return _sistema


def planificar_desde_agente(sitio):
    pedido, usadas = obtener_tarea()
    return planificar(sitio or "", pedido, usadas, _sistema_real())


def autocompletar_login(sitio: str):
    plan, error = planificar_desde_agente(sitio)
    if error:
        return error
    return ejecutar(plan, _sistema_real())
