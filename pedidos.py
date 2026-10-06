"""
Pedidos de Reizo por escrito: la consola y el campo de texto de la isla, en una sola cola.

El texto de la isla entra exactamente como si se escribiera en la consola (o se dijera, en modo voz): pasa por
atender_con_memoria, con los mismos permisos, bloqueos, modo sin confirmación y confirmaciones físicas. La isla solo
acepta texto después de un clic físico en su campo (lo comprueba su hook de mouse), y la herramienta teclado del
agente no puede escribir en ella (herramientas_grupo4.planificar_teclado_ventana).
"""
import queue
import threading

MAX_PEDIDO = 2000  # caracteres; lo mismo que admite el campo de la isla


def limpiar(texto):
    """El texto de un pedido de la isla, o None si no vale (no es texto o está vacío). Se recorta a MAX_PEDIDO."""
    if not isinstance(texto, str):
        return None
    texto = " ".join(texto.split())[:MAX_PEDIDO]
    return texto or None


class ColaPedidos:
    """('consola' | 'isla' | 'fin', texto). La consola lee en su propio hilo, y solo cuando el bucle está listo
    (así el "Tú: " no se imprime en medio de una respuesta)."""

    def __init__(self, leer=input):
        self.cola = queue.Queue()
        self._leer = leer
        self._listo = threading.Event()

    def desde_isla(self, texto):
        texto = limpiar(texto)
        if texto:
            self.cola.put(("isla", texto))

    def iniciar_consola(self, prompt="\nTú: "):
        threading.Thread(target=self._consola, args=(prompt,), name="consola", daemon=True).start()
        return self

    def _consola(self, prompt):
        while True:
            self._listo.wait()
            self._listo.clear()
            try:
                texto = self._leer(prompt)
            except (EOFError, KeyboardInterrupt):
                self.cola.put(("fin", None))
                return
            self.cola.put(("consola", texto))

    def listo(self):
        """El bucle terminó el pedido anterior: la consola puede volver a preguntar."""
        self._listo.set()

    def siguiente(self, timeout=None):
        """El próximo pedido, o None si pasó 'timeout'. Espera en pasos cortos para que Ctrl+C funcione en Windows."""
        limite = None if timeout is None else timeout
        esperado = 0.0
        while limite is None or esperado < limite:
            try:
                return self.cola.get(timeout=0.2)
            except queue.Empty:
                esperado += 0.2
        return None

    def pedido_isla(self):
        """Para el modo voz (sin consola): el próximo texto de la isla, sin esperar, o None."""
        try:
            origen, texto = self.cola.get_nowait()
        except queue.Empty:
            return None
        return texto if origen == "isla" else None
