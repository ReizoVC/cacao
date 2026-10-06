"""
Diagnóstico de actividad: qué fuente hace que el PC parezca en uso. Solo lee; no guarda teclas, posiciones ni
contenido de los informes, solo cuántos eventos llegan y de qué dispositivo.

Fuentes, cada segundo durante N segundos:
  - GetLastInputInfo: si se reinicia (lo que usa el registro de hábitos para teclado y mouse);
  - Raw Input de teclado y mouse (RIDEV_INPUTSINK): eventos por dispositivo físico; hDevice nulo = entrada inyectada
    (SendInput) o sintética;
  - Raw Input HID: TODOS los dispositivos HID conectados (cada página/uso de nivel superior), con su nombre, usage
    page y usage: así se ve si los audífonos, un lápiz o un RGB mandan informes;
  - XInput: puertos conectados y si cambia el número de paquete;
  - MonitorEntrada (entrada.py), el que usan el registro de hábitos y la reflexión: si su mando cuenta actividad.

Uso: .venv\\Scripts\\python diagnostico_actividad.py [segundos=120] [archivo.json]
"""
import ctypes
import json
import sys
import threading
import time
from collections import Counter, defaultdict
from ctypes import wintypes

import entrada

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
hid = ctypes.windll.hid

RIM_TYPEMOUSE, RIM_TYPEKEYBOARD, RIM_TYPEHID = 0, 1, 2
RIDI_DEVICENAME, RIDI_DEVICEINFO = 0x20000007, 0x2000000B
RIDEV_INPUTSINK = 0x00000100
TIPOS = {RIM_TYPEMOUSE: "mouse", RIM_TYPEKEYBOARD: "teclado", RIM_TYPEHID: "hid"}


class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [("hDevice", wintypes.HANDLE), ("dwType", wintypes.DWORD)]


