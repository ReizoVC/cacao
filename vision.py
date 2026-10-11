"""
Fase 5, grupo 2: ver_pantalla. Captura la pantalla con mss y se la pasa a Gemma 4 con Gemma4ChatHandler
(libmtmd + mmproj-F16.gguf).

AVISO DE VERSIÓN (llama-cpp-python 0.3.36): MTMDChatHandler no deja elegir cuántos tokens usa cada imagen.
ManejadorVision sustituye su atributo interno _mtmd_cpp por un envoltorio que fija image_min_tokens e
image_max_tokens al crear el contexto de mtmd. Depende de que _init_mtmd_context llame a
self._mtmd_cpp.mtmd_context_params_default(); si al actualizar deja de funcionar, se pierde el presupuesto
(la imagen usa el valor por defecto del modelo) pero ver_pantalla sigue andando.

Además, en 0.3.36 el handler reinicia la caché KV y reevalúa todo el prompt en cada llamada, por eso el
agente solo lo usa cuando el historial tiene una imagen.
"""
import atexit
import base64
import io
import sys
import time

import llama_cpp
import mss
import win32gui
from PIL import Image, ImageDraw
from llama_cpp import mtmd_cpp
from llama_cpp.llama_chat_format import Gemma4ChatHandler

from herramientas_grupo1 import es_titulo_sensible
from modelo import _log_llama

PRESUPUESTOS = (70, 140, 280, 560, 1120)  # los que admite Gemma 4 (ver herramientas.json)
LADO_MAXIMO = 1920  # se reduce antes de codificar; el preprocesador de mtmd vuelve a escalar igual
ultima_captura = None  # info de la última captura: la herramienta mouse la usa para convertir coordenadas


# libmtmd imprime cada imagen o audio que codifica ("encoding image slice..."); solo se dejan pasar los errores,
# con el mismo callback que llama.cpp (modelo.py): se muestran y quedan en errores_llama.log
mtmd_cpp.mtmd_log_set(_log_llama, None)
mtmd_cpp.mtmd_helper_log_set(_log_llama, None)


class _MtmdConPresupuesto:
    """Delega todo en llama_cpp.mtmd_cpp salvo los parámetros por defecto del contexto."""

    def __init__(self, real, manejador):
        self._real, self._manejador = real, manejador

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)

    def mtmd_context_params_default(self):
        params = self._real.mtmd_context_params_default()
        params.image_min_tokens = params.image_max_tokens = self._manejador.presupuesto
        return params


class ManejadorVision(Gemma4ChatHandler):
    def __init__(self, clip_model_path, presupuesto=280, sin_pensamiento=False):
        super().__init__(clip_model_path=str(clip_model_path), verbose=False)
        self.presupuesto = presupuesto
        self.sin_pensamiento = sin_pensamiento  # Qwen: plantilla del modelo sin <think> (modelo.SIN_PENSAMIENTO)
        self._presupuesto_ctx = None
        self._mtmd_cpp = _MtmdConPresupuesto(self._mtmd_cpp, self)
        atexit.register(self.cerrar)

    def fijar_presupuesto(self, presupuesto):
        # el presupuesto se fija al crear el contexto de mtmd: si cambia, se libera y se vuelve a crear
        if presupuesto != self._presupuesto_ctx and self.mtmd_ctx is not None:
            self._mtmd_cpp.mtmd_free(self.mtmd_ctx)
            self.mtmd_ctx = None
        self.presupuesto = presupuesto

    def cerrar(self):
        # libera el contexto antes de que Python cierre stdout: el callback que registra el handler en
        # Llama.__del__ entra en suppress_stdout_stderr y falla con "I/O operation on closed file"
        if self.mtmd_ctx is not None:
            self._mtmd_cpp.mtmd_free(self.mtmd_ctx)
            self.mtmd_ctx = None
        self.verbose = True  # con verbose el callback no toca stdout

    def _init_mtmd_context(self, llama_model):
        super()._init_mtmd_context(llama_model)
        self._presupuesto_ctx = self.presupuesto

    def _get_chat_template(self, llama_model):
        plantilla = super()._get_chat_template(llama_model)
        return ("{% set enable_thinking = false %}" + plantilla) if self.sin_pensamiento else plantilla


