"""
Regla: con un juego abierto no se carga nada en la GPU (ni Gemma, ni el mmproj, ni Whisper).

Usa la misma detección que el modo juego (deteccion.DetectorJuegos): un proceso de juego (categoría 'juegos' o
carpeta de juegos, sin lanzadores ni Wallpaper Engine) cuenta solo si tiene una ventana visible o usa la GPU de forma
sostenida; un juego que quedó en la bandeja no bloquea. Como aquí no hay historial, la GPU se mide 10 s.
La llaman modelo.crear_llm y transcripcion.TranscriptorWhisper, así que vale para todo: scripts de prueba y
medición, y el agente.
  - Pruebas y mediciones (por defecto): no esperan; terminan con un aviso, para avisar a Reizo en vez de quitarle
    la GPU a quien está jugando. Con la variable de entorno ESPERAR_JUEGO=1 esperan a que se cierre.
  - El agente (esperar=True): avisa y espera a que se cierre el juego antes de cargar.
"""
import os
import time


class _SinEntrada:
    def segundos_sin_entrada(self):
        return 0.0


def juego_abierto(sistema=None, dormir=time.sleep, reloj=time.monotonic):
    """Nombre del juego activo (con las reglas del modo juego) o None. Sin procesos de juego responde al momento;
    con alguno, mira sus ventanas y mide su uso de GPU durante 10 s."""
    import habitos
    from deteccion import DetectorJuegos, SistemaWindows
    sistema = sistema or SistemaWindows(_SinEntrada())
    clasificador = habitos.Clasificador()
    if not any(clasificador.es_juego(ruta) for _, ruta in sistema.procesos()):
        return None
    detector = DetectorJuegos(sistema, clasificador, {**habitos.MW.get("juegos", {}), "gpu_ventana_s": 10,
                                                      "muestreo_s": 0}, reloj=reloj)
    for i in range(3):
        detector.muestrear()
        if detector._vigentes():
            break
        if i < 2:
            dormir(5)
    ruta = detector.activo()
    return detector.nombre(ruta) if ruta else None


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
