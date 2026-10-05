"""
Transcripción con el audio NATIVO de Gemma 4 12B (mmproj-F16 trae codificador de audio, proyector gemma4ua).

El handler multimodal vacía la caché KV del contexto que usa. Para no perder la caché del agente (el prompt de
sistema, ~3000 fichas, que costaría ~1,5 s volver a leer), la transcripción usa un SEGUNDO contexto pequeño sobre los
MISMOS pesos ya cargados en la GPU: un clon superficial del objeto Llama con su propio llama_context, batch y
buffers. No se duplica el modelo. Con n_ctx=1024 y lotes de 256 el contexto extra ocupa ~0,4 GB de VRAM (con
2048/512 eran ~0,9 GB); 1024 fichas alcanzan para ~30 s de audio (voz.py corta la grabación ahí).
OJO: depende de atributos internos de llama-cpp-python 0.3.36 (_ctx, _batch, input_ids, scores, n_tokens, _n_ctx).
"""
import base64
import contextlib
import io
import re
import wave

import llama_cpp
import numpy as np
from llama_cpp import _internals as internals

TASA = 16000
# El audio va ANTES de la instrucción y el vocabulario entre paréntesis: con la instrucción delante, en frases
# cortas Gemma copiaba la pista dentro de la transcripción (ver resultados_voz.md).
INSTRUCCION = ("Transcribe literalmente, en español, lo que dice la persona en el audio anterior. Responde solo con "
               "la transcripción.")
# Pista de vocabulario: DESCARTADA. Acertaba las 3 frases de prueba (eran justo esas palabras), pero en uso real
# hacía que Gemma rellenara audios cortos con ella ("¿Qué hay en mi escritorio?" -> "Quita el escritorio"; un
# "abre la calculadora" -> una orden inventada sobre un Excel). Se deja solo para comparar (pista=PISTA).
PISTA = ("abre, busca en internet, pon el volumen, mueve, cierra, ventanas, apps, calculadora, carpeta, Descargas, "
         "Documentos")
# Freno: más palabras de las que caben en los segundos con voz es una transcripción inventada
MAX_PALABRAS_POR_S, PALABRAS_EXTRA = 6, 3


def contar_palabras(texto):
    return len(re.findall(r"\w+", texto))


def transcripcion_plausible(texto, voz_s):
    return contar_palabras(texto) <= MAX_PALABRAS_POR_S * voz_s + PALABRAS_EXTRA


def contexto_auxiliar(llm, n_ctx=1024, n_batch=256):
    """Clon de `llm` que comparte el modelo (pesos en GPU) pero tiene su propio contexto y caché KV."""
    # copy.copy no sirve: Llama define __getstate__/__setstate__ y volvería a cargar el modelo
    clon = object.__new__(type(llm))
    clon.__dict__.update(llm.__dict__)
    params = llama_cpp.llama_context_params.from_buffer_copy(llm.context_params)
    params.n_ctx = n_ctx
    params.n_batch = params.n_ubatch = n_batch  # lotes más chicos: menos VRAM para los buffers de cálculo
    clon.context_params = params
    clon.n_batch = n_batch
    clon._stack = contextlib.ExitStack()
    clon._ctx = clon._stack.enter_context(contextlib.closing(
        internals.LlamaContext(model=llm._model, params=params, verbose=False)))
    clon._batch = clon._stack.enter_context(contextlib.closing(
        internals.LlamaBatch(n_tokens=n_batch, embd=0, n_seq_max=n_ctx, verbose=False)))
    clon._n_ctx = n_ctx
    clon.n_tokens = 0
    clon.input_ids = np.ndarray((n_ctx,), dtype=np.intc)
    clon.scores = np.ndarray((n_batch, llm._n_vocab), dtype=np.single)
    clon._sampler = None
    clon.cache = None
    clon.interrumpir = None  # la transcripción es corta; el atajo se comprueba antes y después
    return clon