class RID_DEVICE_INFO_HID(ctypes.Structure):
    _fields_ = [("dwVendorId", wintypes.DWORD), ("dwProductId", wintypes.DWORD), ("dwVersionNumber", wintypes.DWORD),
                ("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT)]


class RID_DEVICE_INFO(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("hid", RID_DEVICE_INFO_HID), ("_relleno", ctypes.c_byte * 24)]
    _anonymous_ = ("u",)
    _fields_ = [("cbSize", wintypes.DWORD), ("dwType", wintypes.DWORD), ("u", _U)]


user32.GetRawInputDeviceList.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                 wintypes.DWORD, wintypes.HANDLE]


def nombre_ruta(hdevice):
    n = wintypes.UINT(0)
    user32.GetRawInputDeviceInfoW(hdevice, RIDI_DEVICENAME, None, ctypes.byref(n))
    buf = ctypes.create_unicode_buffer(n.value + 1)
    user32.GetRawInputDeviceInfoW(hdevice, RIDI_DEVICENAME, buf, ctypes.byref(n))
    return buf.value


def nombre_producto(ruta):
    """Nombre del producto (HidD_GetProductString), abriendo el dispositivo sin permisos de lectura ni escritura."""
    h = kernel32.CreateFileW(ruta, 0, 3, None, 3, 0, None)  # acceso 0, compartir lectura/escritura, OPEN_EXISTING
    if not h or h == wintypes.HANDLE(-1).value:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(128)
        return buf.value if hid.HidD_GetProductString(h, buf, ctypes.sizeof(buf)) else ""
    finally:
        kernel32.CloseHandle(h)


def dispositivos():
    """{hDevice: {tipo, ruta, nombre, pagina, uso, vid, pid}} de todos los dispositivos Raw Input conectados."""
    n = wintypes.UINT(0)
    user32.GetRawInputDeviceList(None, ctypes.byref(n), ctypes.sizeof(RAWINPUTDEVICELIST))
    lista = (RAWINPUTDEVICELIST * n.value)()
    user32.GetRawInputDeviceList(lista, ctypes.byref(n), ctypes.sizeof(RAWINPUTDEVICELIST))
    resultado = {}
    for d in lista[:n.value]:
        info = {"tipo": TIPOS.get(d.dwType, str(d.dwType)), "ruta": nombre_ruta(d.hDevice)}
        if d.dwType == RIM_TYPEHID:
            ri = RID_DEVICE_INFO(cbSize=ctypes.sizeof(RID_DEVICE_INFO))
            tam = wintypes.UINT(ctypes.sizeof(ri))
            user32.GetRawInputDeviceInfoW(d.hDevice, RIDI_DEVICEINFO, ctypes.byref(ri), ctypes.byref(tam))
            info.update(pagina=ri.hid.usUsagePage, uso=ri.hid.usUsage, vid=ri.hid.dwVendorId, pid=ri.hid.dwProductId)
        info["nombre"] = nombre_producto(info["ruta"]) if d.dwType == RIM_TYPEHID else ""
        resultado[d.hDevice or 0] = info
    return resultado


class Escucha:
    """Raw Input de teclado, mouse y todos los HID en una ventana oculta; cuenta eventos por segundo y dispositivo."""

    def __init__(self, colecciones):
        self.colecciones = colecciones  # [(pagina, uso)] HID a registrar
        self.eventos = defaultdict(Counter)  # segundo -> Counter((tipo, hDevice))
        self.inicio = time.monotonic()
        self.registrado = False
        self._id_hilo = None

    def iniciar(self):
        listo = threading.Event()
        threading.Thread(target=self._bucle, args=(listo,), daemon=True).start()
        listo.wait(3)
        return self

    def cerrar(self):
        if self._id_hilo:
            user32.PostThreadMessageW(self._id_hilo, 0x0012, 0, 0)

    def _bucle(self, listo):
        self._id_hilo = kernel32.GetCurrentThreadId()
        self._proc = entrada.WNDPROC(self._procesar)
        clase = entrada.WNDCLASSW(lpfnWndProc=self._proc, lpszClassName="DiagnosticoActividad",
                                  hInstance=kernel32.GetModuleHandleW(None))
        user32.RegisterClassW(ctypes.byref(clase))
        hwnd = user32.CreateWindowExW(0, "DiagnosticoActividad", None, 0, 0, 0, 0, 0, entrada.HWND_MESSAGE, None,
                                      clase.hInstance, None)
        pares = [(0x01, 0x02), (0x01, 0x06)] + [c for c in self.colecciones if c not in ((0x01, 0x02), (0x01, 0x06))]
        regs = (entrada.RAWINPUTDEVICE * len(pares))(*[entrada.RAWINPUTDEVICE(p, u, RIDEV_INPUTSINK, hwnd)
                                                       for p, u in pares])
        self.registrado = bool(user32.RegisterRawInputDevices(regs, len(pares),
                                                              ctypes.sizeof(entrada.RAWINPUTDEVICE)))
        listo.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.DestroyWindow(hwnd)

    def _procesar(self, hwnd, mensaje, wparam, lparam):
        if mensaje == entrada.WM_INPUT:
            try:
                tam = wintypes.UINT(0)
                cab = ctypes.sizeof(entrada.RAWINPUTHEADER)
                user32.GetRawInputData(lparam, entrada.RID_INPUT, None, ctypes.byref(tam), cab)
                buf = ctypes.create_string_buffer(tam.value)
                if user32.GetRawInputData(lparam, entrada.RID_INPUT, buf, ctypes.byref(tam), cab) == tam.value:
                    h = entrada.RAWINPUTHEADER.from_buffer_copy(buf)
                    segundo = int(time.monotonic() - self.inicio)
                    self.eventos[segundo][(TIPOS.get(h.dwType, "?"), h.hDevice or 0)] += 1
            except Exception:
                pass
        return user32.DefWindowProcW(hwnd, mensaje, wparam, lparam)


def xinput_paquetes():
    try:
        x = ctypes.windll.xinput1_4
    except OSError:
        return {}
    estado = entrada.XINPUT_STATE()
    return {i: estado.dwPacketNumber for i in range(4) if x.XInputGetState(i, ctypes.byref(estado)) == 0}


def main(segundos=120, salida=None):
    disp = dispositivos()
    colecciones = sorted({(d["pagina"], d["uso"]) for d in disp.values() if d["tipo"] == "hid"})
    print(f"Dispositivos Raw Input: {len(disp)} ({sum(d['tipo'] == 'hid' for d in disp.values())} HID). "
          f"Colecciones HID: {', '.join(f'{p:#06x}/{u:#06x}' for p, u in colecciones)}", flush=True)
    escucha = Escucha(colecciones).iniciar()
    monitor = entrada.MonitorEntrada().iniciar()
    time.sleep(1)
    print(f"Raw Input registrado: {escucha.registrado}; MonitorEntrada: xinput={monitor.xinput_ok} "
          f"rawinput={monitor.rawinput_ok}", flush=True)
    filas, xi_antes = [], xinput_paquetes()
    xi_cambios = Counter()
    inicio = time.monotonic()
    escucha.inicio = inicio
    lii_reinicios = 0
    for s in range(segundos):
        time.sleep(max(0, inicio + s + 1 - time.monotonic()))
        lii = entrada.segundos_sin_teclado_ni_mouse()
        xi = xinput_paquetes()
        for i, p in xi.items():
            if i in xi_antes and xi_antes[i] != p:
                xi_cambios[i] += 1
        xi_antes = xi
        sin_mando = monitor.segundos_sin_mando()
        lii_reinicios += lii < 1.0
        filas.append({"s": s + 1, "sin_teclado_mouse_s": round(lii, 1),
                      "sin_mando_s": None if sin_mando == float("inf") else round(sin_mando, 1)})
        if (s + 1) % 10 == 0:
            bloque = Counter()
            for t in range(s - 9, s + 1):
                bloque.update(escucha.eventos.get(t, {}))
            resumen = ", ".join(f"{tipo}:{disp.get(h, {}).get('nombre') or ('inyectado' if not h else hex(h))}={n}"
                                for (tipo, h), n in bloque.most_common(4)) or "sin eventos"
            print(f"[{s + 1:3d} s] GetLastInputInfo {lii:6.1f} s | mando {filas[-1]['sin_mando_s']} | {resumen}",
                  flush=True)
    escucha.cerrar()
    monitor.cerrar()
    total = Counter()
    for c in escucha.eventos.values():
        total.update(c)
    print("\nEventos por fuente y dispositivo en todo el diagnóstico:")
    detalle = []
    for (tipo, h), n in total.most_common():
        d = disp.get(h, {})
        etiqueta = ("ENTRADA INYECTADA (SendInput, sin dispositivo)" if not h else
                    f"{d.get('nombre') or '(sin nombre)'}" + (f" usage page {d['pagina']:#06x} usage {d['uso']:#06x}"
                                                              if tipo == "hid" else ""))
        ruta = d.get("ruta", "")
        print(f"  {tipo:8s} {n:7d}  {etiqueta}  {ruta[:70]}")
        detalle.append({"tipo": tipo, "eventos": n, "nombre": d.get("nombre", ""), "pagina": d.get("pagina"),
                        "uso": d.get("uso"), "ruta": ruta, "inyectado": not h})
    print(f"\nGetLastInputInfo se reinició en {lii_reinicios}/{segundos} s; XInput: puertos {sorted(xi_antes)}, "
          f"cambios de paquete {dict(xi_cambios)}; MonitorEntrada: último mando hace "
          f"{filas[-1]['sin_mando_s']} s")
    hid_conectados = [{"nombre": d["nombre"], "pagina": d["pagina"], "uso": d["uso"], "vid": d["vid"], "pid": d["pid"]}
                      for d in disp.values() if d["tipo"] == "hid"]
    if salida:
        with open(salida, "w", encoding="utf-8") as f:
            json.dump({"segundos": segundos, "inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "getlastinputinfo_reinicios": lii_reinicios, "xinput_puertos": sorted(xi_antes),
                       "xinput_cambios": dict(xi_cambios), "eventos": detalle, "hid_conectados": hid_conectados,
                       "por_segundo": filas}, f, ensure_ascii=False, indent=1)
        print(f"Guardado en {salida}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 120, sys.argv[2] if len(sys.argv) > 2 else None)