def dibujar_cuadricula(imagen, paso=100):
    """Líneas cada 'paso' píxeles con su coordenada, para que el modelo lea x e y en vez de estimarlas."""
    capa = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for x in range(paso, imagen.width, paso):
        d.line([(x, 0), (x, imagen.height)], fill=(255, 0, 255, 110), width=1)
        for y in (2, imagen.height // 2):
            d.rectangle([x + 1, y, x + 32, y + 12], fill=(0, 0, 0, 170))
            d.text((x + 3, y), str(x), fill=(255, 255, 0, 255))
    for y in range(paso, imagen.height, paso):
        d.line([(0, y), (imagen.width, y)], fill=(255, 0, 255, 110), width=1)
        for x in (2, imagen.width // 2):
            d.rectangle([x, y + 1, x + 32, y + 13], fill=(0, 0, 0, 170))
            d.text((x + 2, y + 1), str(y), fill=(0, 255, 255, 255))
    return Image.alpha_composite(imagen.convert("RGBA"), capa).convert("RGB")


class CapturaBloqueada(Exception):
    """La ventana a capturar tiene un título sensible (contraseñas, claves, .env...)."""


def ventanas_visibles():
    """Ventanas visibles con título, de la de arriba a la de abajo (orden Z): [(hwnd, título, rect)]."""
    lista = []

    def agregar(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
            titulo = win32gui.GetWindowText(hwnd)
            if titulo.strip():
                lista.append((hwnd, titulo, win32gui.GetWindowRect(hwnd)))
        return True

    win32gui.EnumWindows(agregar, None)
    return lista


def tapar_sensibles(imagen, zona, ventanas, hwnd_capturada=None):
    """Tapa en la imagen (aún sin reducir, en píxeles de pantalla) las ventanas de título sensible que se ven en
    la zona. Si se captura una sola ventana, solo pueden asomar las que están por encima de ella en el orden Z.
    Devuelve los títulos tapados."""
    d = ImageDraw.Draw(imagen)
    tapadas = []
    for hwnd, titulo, (izq, arr, der, aba) in ventanas:
        if hwnd == hwnd_capturada:
            break  # las de debajo quedan ocultas por la ventana capturada
        if not es_titulo_sensible(titulo):
            continue
        x0, y0 = max(izq, zona["left"]) - zona["left"], max(arr, zona["top"]) - zona["top"]
        x1 = min(der, zona["left"] + zona["width"]) - zona["left"]
        y1 = min(aba, zona["top"] + zona["height"]) - zona["top"]
        if x1 > x0 and y1 > y0:
            d.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))
            d.text((x0 + 8, y0 + 8), "[ventana oculta: contenido sensible]", fill=(255, 255, 255))
            tapadas.append(titulo)
    return tapadas


def _zonas_isla_por_defecto():
    import ui_isla
    return [ui_isla.rect_ventana(h) for h in ui_isla.ventanas_isla()]


# Fase 7: la isla se tapa en negro en toda captura (además de que Windows la excluya con WDA_EXCLUDEFROMCAPTURE);
# sin aviso, para que el modelo ni sepa que está ahí. El agente la cambia por ServidorIsla.zonas_isla.
zonas_isla = _zonas_isla_por_defecto


def tapar_isla(imagen, zona):
    d = ImageDraw.Draw(imagen)
    tapadas = 0
    for izq, arr, der, aba in zonas_isla():
        x0, y0 = max(izq, zona["left"]) - zona["left"], max(arr, zona["top"]) - zona["top"]
        x1 = min(der, zona["left"] + zona["width"]) - zona["left"]
        y1 = min(aba, zona["top"] + zona["height"]) - zona["top"]
        if x1 > x0 and y1 > y0:
            d.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))
            tapadas += 1
    return tapadas


def capturar(region="ventana_activa", cuadricula=False):
    """Devuelve (data_url JPEG, info). info lleva el tamaño enviado y cómo pasar a coordenadas de pantalla:
    las de mss son píxeles físicos, porque mss pone el proceso en modo DPI-aware."""
    global ultima_captura
    with mss.mss() as sct:  # mss activa el modo DPI-aware, así GetWindowRect da píxeles reales
        zona = sct.monitors[0] if region == "completa" else None
        hwnd = None
        if zona is None:
            hwnd = win32gui.GetForegroundWindow()
            if es_titulo_sensible(win32gui.GetWindowText(hwnd)):
                raise CapturaBloqueada("La ventana activa parece tener contraseñas o claves; no la capturo.")
            izq, arr, der, aba = win32gui.GetWindowRect(hwnd)
            zona = {"left": izq, "top": arr, "width": max(1, der - izq), "height": max(1, aba - arr)}
            if win32gui.IsIconic(hwnd) or zona["width"] < 50 or zona["height"] < 50:
                zona, hwnd = sct.monitors[0], None
        toma = sct.grab(zona)
    imagen = Image.frombytes("RGB", toma.size, toma.bgra, "raw", "BGRX")
    tapadas = tapar_sensibles(imagen, zona, ventanas_visibles(), hwnd)
    tapar_isla(imagen, zona)
    escala = min(1.0, LADO_MAXIMO / max(imagen.size))
    if escala < 1.0:
        imagen = imagen.resize((round(imagen.width * escala), round(imagen.height * escala)), Image.LANCZOS)
    if cuadricula:
        imagen = dibujar_cuadricula(imagen)
    buf = io.BytesIO()
    imagen.save(buf, format="JPEG", quality=85)
    data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    info = {"ancho": imagen.width, "alto": imagen.height,
            "origen": (zona["left"], zona["top"]), "escala": escala, "momento": time.time(),
            "ventanas_tapadas": len(tapadas)}
    ultima_captura = info
    return data_url, info
