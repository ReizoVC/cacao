"""
Fase 6: actividad de Reizo frente al PC (teclado, mouse y mandos), solo con ENTRADA FÍSICA.

Teclado y mouse se miden con Raw Input (RIDEV_INPUTSINK en una ventana oculta), no con GetLastInputInfo: en este PC
GetLastInputInfo se reiniciaba sin parar sin ninguna tecla ni movimiento (diagnostico_actividad.py, 2026-10-06), así
que nunca había 'inactivo'. Raw Input dice de qué dispositivo viene cada evento; la entrada inyectada (SendInput: la
herramienta teclado/mouse del agente, macros, control remoto por software) llega SIN dispositivo y no cuenta. Del
mouse cuentan los botones, la rueda y el movimiento de al menos MOVIMIENTO_MIN cuentas en un segundo (la deriva del
sensor no). Si Raw Input no se pudo registrar, se vuelve a GetLastInputInfo y se avisa en raw_teclado_ok.

Los mandos se vigilan aparte, en hilos, sin instalar nada:
  - XInput (xinput1_4.dll): mandos Xbox y compatibles, 4 puertos, consultados 4 veces por segundo;
  - Raw Input HID (gamepad y joystick): los demás (DualSense, Switch Pro...).
Cuenta como actividad un botón que cambia o un eje que se mueve más de ZONA_MUERTA de su recorrido; así un stick que
deriva o un mando que manda informes sin parar (el DualSense manda ~250 por segundo, con el giroscopio) no la falsea.
Lo usan registro_habitos.py (estado 'inactivo'), la vigilancia de la reflexión y el modo juego (deteccion.py).
"""
import ctypes
import threading
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

ZONA_MUERTA = 0.12      # fracción del recorrido de un eje
MOVIMIENTO_MIN = 12     # cuentas de mouse (|dx| + |dy|) en un segundo para que el movimiento sea actividad
XINPUT_STICK = 4000     # de 32767
XINPUT_GATILLO = 30     # de 255


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def segundos_sin_teclado_ni_mouse():
    info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000


# ---------- comparación de estados de un mando (pura, para poder probarla sin mando) ----------

def hay_cambio(anterior, actual):
    """anterior/actual: {'botones': set, 'ejes': {nombre: valor en 0..1}, 'hat': int|None}. True si cambió un
    botón o el hat, o si algún eje se movió más de ZONA_MUERTA."""
    if anterior is None:
        return False  # el primer informe de un mando recién conectado no es actividad
    if anterior["botones"] != actual["botones"] or anterior.get("hat") != actual.get("hat"):
        return True
    return any(abs(v - anterior["ejes"].get(k, v)) > ZONA_MUERTA for k, v in actual["ejes"].items())


# ---------- XInput ----------

class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [("wButtons", wintypes.WORD), ("bLeftTrigger", ctypes.c_ubyte), ("bRightTrigger", ctypes.c_ubyte),
                ("sThumbLX", ctypes.c_short), ("sThumbLY", ctypes.c_short),
                ("sThumbRX", ctypes.c_short), ("sThumbRY", ctypes.c_short)]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", XINPUT_GAMEPAD)]


def _estado_xinput(g):
    # ejes escalados para que XINPUT_GATILLO y XINPUT_STICK equivalgan a ZONA_MUERTA en hay_cambio
    gatillo, stick = ZONA_MUERTA / XINPUT_GATILLO, ZONA_MUERTA / XINPUT_STICK
    return {"botones": {b for b in range(16) if g.wButtons & (1 << b)}, "hat": None,
            "ejes": {"lt": g.bLeftTrigger * gatillo, "rt": g.bRightTrigger * gatillo,
                     "lx": g.sThumbLX * stick, "ly": g.sThumbLY * stick,
                     "rx": g.sThumbRX * stick, "ry": g.sThumbRY * stick}}


# ---------- Raw Input HID ----------