def a_wav(audio):
    """int16 mono a 16 kHz -> bytes WAV (libmtmd reconoce el formato por la cabecera)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TASA)
        w.writeframes(np.asarray(audio, dtype=np.int16).tobytes())
    return buf.getvalue()


class TranscriptorNativo:
    def __init__(self, llm, handler, n_ctx=1024, n_batch=256, pista=None):
        self.llm = contexto_auxiliar(llm, n_ctx, n_batch)
        self.handler = handler  # el mismo ManejadorVision del agente: comparte el contexto de mtmd (mmproj)
        self.instruccion = INSTRUCCION + (f" (Son órdenes a un asistente de escritorio; palabras frecuentes: "
                                          f"{pista}.)" if pista else "")
        self.pista = pista

    def transcribir(self, wav_bytes):
        url = "data:audio/wav;base64," + base64.b64encode(wav_bytes).decode()
        mensajes = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": url}},
                                                 {"type": "text", "text": self.instruccion}]}]
        r = self.handler(llama=self.llm, messages=mensajes, temperature=0.0, max_tokens=120)
        texto = r["choices"][0]["message"]["content"].strip().strip('"«»')
        # red de seguridad: si aun así copió la instrucción o la pista, se descarta esa parte
        for eco in ("palabras frecuentes", "asistente de escritorio", "Transcribe literalmente"):
            if eco.lower() in texto.lower():
                lineas = [l for l in texto.splitlines() if eco.lower() not in l.lower()]
                texto = lineas[-1].strip() if lineas else ""
                break
        return texto

    def cerrar(self):
        self.llm._stack.close()


# ---------- faster-whisper (motor elegido tras la validación de 20 grabaciones; ver resultados_voz.md) ----------

def _rutas_cuda_pip():
    """cuBLAS y cuDNN vienen en las ruedas nvidia-* de pip; CTranslate2 las busca en el PATH de DLL."""
    import os
    import site
    for raiz in site.getsitepackages():
        for paquete in ("cublas", "cudnn"):
            carpeta = os.path.join(raiz, "nvidia", paquete, "bin")
            if os.path.isdir(carpeta):
                os.add_dll_directory(carpeta)
                os.environ["PATH"] = carpeta + os.pathsep + os.environ["PATH"]


ALUCINACIONES_WHISPER = ("gracias por ver", "subtítulos", "subtitulos", "amaraorg", "suscríbete", "suscribete",
                         "nos vemos en el próximo video", "gracias por su atención")


class TranscriptorWhisper:
    """faster-whisper en la GPU. Sin pista de vocabulario (initial_prompt) ni texto previo: con pista, Gemma
    rellenaba audios cortos con ella, y Whisper con condition_on_previous_text arrastra frases anteriores."""

    def __init__(self, modelo="large-v3-turbo", dispositivo="cuda", tipo="int8_float16", haz=5, esperar_juego=False):
        from guardia_juego import exigir_gpu_libre
        exigir_gpu_libre("Whisper", esperar=esperar_juego)
        _rutas_cuda_pip()
        from faster_whisper import WhisperModel
        self.modelo = WhisperModel(modelo, device=dispositivo, compute_type=tipo)
        self.haz = haz

    def transcribir(self, wav_bytes):
        with wave.open(io.BytesIO(wav_bytes)) as w:
            audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        segmentos, _ = self.modelo.transcribe(audio, language="es", beam_size=self.haz, vad_filter=False,
                                              condition_on_previous_text=False, without_timestamps=True)
        texto = " ".join(s.text.strip() for s in segmentos).strip()
        # Whisper rellena el silencio y el ruido con frases de subtítulos de YouTube; nunca son órdenes
        plano = re.sub(r"[^a-záéíóúñü ]", "", texto.lower())
        if any(frase in plano for frase in ALUCINACIONES_WHISPER):
            return ""
        return texto

    def descargar(self):
        """Modo juego: libera la VRAM; los pesos se vuelven a leer del disco al cargar."""
        self.modelo.model.unload_model()

    def cargar(self):
        from guardia_juego import exigir_gpu_libre
        exigir_gpu_libre("Whisper", esperar=True)
        self.modelo.model.load_model()

    def cerrar(self):
        self.modelo = None
