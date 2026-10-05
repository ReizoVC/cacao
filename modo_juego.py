"""
Modo juego: con un juego ACTIVO el agente libera la VRAM descargando Gemma (con el mmproj de visión) y Whisper, y
los recarga cuando termina. Usa deteccion.DetectorJuegos (el mismo que la reflexión): un juego cuenta si tiene una
ventana visible o usa la GPU de forma sostenida, y termina tras 2 min sin esas señales; un juego en la bandeja (Roblox
al cerrarlo) no cuenta. Sin lanzadores (Steam, Epic...) ni Wallpaper Engine. "estoy jugando" / "ya terminé" lo
fuerzan (estoy_jugando / ya_termine), sin esperar las comprobaciones.

  - Para entrar hacen falta 'confirmar' comprobaciones seguidas con juego (cada intervalo_s); para salir, otras tantas
    sin juego: así un juego que se reinicia o un lanzador que abre y cierra procesos no provocan recargas seguidas.
  - Descarga y recarga con el cerrojo del planificador (el mismo que toma cada pedido): nunca a mitad de una tarea o
    de una reflexión. Antes de descargar se pide parar la reflexión.
  - Un pedido en modo juego no llega al modelo: recibe mensaje() ("estoy en pausa..."). Mientras se recarga, el
    pedido espera al cerrojo y se atiende con el modelo ya cargado.
"""
import threading
import time

NORMAL, DESCARGANDO, JUEGO, RECARGANDO = "normal", "descargando", "juego", "recargando"


class ModoJuego:
    def __init__(self, vigilante, cerrojo, descargar, cargar, parar_reflexion=lambda: None, intervalo_s=5,
                 confirmar=2, anotar=print, reloj=time.perf_counter):
        self.vigilante, self.cerrojo = vigilante, cerrojo
        self.descargar, self.cargar, self.parar_reflexion = descargar, cargar, parar_reflexion
        self.intervalo, self.confirmar, self.anotar, self.reloj = intervalo_s, confirmar, anotar, reloj
        self.estado = NORMAL
        self.juego = None          # nombre del juego que provocó la pausa
        self.tiempos = []          # [{'accion': 'descargar' | 'cargar', 'segundos': x, 'juego': ...}]
        self.error = None
        self._con_juego = self._sin_juego = 0
        self._fin = threading.Event()
        self._hilo = None

    # ----- consulta -----

    def en_pausa(self):
        """Nombre del juego si el agente está en pausa (descargando o con el modelo fuera); si no, None."""
        return self.juego if self.estado in (DESCARGANDO, JUEGO) else None

    def mensaje(self):
        return (f"Estoy en pausa porque {self.juego or 'un juego'} está abierto: liberé la GPU para el juego. "
                "Vuelvo en cuanto lo cierres.")

    # ----- bucle -----

    def iniciar(self):
        self._hilo = threading.Thread(target=self._bucle, name="modo-juego", daemon=True)
        self._hilo.start()
        return self

    def cerrar(self):
        self._fin.set()

    def _bucle(self):
        while not self._fin.wait(self.intervalo):
            try:
                self.comprobar()
            except Exception as e:  # nunca debe tumbar al agente
                self.error = f"{type(e).__name__}: {e}"
                self.anotar(f"[modo juego] error: {self.error}")
                self._fin.wait(60)

    def comprobar(self):
        """Una comprobación (el hilo la repite cada intervalo_s; las pruebas la llaman directamente)."""
        ruta = self.vigilante.juego_abierto()
        if ruta and self.estado == NORMAL:
            self._con_juego += 1
            self._sin_juego = 0
            if self._con_juego >= self.confirmar:
                self._entrar(self._nombre(ruta))
        elif not ruta and self.estado == JUEGO:
            self._sin_juego += 1
            self._con_juego = 0
            if self._sin_juego >= self.confirmar:
                self._salir()
        else:
            self._con_juego = self._sin_juego = 0

    def _nombre(self, ruta):
        try:
            return self.vigilante.detector.nombre(ruta)
        except Exception:
            return ruta.replace("\\", "/").rsplit("/", 1)[-1]

    # ----- comandos de Reizo -----

    def estoy_jugando(self):
        """Fuerza la pausa ahora (descarga sin esperar las comprobaciones). Devuelve la respuesta para Reizo."""
        self.vigilante.detector.estoy_jugando()
        if self.estado == NORMAL:
            self._entrar(self._nombre(self.vigilante.juego_abierto()))
        return "Vale, libero la GPU para que juegues. Dime \"ya terminé\" cuando acabes."

    def ya_termine(self):
        """Da por terminados los juegos activos y recarga ya (tarda unos segundos)."""
        self.vigilante.detector.ya_termine()
        if self.estado == JUEGO and not self.vigilante.juego_abierto():
            self._salir()
            return "Listo, ya volví. ¿En qué te ayudo?"
        if self.estado == JUEGO:  # sigue habiendo otro juego activo
            return self.mensaje()
        return "No estaba en pausa; sigo aquí."

    def _entrar(self, juego):
        self.parar_reflexion()
        with self.cerrojo:  # espera a que termine el pedido o la reflexión en curso
            self.juego, self.estado = juego, DESCARGANDO
            t0 = self.reloj()
            self.descargar()
            self.tiempos.append({"accion": "descargar", "segundos": round(self.reloj() - t0, 2), "juego": juego})
            self.estado = JUEGO
        self._con_juego = 0
        self.anotar(f"[modo juego] {juego} abierto: modelos descargados en {self.tiempos[-1]['segundos']} s")

    def _salir(self):
        with self.cerrojo:
            self.estado = RECARGANDO
            t0 = self.reloj()
            try:
                self.cargar()
            except Exception:
                self.estado = JUEGO  # sigue en pausa; se reintenta en la próxima comprobación sin juego
                raise
            self.tiempos.append({"accion": "cargar", "segundos": round(self.reloj() - t0, 2), "juego": self.juego})
            self.estado, self.juego = NORMAL, None
        self._sin_juego = 0
        self.anotar(f"[modo juego] juego cerrado: modelos recargados en {self.tiempos[-1]['segundos']} s")
