"""
Fase 7: las confirmaciones solo aceptan entrada FÍSICA (diseno_fase7.md §6).

Mientras hay una confirmación pendiente se instalan dos hooks de bajo nivel (WH_KEYBOARD_LL y WH_MOUSE_LL) en un hilo
con su propio bucle de mensajes:
  - teclado: Enter = sí, Esc = no, solo si la tecla NO trae LLKHF_INJECTED (ni LLKHF_LOWER_IL_INJECTED). Mientras
    se espera, Enter y Esc no llegan a ninguna app (los dos, físicos o inyectados), como hacía RegisterHotKey;
  - mouse: se anota cada clic izquierdo dentro de la isla, con LLMHF_INJECTED (o LLMHF_LOWER_IL_INJECTED) o sin él.
    Un "Permitir" o "Denegar" de la isla solo vale si el último clic dentro de la isla fue físico y reciente. El clic
    no se consume: la isla lo recibe normalmente.
Así el agente nunca puede aprobar su propia acción con sus herramientas mouse o teclado (que usan SendInput y
llegan marcadas como inyectadas). Los hooks se quitan en cuanto se responde.

procesar_tecla / procesar_clic tienen la lógica sin Win32: las pruebas les pasan eventos simulados.
"""
import ctypes
import threading
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL, WH_MOUSE_LL = 13, 14
WM_KEYDOWN, WM_SYSKEYDOWN = 0x0100, 0x0104
WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0201, 0x0202
WM_QUIT = 0x0012
VK_RETURN, VK_ESCAPE = 0x0D, 0x1B
LLKHF_INJECTED, LLKHF_LOWER_IL_INJECTED = 0x10, 0x02
LLMHF_INJECTED, LLMHF_LOWER_IL_INJECTED = 0x01, 0x02
CLIC_VALIDO_S = 2.0  # entre el clic físico en la isla y la decisión que manda la isla


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE


class EntradaFisica:
    """zona_isla(): rectángulos (izq, arriba, der, abajo) de la isla en píxeles de pantalla, o []."""

    def __init__(self, zona_isla=lambda: [], al_teclear=lambda si: None, reloj=time.monotonic):
        self.zona_isla, self.al_teclear, self.reloj = zona_isla, al_teclear, reloj
        self.ultimo_clic_isla = None   # (instante, físico)
        self.teclas_inyectadas = 0     # para el registro: cuántas se ignoraron
        self.clics_inyectados = 0
        self._hooks = []
        self._hilo = None
        self._id_hilo = None
        self._listo = threading.Event()

    # ----- lógica (sin Win32) -----

    def procesar_tecla(self, vk, mensaje, flags):
        """True si la tecla se consume (Enter o Esc mientras se espera)."""
        if vk not in (VK_RETURN, VK_ESCAPE):
            return False
        if mensaje in (WM_KEYDOWN, WM_SYSKEYDOWN):
            if flags & (LLKHF_INJECTED | LLKHF_LOWER_IL_INJECTED):
                self.teclas_inyectadas += 1
            else:
                self.al_teclear(vk == VK_RETURN)
        return True

    def procesar_clic(self, mensaje, x, y, flags):
        if mensaje not in (WM_LBUTTONDOWN, WM_LBUTTONUP):
            return
        if not any(izq <= x < der and arriba <= y < abajo for izq, arriba, der, abajo in self.zona_isla()):
            return
        fisico = not flags & (LLMHF_INJECTED | LLMHF_LOWER_IL_INJECTED)
        if not fisico:
            self.clics_inyectados += 1
        # el par bajar/subir cuenta como uno: si cualquiera de los dos es inyectado, el clic no es físico
        if mensaje == WM_LBUTTONDOWN or self.ultimo_clic_isla is None or not fisico:
            self.ultimo_clic_isla = (self.reloj(), fisico)

    def clic_fisico_reciente(self, desde):
        """True si el último clic dentro de la isla fue físico, posterior a 'desde' y de hace ≤ CLIC_VALIDO_S."""
        if self.ultimo_clic_isla is None:
            return False
        instante, fisico = self.ultimo_clic_isla
        return fisico and instante >= desde and self.reloj() - instante <= CLIC_VALIDO_S

    # ----- Win32 -----

    def iniciar(self):
        self._hilo = threading.Thread(target=self._bucle, name="entrada-fisica", daemon=True)
        self._hilo.start()
        self._listo.wait(2)
        return len(self._hooks) == 2

    def cerrar(self):
        if self._id_hilo:
            user32.PostThreadMessageW(self._id_hilo, WM_QUIT, 0, 0)
            self._hilo.join(2)

    def _bucle(self):
        self._id_hilo = kernel32.GetCurrentThreadId()

        def teclado(codigo, wparam, lparam):
            if codigo == 0:
                k = KBDLLHOOKSTRUCT.from_address(lparam)
                try:
                    if self.procesar_tecla(k.vkCode, wparam, k.flags):
                        return 1  # Enter/Esc no llegan a ninguna app mientras se espera la confirmación
                except Exception:
                    pass
            return user32.CallNextHookEx(None, codigo, wparam, lparam)

        def raton(codigo, wparam, lparam):
            if codigo == 0:
                m = MSLLHOOKSTRUCT.from_address(lparam)
                try:
                    self.procesar_clic(wparam, m.pt.x, m.pt.y, m.flags)
                except Exception:
                    pass
            return user32.CallNextHookEx(None, codigo, wparam, lparam)

        self._procs = (HOOKPROC(teclado), HOOKPROC(raton))  # referencias vivas mientras dure el hook
        modulo = kernel32.GetModuleHandleW(None)
        for tipo, proc in ((WH_KEYBOARD_LL, self._procs[0]), (WH_MOUSE_LL, self._procs[1])):
            h = user32.SetWindowsHookExW(tipo, proc, modulo, 0)
            if h:
                self._hooks.append(h)
        self._listo.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        for h in self._hooks:
            user32.UnhookWindowsHookEx(h)
        self._hooks = []
