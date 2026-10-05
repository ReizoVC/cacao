"""
Regla: con un juego abierto no se carga nada en la GPU (ni Gemma, ni el mmproj, ni Whisper).

Usa la misma detección que el modo juego (deteccion.Vigilante.juego_abierto: categoría 'juegos' o carpeta de juegos,
sin lanzadores ni Wallpaper Engine). La llaman modelo.crear_llm y transcripcion.TranscriptorWhisper, así que vale
para todo: scripts de prueba y medición, y el agente.
  - Pruebas y mediciones (por defecto): no esperan; terminan con un aviso, para avisar a Reizo en vez de quitarle
    la GPU a quien está jugando. Con la variable de entorno ESPERAR_JUEGO=1 esperan a que se cierre.
  - El agente (esperar=True): avisa y espera a que se cierre el juego antes de cargar.
"""
import os
import time


class _SinEntrada:
    def segundos_sin_entrada(self):
        return 0.0


def juego_abierto():
    """Nombre del juego abierto (con las reglas del modo juego) o None."""
    import habitos
    from deteccion import SistemaWindows, Vigilante
    vigilante = Vigilante(SistemaWindows(_SinEntrada()), habitos.Clasificador(), habitos.MW)
    ruta = vigilante.juego_abierto()
    return vigilante.clasificador.info(ruta)["nombre"] if ruta else None


def exigir_gpu_libre(que="el modelo", esperar=False, cada_s=30, avisar=print, detectar=juego_abierto):
    juego = detectar()
    if not juego:
        return
    esperar = esperar or os.environ.get("ESPERAR_JUEGO") == "1"
    if not esperar:
        raise SystemExit(f"[GPU] {juego} está abierto: no cargo {que} (con un juego abierto no se usa la GPU). "
                         "Ciérralo o lanza con ESPERAR_JUEGO=1 para esperar.")
    avisar(f"[GPU] {juego} está abierto: espero a que se cierre para cargar {que}.")
    while detectar():
        time.sleep(cada_s)
    avisar(f"[GPU] {juego} cerrado: cargo {que}.")
