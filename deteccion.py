"""
Fase 6: cuándo puede arrancar la reflexión (o el lint) y cuándo debe detenerse (diseno_fase6.md §4.2).

Arranca solo si: ≥ inactividad_min sin teclado, mouse ni mando; sin pantalla completa (también ventana sin bordes);
sin ningún juego en marcha (los lanzadores no cuentan); sin audio que bloquee; y con la GPU por debajo de
gpu_max_pct durante gpu_ventana_s.
Audio según la categoría de la app que suena: 'música' no bloquea; el navegador solo si está a pantalla completa;
cualquier otra ('video', llamadas de 'comunicación', desconocidas) sí. El audio del propio agente (Piper) no cuenta.

Durante la reflexión, Guardia comprueba cada vigilancia_ms (los procesos, cada 2 s) y avisa del primer motivo para
parar: cualquier entrada nueva, pantalla completa, un juego que se abre o audio que empieza.
SistemaWindows hace las consultas reales (todas de solo lectura); las pruebas usan un sistema falso.
"""
import ctypes
import os
import subprocess
import threading
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
QUNS_PANTALLA_COMPLETA = {2, 3, 4}  # ocupado, D3D a pantalla completa, modo presentación
WS_CAPTION = 0x00C00000
CLASES_ESCRITORIO = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)]


class SistemaWindows:
    def __init__(self, monitor_entrada):
        self.entrada = monitor_entrada
        self.pid_propio = os.getpid()

    def segundos_sin_entrada(self):
        return self.entrada.segundos_sin_entrada()

    def pantalla_completa(self):
        estado = ctypes.c_int(0)
        if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(estado)) == 0 \
                and estado.value in QUNS_PANTALLA_COMPLETA:
            return True
        # ventana sin bordes que cubre todo su monitor (juegos y videos "en ventana sin bordes"); una ventana
        # maximizada no cuenta aunque la barra de tareas esté oculta
        hwnd = user32.GetForegroundWindow()
        if not hwnd or user32.IsZoomed(hwnd):
            return False
        clase = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, clase, 64)
        if clase.value in CLASES_ESCRITORIO or user32.GetWindowLongW(hwnd, -16) & WS_CAPTION:
            return False
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        info = MONITORINFO(ctypes.sizeof(MONITORINFO))
        user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info))
        m = info.rcMonitor
        return r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom

    def ejecutables(self):
        import psutil
        rutas = []
        for p in psutil.process_iter(["exe", "name"]):
            rutas.append(p.info["exe"] or p.info["name"] or "")
        return rutas

    def audio(self):
        """[(exe_ruta, aumid, pico)] de las sesiones de audio activas de otros procesos."""
        import comtypes
        from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
        import habitos
        comtypes.CoInitialize()  # cada hilo que usa COM
        sesiones = []
        try:
            for s in AudioUtilities.GetAllSessions():
                pid = s.ProcessId
                if not pid or pid == self.pid_propio or s.State != 1:  # 1 = AudioSessionStateActive
                    continue
                try:
                    pico = s._ctl.QueryInterface(IAudioMeterInformation).GetPeakValue()
                    exe = s.Process.exe() if s.Process else None
                except Exception:
                    continue
                sesiones.append((exe, habitos.aumid_de_pid(pid), pico))
        finally:
            comtypes.CoUninitialize()
        return sesiones

    def uso_gpu(self):
        try:
            salida = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                                    capture_output=True, text=True, timeout=5,
                                    creationflags=subprocess.CREATE_NO_WINDOW).stdout
            return int(salida.split()[0])
        except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
            return None


