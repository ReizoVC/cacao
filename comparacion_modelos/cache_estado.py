"""
Caché por estados del prompt de sistema (fase A, solo banco; producción no lo usa).

Qwen 3.5 no reutiliza el prefijo de la caché KV: llama-cpp-python intenta kv_cache_seq_rm y su memoria híbrida
(recurrente) lo rechaza, así que recalcula ≈ 4 300 tokens en cada llamada (cerebro/modelos/prompt-y-cache.md).
Aquí se guarda el estado de llama.cpp justo después del prompt de sistema y se restaura antes de cada llamada cuyo
prompt empieza por esos mismos tokens; generate() ve entonces un prefijo ya evaluado y solo lee el resto.

- El prefijo se obtiene de llamadas reales: se capturan (sin evaluarlos) los tokens que llegan a generate() con el
  prompt de sistema y dos pedidos distintos, y se toma su parte común.
- La restauración copia solo el estado de llama.cpp (llama_state_set_data) y los tokens; no copia la matriz scores
  de Llama.load_state (n_batch × vocabulario, cientos de MB con Qwen).
- Si el prompt de sistema cambia (p. ej. una memoria nueva), el estado se vuelve a crear.
- Si kv_cache_seq_rm también falla tras restaurar, generate() hace lo de siempre (todo el prompt): sin ahorro, pero
  correcto. Se anota.
"""
import ctypes
import time

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


class CacheEstado:
    def __init__(self, llm, sistema, alinear=True):
        """sistema: función sin argumentos que devuelve el texto del prompt de sistema vigente. alinear: guardar el
        estado en el último múltiplo de n_batch del prefijo (las mismas cuentas que sin caché)."""
        self.llm, self.sistema, self.alinear = llm, sistema, alinear
        self.generar = llm.generate
        self.recortar = llm._ctx.kv_cache_seq_rm
        self.texto = None
        self.prefijo, self.datos, self.n_bytes = [], None, 0
        self.stats = {"estados_creados": 0, "segundos_crear": [], "bytes_estado": 0, "restauraciones": 0,
                      "segundos_restaurar": [], "sin_prefijo": 0, "seq_rm_ok": 0, "seq_rm_falla": 0,
                      "tokens_prefijo": 0}
        self._ultima_restaurada = False
        llm.generate = self.generate
        llm._ctx.kv_cache_seq_rm = self.kv_cache_seq_rm

    def _capturar_prefijo(self, texto):
        capturas = []

        def capturar(tokens, *args, **kwargs):
            capturas.append(list(tokens))
            raise _Capturado  # en el primer paso: no evalúa nada
            yield

        self.llm.generate = capturar
        try:
            for pedido in ("AAAA uno", "ZZZZ dos"):  # el método de la clase: sin las envolturas de medida del banco
                try:
                    type(self.llm).create_chat_completion(self.llm, messages=[{"role": "system", "content": texto},
                                                                              {"role": "user", "content": pedido}],
                                                          max_tokens=1)
                except _Capturado:
                    pass
        finally:
            self.llm.generate = self.generate
        return capturas[0][:_comun(capturas[0], capturas[1])]

    def crear(self):
        t = time.perf_counter()
        self.texto = self.sistema()
        comun = self._capturar_prefijo(self.texto)
        # alineado a n_batch: sin caché, el prompt se evalúa en bloques de n_batch desde la posición 0. Si el estado
        # se guarda en un múltiplo de n_batch, el resto se evalúa en los mismos bloques y las cuentas coinciden.
        corte = (len(comun) // self.llm.n_batch) * self.llm.n_batch if self.alinear else len(comun)
        self.prefijo = comun[:corte]
        self.stats["tokens_prefijo_comun"] = len(comun)
        self.llm.reset()
        self.llm._ctx.kv_cache_clear()
        self.llm.eval(self.prefijo)
        n = llama_cpp.llama_state_get_size(self.llm._ctx.ctx)
        buffer = (ctypes.c_uint8 * int(n))()
        self.n_bytes = int(llama_cpp.llama_state_get_data(self.llm._ctx.ctx, buffer, n))
        self.datos = (ctypes.c_uint8 * self.n_bytes).from_buffer_copy(bytes(buffer)[:self.n_bytes])
        self.stats["estados_creados"] += 1
        self.stats["segundos_crear"].append(round(time.perf_counter() - t, 3))
        self.stats["bytes_estado"] = self.n_bytes
        self.stats["tokens_prefijo"] = len(self.prefijo)

    def restaurar(self):
        t = time.perf_counter()
        if llama_cpp.llama_state_set_data(self.llm._ctx.ctx, self.datos, self.n_bytes) != self.n_bytes:
            raise RuntimeError("llama_state_set_data no restauró el estado completo")
        p = len(self.prefijo)
        self.llm.input_ids[:p] = self.prefijo
        self.llm.n_tokens = p
        self.llm._requires_eval = True
        self.stats["restauraciones"] += 1
        self.stats["segundos_restaurar"].append(round(time.perf_counter() - t, 4))

    def generate(self, tokens, *args, **kwargs):
        tokens = list(tokens)
        if self.datos is None or self.sistema() != self.texto:
            self.crear()
        p = len(self.prefijo)
        self._ultima_restaurada = len(tokens) > p and tokens[:p] == self.prefijo
        if self._ultima_restaurada:
            self.restaurar()
        else:
            self.stats["sin_prefijo"] += 1
        yield from self.generar(tokens, *args, **kwargs)

    def kv_cache_seq_rm(self, *args):
        ok = self.recortar(*args)
        if self._ultima_restaurada:
            self.stats["seq_rm_ok" if ok else "seq_rm_falla"] += 1
            self._ultima_restaurada = False
        return ok

    def resumen(self):
        s = dict(self.stats)
        for k in ("segundos_crear", "segundos_restaurar"):
            v = s.pop(k)
            s[k.replace("segundos", "s") + "_media"] = round(sum(v) / len(v), 4) if v else None
            s[k.replace("segundos", "s") + "_max"] = max(v) if v else None
        s["mb_estado"] = round(s["bytes_estado"] / 2**20, 1)
        return s