WM_INPUT = 0x00FF
RIM_TYPEMOUSE, RIM_TYPEKEYBOARD, RIM_TYPEHID = 0, 1, 2
RI_KEY_BREAK = 0x01
MOUSE_MOVE_ABSOLUTE = 0x01
PAGINA_RATON, PAGINA_TECLADO = 0x02, 0x06  # usos de la página de escritorio genérico (0x01)
RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIDI_PREPARSEDDATA = 0x20000005
HWND_MESSAGE = wintypes.HWND(-3)
HIDP_INPUT = 0
HIDP_STATUS_SUCCESS = 0x00110000
PAGINA_ESCRITORIO = 0x01
USOS_EJES = {0x30: "x", 0x31: "y", 0x32: "z", 0x33: "rx", 0x34: "ry", 0x35: "rz", 0x36: "slider"}
USO_HAT = 0x39


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT), ("dwFlags", wintypes.DWORD),
                ("hwndTarget", wintypes.HWND)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD), ("hDevice", wintypes.HANDLE),
                ("wParam", wintypes.WPARAM)]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [("Usage", wintypes.USHORT), ("UsagePage", wintypes.USHORT),
                ("InputReportByteLength", wintypes.USHORT), ("OutputReportByteLength", wintypes.USHORT),
                ("FeatureReportByteLength", wintypes.USHORT), ("Reserved", wintypes.USHORT * 17),
                ("NumberLinkCollectionNodes", wintypes.USHORT), ("NumberInputButtonCaps", wintypes.USHORT),
                ("NumberInputValueCaps", wintypes.USHORT), ("NumberInputDataIndices", wintypes.USHORT),
                ("NumberOutputButtonCaps", wintypes.USHORT), ("NumberOutputValueCaps", wintypes.USHORT),
                ("NumberOutputDataIndices", wintypes.USHORT), ("NumberFeatureButtonCaps", wintypes.USHORT),
                ("NumberFeatureValueCaps", wintypes.USHORT), ("NumberFeatureDataIndices", wintypes.USHORT)]


class _RANGO(ctypes.Structure):
    _fields_ = [("UsageMin", wintypes.USHORT), ("UsageMax", wintypes.USHORT),
                ("StringMin", wintypes.USHORT), ("StringMax", wintypes.USHORT),
                ("DesignatorMin", wintypes.USHORT), ("DesignatorMax", wintypes.USHORT),
                ("DataIndexMin", wintypes.USHORT), ("DataIndexMax", wintypes.USHORT)]


class HIDP_BUTTON_CAPS(ctypes.Structure):
    _fields_ = [("UsagePage", wintypes.USHORT), ("ReportID", ctypes.c_ubyte), ("IsAlias", ctypes.c_ubyte),
                ("BitField", wintypes.USHORT), ("LinkCollection", wintypes.USHORT), ("LinkUsage", wintypes.USHORT),
                ("LinkUsagePage", wintypes.USHORT), ("IsRange", ctypes.c_ubyte), ("IsStringRange", ctypes.c_ubyte),
                ("IsDesignatorRange", ctypes.c_ubyte), ("IsAbsolute", ctypes.c_ubyte),
                ("ReportCount", wintypes.USHORT), ("Reserved2", wintypes.USHORT), ("Reserved", wintypes.ULONG * 9),
                ("Range", _RANGO)]


class HIDP_VALUE_CAPS(ctypes.Structure):
    _fields_ = [("UsagePage", wintypes.USHORT), ("ReportID", ctypes.c_ubyte), ("IsAlias", ctypes.c_ubyte),
                ("BitField", wintypes.USHORT), ("LinkCollection", wintypes.USHORT), ("LinkUsage", wintypes.USHORT),
                ("LinkUsagePage", wintypes.USHORT), ("IsRange", ctypes.c_ubyte), ("IsStringRange", ctypes.c_ubyte),
                ("IsDesignatorRange", ctypes.c_ubyte), ("IsAbsolute", ctypes.c_ubyte), ("HasNull", ctypes.c_ubyte),
                ("Reserved", ctypes.c_ubyte), ("BitSize", wintypes.USHORT), ("ReportCount", wintypes.USHORT),
                ("Reserved2", wintypes.USHORT * 5), ("UnitsExp", wintypes.ULONG), ("Units", wintypes.ULONG),
                ("LogicalMin", wintypes.LONG), ("LogicalMax", wintypes.LONG), ("PhysicalMin", wintypes.LONG),
                ("PhysicalMax", wintypes.LONG), ("Range", _RANGO)]


WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR)]


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(wintypes.UINT),
                                   wintypes.UINT]
user32.GetRawInputDeviceInfoW.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_void_p,
                                          ctypes.POINTER(wintypes.UINT)]
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                   wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
user32.RegisterRawInputDevices.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.UINT]


class _DispositivoHID:
    """Lee botones y ejes de los informes de un mando HID con su 'preparsed data' (hid.dll)."""

    def __init__(self, preparsed):
        self.preparsed = preparsed
        self.hid = ctypes.windll.hid
        caps = HIDP_CAPS()
        self.hid.HidP_GetCaps(preparsed, ctypes.byref(caps))
        n = wintypes.USHORT(caps.NumberInputButtonCaps)
        botones = (HIDP_BUTTON_CAPS * max(1, n.value))()
        self.hid.HidP_GetButtonCaps(HIDP_INPUT, botones, ctypes.byref(n), preparsed)
        self.paginas_botones = sorted({b.UsagePage for b in botones[:n.value]})
        n = wintypes.USHORT(caps.NumberInputValueCaps)
        valores = (HIDP_VALUE_CAPS * max(1, n.value))()
        self.hid.HidP_GetValueCaps(HIDP_INPUT, valores, ctypes.byref(n), preparsed)
        self.ejes = []  # (uso, mínimo, máximo)
        for v in valores[:n.value]:
            usos = range(v.Range.UsageMin, v.Range.UsageMax + 1) if v.IsRange else [v.Range.UsageMin]
            for uso in usos:  # sin IsRange, Range.UsageMin es el campo NotRange.Usage
                if v.UsagePage == PAGINA_ESCRITORIO and (uso in USOS_EJES or uso == USO_HAT):
                    self.ejes.append((uso, v.LogicalMin, v.LogicalMax))

    def estado(self, informe):
        buf = (ctypes.c_char * len(informe)).from_buffer_copy(informe)
        pulsados = set()
        for pagina in self.paginas_botones:
            n = wintypes.ULONG(64)
            usos = (wintypes.USHORT * 64)()
            if self.hid.HidP_GetUsages(HIDP_INPUT, pagina, 0, usos, ctypes.byref(n), self.preparsed, buf,
                                       len(informe)) == HIDP_STATUS_SUCCESS:
                pulsados |= {(pagina, usos[i]) for i in range(n.value)}
        ejes, hat = {}, None
        for uso, minimo, maximo in self.ejes:
            valor = wintypes.ULONG()
            if self.hid.HidP_GetUsageValue(HIDP_INPUT, PAGINA_ESCRITORIO, 0, uso, ctypes.byref(valor),
                                           self.preparsed, buf, len(informe)) != HIDP_STATUS_SUCCESS:
                continue
            if uso == USO_HAT:
                hat = valor.value
            elif maximo > minimo:
                ejes[USOS_EJES[uso]] = (valor.value - minimo) / (maximo - minimo)
        return {"botones": pulsados, "ejes": ejes, "hat": hat}