class Vigilante:
    def __init__(self, sistema, clasificador, config, reloj=time.monotonic, dormir=time.sleep):
        self.sistema, self.clasificador = sistema, clasificador
        self.c = config["reflexion"]
        self.reloj, self.dormir = reloj, dormir
        self._sonando = {}  # app -> (primera vez, última vez) que se oyó por encima del umbral

    # ----- comprobaciones sueltas -----

    def juego_abierto(self):
        return next((r for r in self.sistema.ejecutables() if self.clasificador.es_juego(r)), None)

    def audio_que_bloquea(self):
        """Nombre de la app cuyo audio bloquea (sonando ≥ audio_min_s), o None. Hay que llamarla seguido
        (cada ≤ 1 s) para medir la duración."""
        ahora = self.reloj()
        pantalla_completa = None
        for exe, aumid, pico in self.sistema.audio():
            if pico <= self.c["audio_umbral"]:
                continue
            info = self.clasificador.info(exe, aumid)
            if info["categoria"] == "música":
                continue
            if info["categoria"] == "navegador":
                if pantalla_completa is None:
                    pantalla_completa = self.sistema.pantalla_completa()
                if not pantalla_completa:
                    continue
            primera, ultima = self._sonando.get(info["app"], (ahora, ahora))
            if ahora - ultima > 1.5:  # hubo un silencio largo: empieza de nuevo
                primera = ahora
            self._sonando[info["app"]] = (primera, ahora)
        self._sonando = {a: t for a, t in self._sonando.items() if ahora - t[1] <= 1.5}
        return next((a for a, (p, u) in self._sonando.items() if u - p >= self.c["audio_min_s"]), None)

    # ----- antes de empezar -----

    def motivo_para_no_empezar(self, inactividad_min=None):
        """None si puede empezar. Mide durante gpu_ventana_s (GPU y audio); corta antes si algo falla."""
        minimo = (inactividad_min if inactividad_min is not None else self.c["inactividad_min"]) * 60
        if self.sistema.segundos_sin_entrada() < minimo:
            return "actividad reciente"
        if self.sistema.pantalla_completa():
            return "pantalla completa"
        juego = self.juego_abierto()
        if juego:
            return f"juego abierto ({juego.replace(chr(92), '/').rsplit('/', 1)[-1]})"
        usos, fin, previo = [], self.reloj() + self.c["gpu_ventana_s"], self.sistema.segundos_sin_entrada()
        while self.reloj() < fin:
            sonando = self.audio_que_bloquea()
            if sonando:
                return f"audio ({sonando})"
            uso = self.sistema.uso_gpu()
            if uso is not None:
                usos.append(uso)
            idle = self.sistema.segundos_sin_entrada()
            if idle < previo - 0.2:
                return "actividad reciente"
            previo = idle
            self.dormir(1)
        if self.audio_que_bloquea():
            return "audio"
        if usos and sum(usos) / len(usos) > self.c["gpu_max_pct"]:
            return f"GPU ocupada ({sum(usos) / len(usos):.0f} %)"
        return None


class Guardia:
    """Hilo que vigila mientras dura la reflexión. 'parar' (threading.Event) se activa con el primer motivo."""

    def __init__(self, vigilante, parar, intervalo_s=None, cada_procesos_s=2.0):
        self.v = vigilante
        self.parar = parar
        self.intervalo = intervalo_s if intervalo_s is not None else vigilante.c["vigilancia_ms"] / 1000
        self.cada_procesos = cada_procesos_s
        self.motivo = None
        self._fin = threading.Event()
        self._hilo = None

    def __enter__(self):
        self._hilo = threading.Thread(target=self._vigilar, name="guardia-reflexion", daemon=True)
        self._hilo.start()
        return self

    def __exit__(self, *_):
        self._fin.set()
        self._hilo.join(5)

    def _vigilar(self):
        s = self.v.sistema
        previo = s.segundos_sin_entrada()
        ultimo_procesos = 0.0
        while not self._fin.is_set() and not self.parar.is_set():
            idle = s.segundos_sin_entrada()
            motivo = None
            if idle < previo - 0.2:  # sin entrada, el contador solo crece: si baja, hubo teclado, mouse o mando
                motivo = "actividad (teclado, mouse o mando)"
            elif s.pantalla_completa():
                motivo = "pantalla completa"
            else:
                sonando = self.v.audio_que_bloquea()
                if sonando:
                    motivo = f"audio ({sonando})"
                elif self.v.reloj() - ultimo_procesos >= self.cada_procesos:
                    ultimo_procesos = self.v.reloj()
                    juego = self.v.juego_abierto()
                    if juego:
                        motivo = "juego abierto"
            previo = idle
            if motivo:
                self.motivo = motivo
                self.parar.set()
                return
            self._fin.wait(self.intervalo)
