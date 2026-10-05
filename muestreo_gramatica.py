"""
Muestreo con gramática más rápido para llama-cpp-python.

Problema: Llama._init_sampler mete la gramática ANTES de top_k, así que en cada paso llama.cpp
valida los ~262.000 tokens del vocabulario de Gemma contra la gramática (~125 ms/token contra ~26).

Dos estrategias:
  "topk"     (a) penalizaciones -> top_k -> gramática sobre esos candidatos -> resto de la cadena.
                 Si ningún candidato es válido, se repite con la gramática sobre el vocabulario completo.
  "rechazo"  (b) como common_sampler_sample de llama.cpp: se muestrea sin gramática, se valida solo
                 el token elegido y, si no es válido, se vuelve a muestrear con la gramática completa.

AVISO DE VERSIÓN: esto sobrescribe Llama._init_sampler, un método INTERNO de llama-cpp-python
probado con la versión 0.3.36. Depende de que Llama.sample() llame a self._sampler.sample(ctx, idx)
y de las firmas de llama_get_logits_ith / llama_sampler_apply / llama_sampler_accept. Si al actualizar
llama-cpp-python algo falla, pasa MODO_GRAMATICA = None (o no uses LlamaRapida) y vuelve a medir.
"""
import ctypes

import numpy as np
import llama_cpp
from llama_cpp import Llama
from llama_cpp import _internals as internals

VERSION_PROBADA = "0.3.36"

_DTYPE = np.dtype([("id", np.int32), ("logit", np.float32), ("p", np.float32)], align=True)
assert _DTYPE.itemsize == ctypes.sizeof(llama_cpp.llama_token_data)


class MuestreadorGramatica:
    """Imita la interfaz de internals.LlamaSampler que usa Llama.sample(): sample(ctx, idx)."""

    def __init__(self, llm, modo, grammar, top_k, top_p, min_p, typical_p, temp,
                 repeat_penalty, frequency_penalty, presence_penalty):
        self.modo = modo
        self.interrumpir = llm.interrumpir  # p. ej. el atajo de emergencia: lanza una excepción para cortar
        self.n_vocab = llm._n_vocab
        self.ids = np.arange(self.n_vocab, dtype=np.int32)
        self.buf = np.zeros(self.n_vocab, dtype=_DTYPE)
        self.uno = np.zeros(1, dtype=_DTYPE)
        self.top_k = top_k if top_k > 0 else self.n_vocab

        # cada etapa es una cadena aparte para poder intercalar la gramática donde convenga
        self.pen = internals.LlamaSampler()
        self.pen.add_penalties(n_vocab=self.n_vocab, penalty_last_n=llm.last_n_tokens_size,
                               penalty_repeat=repeat_penalty, penalty_freq=frequency_penalty,
                               penalty_present=presence_penalty)
        self.topk = internals.LlamaSampler()
        self.topk.add_top_k(self.top_k)
        self.gram = internals.LlamaSampler()
        self.gram.add_grammar(llm._model, grammar)
        self.post = internals.LlamaSampler()
        if temp == 0.0:
            self.post.add_greedy()
        else:
            self.post.add_typical(typical_p, 1)
            self.post.add_top_p(top_p, 1)
            self.post.add_min_p(min_p, 1)
            self.post.add_temp(temp)
            self.post.add_dist(llm._seed)
        # estadísticas para el benchmark
        self.pasos = 0
        self.respaldos = 0

    # --- utilidades ---

    def _llenar(self, ctx, idx):
        ptr = llama_cpp.llama_get_logits_ith(ctx.ctx, idx)
        self.buf["id"] = self.ids  # los samplers reordenan el arreglo en su sitio
        self.buf["logit"] = np.ctypeslib.as_array(ptr, shape=(self.n_vocab,))
        self.buf["p"] = 0.0
        arr = llama_cpp.llama_token_data_array(
            data=self.buf.ctypes.data_as(llama_cpp.llama_token_data_p),
            size=self.n_vocab, selected=-1, sorted=False)
        return arr

    @staticmethod
    def _aplicar(sampler, arr):
        llama_cpp.llama_sampler_apply(sampler.sampler, ctypes.byref(arr))

    @staticmethod
    def _vista(arr):
        n = arr.size
        direccion = ctypes.cast(arr.data, ctypes.c_void_p).value
        return np.frombuffer((ctypes.c_char * (n * _DTYPE.itemsize)).from_address(direccion), dtype=_DTYPE)

    def _token_valido(self, token):
        self.uno["id"] = token
        self.uno["logit"] = 0.0
        arr = llama_cpp.llama_token_data_array(
            data=self.uno.ctypes.data_as(llama_cpp.llama_token_data_p), size=1, selected=-1, sorted=False)
        self._aplicar(self.gram, arr)
        return np.isfinite(self.uno["logit"][0])

    def _completo(self, ctx, idx):
        # igual que la cadena original: penalizaciones -> gramática (vocabulario entero) -> top_k -> resto
        self.respaldos += 1
        arr = self._llenar(ctx, idx)
        for etapa in (self.pen, self.gram, self.topk, self.post):
            self._aplicar(etapa, arr)
        return arr.data[arr.selected].id

    # --- interfaz usada por Llama.sample ---

    def sample(self, ctx, idx=-1):
        if self.interrumpir is not None:
            self.interrumpir()
        self.pasos += 1
        if self.modo == "topk":
            arr = self._llenar(ctx, idx)
            self._aplicar(self.pen, arr)
            self._aplicar(self.topk, arr)
            self._aplicar(self.gram, arr)
            v = self._vista(arr)
            validos = v[np.isfinite(v["logit"])]
            if len(validos):
                # se dejan solo los válidos y ordenados: con sorted=True, softmax y min_p toman
                # data[0] como máximo y un -inf ahí produciría NaN
                self.cand = np.ascontiguousarray(validos[np.argsort(-validos["logit"], kind="stable")])
                arr = llama_cpp.llama_token_data_array(
                    data=self.cand.ctypes.data_as(llama_cpp.llama_token_data_p),
                    size=len(self.cand), selected=-1, sorted=True)
                self._aplicar(self.post, arr)
                token = arr.data[arr.selected].id
            else:
                token = self._completo(ctx, idx)
        else:  # "rechazo"
            arr = self._llenar(ctx, idx)
            for etapa in (self.pen, self.topk, self.post):
                self._aplicar(etapa, arr)
            token = arr.data[arr.selected].id
            if not self._token_valido(token):
                token = self._completo(ctx, idx)
        for etapa in (self.pen, self.gram, self.post):
            etapa.accept(token)
        return token

    def close(self):
        for etapa in (self.pen, self.topk, self.gram, self.post):
            etapa.close()