class MonitorEntrada:
    """segundos_sin_entrada(): desde la última entrada FÍSICA de teclado, mouse o mando (ver arriba). Al arrancar
    cuenta desde ese momento."""

    def __init__(self, reloj=time.monotonic):
        self.reloj = reloj
        self.inicio = reloj()
        self.ultima_mando = None   # reloj() de la última actividad de un mando
        self.ultima_fisica = None  # reloj() de la última tecla o movimiento de mouse físicos
        self.inyectados = 0        # eventos de teclado/mouse sin dispositivo (no cuentan), para el diagnóstico
        self._mov = [0, 0]         # [segundo, cuentas de movimiento en ese segundo]
        self._abs = {}             # mouse absoluto (tabletas, escritorio remoto): última posición por dispositivo
        self.xinput_ok = False
        self.rawinput_ok = False
        self.raw_teclado_ok = False  # teclado y mouse por Raw Input; si es False se usa GetLastInputInfo
        self._parar = threading.Event()
        self._hilos = []
        self._anteriores = {}      # mando -> último estado
        self._dispositivos = {}    # hDevice -> _DispositivoHID | None
        self._id_hilo_raw = None

    def iniciar(self):
        for objetivo, nombre in ((self._bucle_xinput, "mando-xinput"), (self._bucle_rawinput, "mando-hid")):
            hilo = threading.Thread(target=objetivo, name=nombre, daemon=True)
            hilo.start()
            self._hilos.append(hilo)
        return self

    def cerrar(self):
        self._parar.set()
        if self._id_hilo_raw:
            user32.PostThreadMessageW(self._id_hilo_raw, 0x0012, 0, 0)  # WM_QUIT

    def segundos_sin_mando(self):
        return float("inf") if self.ultima_mando is None else self.reloj() - self.ultima_mando

    def segundos_sin_teclado_ni_mouse(self):
        if not self.raw_teclado_ok:
            return segundos_sin_teclado_ni_mouse()  # respaldo: Raw Input no se registró
        return self.reloj() - (self.ultima_fisica if self.ultima_fisica is not None else self.inicio)

    def segundos_sin_entrada(self):
        return min(self.segundos_sin_teclado_ni_mouse(), self.segundos_sin_mando())

    # ----- teclado y mouse (sin Win32, para poder probarlo) -----

    def procesar_teclado(self, hdevice, flags):
        """Una tecla de Raw Input. hdevice 0 = inyectada: no cuenta. Solo la pulsación (no la suelta)."""
        if not hdevice:
            self.inyectados += 1
            return False
        if flags & RI_KEY_BREAK:
            return False
        self.ultima_fisica = self.reloj()
        return True

    def procesar_raton(self, hdevice, usflags, botones, dx, dy):
        """Un evento de mouse de Raw Input. Cuentan botones y rueda (usButtonFlags != 0) y el movimiento que suma
        MOVIMIENTO_MIN cuentas en un segundo. hdevice 0 = inyectado: no cuenta."""
        if not hdevice:
            self.inyectados += 1
            return False
        ahora = self.reloj()
        if botones:
            self.ultima_fisica = ahora
            return True
        if usflags & MOUSE_MOVE_ABSOLUTE:
            previo, self._abs[hdevice] = self._abs.get(hdevice), (dx, dy)
            if previo is None:
                return False
            dx, dy = (dx - previo[0]) * 1920 // 65536, (dy - previo[1]) * 1080 // 65536  # a píxeles aproximados
        segundo = int(ahora)
        if self._mov[0] != segundo:
            self._mov = [segundo, 0]
        self._mov[1] += abs(dx) + abs(dy)
        if self._mov[1] >= MOVIMIENTO_MIN:
            self.ultima_fisica = ahora
            return True
        return False

    def _registrar(self, mando, estado):
        if hay_cambio(self._anteriores.get(mando), estado):
            self.ultima_mando = self.reloj()
        self._anteriores[mando] = estado

    def _bucle_xinput(self):
        try:
            xinput = ctypes.windll.xinput1_4
        except OSError:
            return
        self.xinput_ok = True
        estado = XINPUT_STATE()
        while not self._parar.wait(0.25):
            for i in range(4):
                if xinput.XInputGetState(i, ctypes.byref(estado)) == 0:
                    self._registrar(("xinput", i), _estado_xinput(estado.Gamepad))
                else:
                    self._anteriores.pop(("xinput", i), None)

    def _bucle_rawinput(self):
        self._id_hilo_raw = kernel32.GetCurrentThreadId()
        self._wndproc = WNDPROC(self._procesar)  # referencia viva: si no, el GC libera el callback
        clase = WNDCLASSW(lpfnWndProc=self._wndproc, lpszClassName="AsistenteMandosHID",
                          hInstance=kernel32.GetModuleHandleW(None))
        user32.RegisterClassW(ctypes.byref(clase))
        hwnd = user32.CreateWindowExW(0, "AsistenteMandosHID", None, 0, 0, 0, 0, 0, HWND_MESSAGE, None,
                                      clase.hInstance, None)
        if not hwnd:
            return
        dispositivos = (RAWINPUTDEVICE * 2)(RAWINPUTDEVICE(PAGINA_ESCRITORIO, 0x04, RIDEV_INPUTSINK, hwnd),
                                            RAWINPUTDEVICE(PAGINA_ESCRITORIO, 0x05, RIDEV_INPUTSINK, hwnd))
        self.rawinput_ok = bool(user32.RegisterRawInputDevices(dispositivos, 2, ctypes.sizeof(RAWINPUTDEVICE)))
        fisicos = (RAWINPUTDEVICE * 2)(RAWINPUTDEVICE(PAGINA_ESCRITORIO, PAGINA_TECLADO, RIDEV_INPUTSINK, hwnd),
                                       RAWINPUTDEVICE(PAGINA_ESCRITORIO, PAGINA_RATON, RIDEV_INPUTSINK, hwnd))
        self.raw_teclado_ok = bool(user32.RegisterRawInputDevices(fisicos, 2, ctypes.sizeof(RAWINPUTDEVICE)))
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.DestroyWindow(hwnd)

    def _procesar(self, hwnd, mensaje, wparam, lparam):
        if mensaje == WM_INPUT:
            try:
                self._leer_rawinput(lparam)
            except Exception:  # un mando raro no debe tumbar el hilo
                pass
        return user32.DefWindowProcW(hwnd, mensaje, wparam, lparam)

    def _leer_rawinput(self, lparam):
        tamano = wintypes.UINT(0)
        cabecera = ctypes.sizeof(RAWINPUTHEADER)
        user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(tamano), cabecera)
        buf = ctypes.create_string_buffer(tamano.value)
        if user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(tamano), cabecera) != tamano.value:
            return
        h = RAWINPUTHEADER.from_buffer_copy(buf)
        if h.dwType == RIM_TYPEKEYBOARD:
            _, flags = (wintypes.USHORT * 2).from_buffer_copy(buf, cabecera)  # RAWKEYBOARD: MakeCode, Flags
            self.procesar_teclado(h.hDevice, flags)
            return
        if h.dwType == RIM_TYPEMOUSE:
            # RAWMOUSE: usFlags (+2 de relleno), usButtonFlags, usButtonData, ulRawButtons, lLastX, lLastY
            usflags = wintypes.USHORT.from_buffer_copy(buf, cabecera).value
            botones = wintypes.USHORT.from_buffer_copy(buf, cabecera + 4).value
            dx, dy = (wintypes.LONG * 2).from_buffer_copy(buf, cabecera + 12)
            self.procesar_raton(h.hDevice, usflags, botones, dx, dy)
            return
        if h.dwType != RIM_TYPEHID:
            return
        dwsize, dwcount = (wintypes.DWORD * 2).from_buffer_copy(buf, cabecera)
        datos = buf.raw[cabecera + 8:cabecera + 8 + dwsize * dwcount]
        disp = self._dispositivo(h.hDevice)
        if disp is None:
            return
        for i in range(dwcount):
            self._registrar(("hid", h.hDevice), disp.estado(datos[i * dwsize:(i + 1) * dwsize]))

    def _dispositivo(self, hdevice):
        if hdevice not in self._dispositivos:
            tamano = wintypes.UINT(0)
            user32.GetRawInputDeviceInfoW(hdevice, RIDI_PREPARSEDDATA, None, ctypes.byref(tamano))
            preparsed = ctypes.create_string_buffer(tamano.value) if tamano.value else None
            if preparsed and user32.GetRawInputDeviceInfoW(hdevice, RIDI_PREPARSEDDATA, preparsed,
                                                           ctypes.byref(tamano)) > 0:
                self._dispositivos[hdevice] = _DispositivoHID(preparsed)
            else:
                self._dispositivos[hdevice] = None
        return self._dispositivos[hdevice]
