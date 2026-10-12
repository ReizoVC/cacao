"""
Caché por estados del prompt de sistema (perfil qwen9b, "cache_estados": true; Gemma no la usa porque ya reutiliza el
prefijo). Decisión del usuario del 2026-10-11; probada en el banco (cerebro/modelos/prompt-y-cache.md, fase A).

Qwen 3.5 no reutiliza el prefijo de la caché KV: llama-cpp-python intenta kv_cache_seq_rm y su memoria híbrida
(recurrente) lo rechaza, así que recalculaba ≈ 4 300 tokens en cada llamada. Aquí se guarda el estado de llama.cpp
justo después del prompt de sistema y se restaura antes de cada llamada cuyo prompt empieza por esos tokens.

- modelo.crear_llm() crea una caché nueva para cada modelo: al descargarlo (modo juego) o recargarlo, el estado
  anterior desaparece con él.
- pedir_accion() indica el prompt de sistema vigente (sistema()); si cambia, el estado se vuelve a crear.
- El prefijo se obtiene capturando, sin evaluarlos, los tokens que llegan a generate() con dos pedidos distintos, y se
  guarda en el último múltiplo de n_batch: así el resto se evalúa en los mismos bloques que sin caché (en el banco,
  salidas idénticas en 42 casos con greedy).
- Si el estado ya contiene el prompt entero (la visión evalúa texto e imagen y luego llama a create_completion con ese
  prompt), no se restaura: se borraría lo evaluado.
- Si kv_cache_seq_rm falla tras restaurar, generate() hace lo de siempre (todo el prompt): sin ahorro, correcto.
"""
import ctypes

import llama_cpp


class _Capturado(Exception):
    pass


def _comun(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


class CacheEstados:
    def __init__(self, llm):
        self.llm = llm
        self.generar = llm.generate
        self.recortar = llm._ctx.kv_cache_seq_rm
        self.texto_pedido = None  # el prompt de sistema vigente (lo fija pedir_accion)
        self.texto = None  # el del estado guardado
        self.prefijo, self.datos, self.n_bytes = [], None, 0
        self.stats = {"estados_creados": 0, "restauraciones": 0, "ya_evaluado": 0, "sin_prefijo": 0,
                      "seq_rm_ok": 0, "seq_rm_falla": 0}
        self._ultima_restaurada = False
        llm.generate = self.generate
        llm._ctx.kv_cache_seq_rm = self.kv_cache_seq_rm

    def sistema(self, texto):
        self.texto_pedido = texto

    def _capturar_prefijo(self, texto):
        capturas = []

        def capturar(tokens, *args, **kwargs):
            capturas.append(list(tokens))
            raise _Capturado  # en el primer paso: no evalúa nada
            yield

        self.llm.generate = capturar
        try:
            for pedido in ("AAAA uno", "ZZZZ dos"):  # el método de la clase: sin envolturas
                try:
                    type(self.llm).create_chat_completion(self.llm, messages=[{"role": "system", "content": texto},
                                                                              {"role": "user", "content": pedido}],
                                                          max_tokens=1)
                except _Capturado:
                    pass
        finally:
            self.llm.generate = self.generate
        return capturas[0][:_comun(capturas[0], capturas[1])]

    def crear(self, texto):
        self.datos, self.texto = None, None  # si se interrumpe (atajo de emergencia), no queda un estado a medias
        comun = self._capturar_prefijo(texto)
        self.prefijo = comun[:(len(comun) // self.llm.n_batch) * self.llm.n_batch]
        self.llm.reset()
        self.llm._ctx.kv_cache_clear()
        self.llm.eval(self.prefijo)
        n = llama_cpp.llama_state_get_size(self.llm._ctx.ctx)
        buffer = (ctypes.c_uint8 * int(n))()
        self.n_bytes = int(llama_cpp.llama_state_get_data(self.llm._ctx.ctx, buffer, n))
        self.datos = (ctypes.c_uint8 * self.n_bytes).from_buffer_copy(bytes(buffer)[:self.n_bytes])
        self.texto = texto
        self.stats["estados_creados"] += 1

    def restaurar(self):
        if llama_cpp.llama_state_set_data(self.llm._ctx.ctx, self.datos, self.n_bytes) != self.n_bytes:
            raise RuntimeError("llama_state_set_data no restauró el estado completo")
        p = len(self.prefijo)
        self.llm.input_ids[:p] = self.prefijo
        self.llm.n_tokens = p
        self.llm._requires_eval = True
        self.stats["restauraciones"] += 1

    def generate(self, tokens, *args, **kwargs):
        tokens = list(tokens)
        self._ultima_restaurada = False
        actual = self.llm.input_ids[:self.llm.n_tokens].tolist()
        ya_evaluado = self.llm.n_tokens == len(tokens) and actual == tokens
        if ya_evaluado:
            self.stats["ya_evaluado"] += 1
        elif self.texto_pedido is not None:
            if self.datos is None or self.texto != self.texto_pedido:
                self.crear(self.texto_pedido)
            p = len(self.prefijo)
            if p and len(tokens) > p and tokens[:p] == self.prefijo:
                self.restaurar()
                self._ultima_restaurada = True
            else:
                self.stats["sin_prefijo"] += 1
        yield from self.generar(tokens, *args, **kwargs)

    def kv_cache_seq_rm(self, *args):
        ok = self.recortar(*args)
        if self._ultima_restaurada:
            self.stats["seq_rm_ok" if ok else "seq_rm_falla"] += 1
            self._ultima_restaurada = False
        return ok