class LlamaRapida(Llama):
    """Llama con muestreo de gramática rápido. modo_gramatica: "topk", "rechazo" o None (original)."""

    def __init__(self, *args, modo_gramatica="topk", **kwargs):
        if llama_cpp.__version__ != VERSION_PROBADA:
            print(f"Aviso: muestreo_gramatica se probó con llama-cpp-python {VERSION_PROBADA} "
                  f"y tienes {llama_cpp.__version__}; si falla, usa modo_gramatica=None.")
        self.modo_gramatica = modo_gramatica
        self.ultimo_muestreador = None
        self.interrumpir = None  # función que se llama en cada token con gramática; puede lanzar para cortar
        super().__init__(*args, **kwargs)

    def eval(self, tokens):
        # la lectura del prompt (resultados largos de herramientas) no muestrea tokens: sin esto, el atajo de
        # emergencia esperaba a que terminara (~4 s). Se comprueba entre bloques de n_batch tokens; si corta a
        # mitad, n_tokens e input_ids quedan coherentes con lo ya evaluado y la caché se reutiliza después.
        for i in range(0, len(tokens), self.n_batch):
            if self.interrumpir is not None:
                self.interrumpir()
            super().eval(tokens[i:i + self.n_batch])

    # Sobrescribe un método interno de llama-cpp-python 0.3.36 (ver aviso al inicio del archivo).
    def _init_sampler(self, top_k=40, top_p=0.95, min_p=0.05, typical_p=1.0, temp=0.80,
                      repeat_penalty=1.0, frequency_penalty=0.0, presence_penalty=0.0, tfs_z=1.0,
                      mirostat_mode=0, mirostat_eta=0.1, mirostat_tau=5.0, penalize_nl=True,
                      logits_processor=None, grammar=None):
        if (self.modo_gramatica is None or grammar is None or logits_processor is not None
                or mirostat_mode != 0 or temp < 0.0):
            self.ultimo_muestreador = None
            return super()._init_sampler(
                top_k=top_k, top_p=top_p, min_p=min_p, typical_p=typical_p, temp=temp,
                repeat_penalty=repeat_penalty, frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty, tfs_z=tfs_z, mirostat_mode=mirostat_mode,
                mirostat_eta=mirostat_eta, mirostat_tau=mirostat_tau, penalize_nl=penalize_nl,
                logits_processor=logits_processor, grammar=grammar)
        m = MuestreadorGramatica(self, self.modo_gramatica, grammar, top_k, top_p, min_p, typical_p,
                                 temp, repeat_penalty, frequency_penalty, presence_penalty)
        self.ultimo_muestreador = m
        return m
