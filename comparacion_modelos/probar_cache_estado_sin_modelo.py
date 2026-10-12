"""
Pruebas sin modelo de cache_estado.py con un Llama falso (sin GPU): prefijo alineado a n_batch, restauración antes de
cada llamada, NO restaurar si el estado ya tiene el prompt entero (ruta de visión: fallo de #56 s22/s33) y estado nuevo
si cambia el prompt de sistema.
Uso: .venv\\Scripts\\python comparacion_modelos\\probar_cache_estado_sin_modelo.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llama_cpp  # noqa: E402

import cache_estado  # noqa: E402

fallos, ejecutadas = [], []


def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    print(("OK " if condicion else "MAL ") + nombre + (f": {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


def tokens_de(texto):
    return [ord(c) for c in texto]


class Ctx:
    def __init__(self, llm):
        self.llm, self.ctx = llm, object()

    def kv_cache_seq_rm(self, *args):
        return True

    def kv_cache_clear(self):
        pass


class LlamaFalso:
    n_batch = 4

    def __init__(self):
        self.input_ids = np.zeros(1000, dtype=np.intc)
        self.n_tokens = 0
        self._requires_eval = True
        self._ctx = Ctx(self)
        self.generadas = []

    def reset(self):
        self.n_tokens = 0

    def eval(self, tokens):
        self.input_ids[self.n_tokens:self.n_tokens + len(tokens)] = tokens
        self.n_tokens += len(tokens)

    def generate(self, tokens, *args, **kwargs):
        self.generadas.append((list(tokens), self.n_tokens))
        yield 0

    def create_chat_completion(self, messages, max_tokens=None):
        tokens = [1] + tokens_de(messages[0]["content"]) + [2] + tokens_de(messages[1]["content"]) + [3]
        for _ in self.generate(tokens):
            break


estado = {}
llama_cpp.llama_state_get_size = lambda ctx: 64
llama_cpp.llama_state_get_data = lambda ctx, buffer, n: (estado.__setitem__("guardado", True) or 16)
llama_cpp.llama_state_set_data = lambda ctx, datos, n: (estado.__setitem__("restaurado", estado.get("restaurado", 0) + 1)
                                                       or n)

llm = LlamaFalso()
sistema = {"texto": "sistema largo"}
cache = cache_estado.CacheEstado(llm, lambda: sistema["texto"])
prompt = [1] + tokens_de("sistema largo") + [2] + tokens_de("hola") + [3]
list(llm.generate(prompt))
p = len(cache.prefijo)
ok("prefijo alineado a n_batch", p % llm.n_batch == 0 and p <= len(tokens_de("sistema largo")) + 2, p)
ok("primera llamada: crea el estado y restaura", cache.stats["estados_creados"] == 1 and estado.get("restaurado") == 1)
ok("tras restaurar, generate ve el prefijo ya evaluado", llm.generadas[-1][1] == p, llm.generadas[-1])
# ruta de visión: el estado ya contiene el prompt entero
llm.input_ids[:len(prompt)] = prompt
llm.n_tokens = len(prompt)
list(llm.generate(prompt))
ok("estado con el prompt entero (visión): no se restaura", estado["restaurado"] == 1
   and cache.stats.get("ya_evaluado") == 1 and llm.generadas[-1][1] == len(prompt), cache.stats)
# siguiente llamada normal, con el estado de la anterior (otra continuación): se restaura
otro = [1] + tokens_de("sistema largo") + [2] + tokens_de("hola") + [3] + tokens_de("respuesta")
llm.input_ids[:len(prompt)] = prompt
llm.n_tokens = len(prompt) + 2  # el estado tiene además lo generado
list(llm.generate(otro))
ok("llamada siguiente: se restaura el estado del prompt de sistema", estado["restaurado"] == 2)
# el prompt de sistema cambia (una memoria nueva): estado nuevo
sistema["texto"] = "sistema distinto"
nuevo = [1] + tokens_de("sistema distinto") + [2] + tokens_de("hola") + [3]
list(llm.generate(nuevo))
ok("prompt de sistema nuevo: se crea otro estado", cache.stats["estados_creados"] == 2 and estado["restaurado"] == 3)
# un prompt que no empieza por el prefijo: sin restaurar
list(llm.generate([9, 9, 9, 9, 9, 9, 9, 9]))
ok("prompt sin el prefijo: no se restaura", estado["restaurado"] == 3 and cache.stats["sin_prefijo"] == 1)
print(f"{len(ejecutadas) - len(fallos)}/{len(ejecutadas)} OK")
sys.exit(1 if fallos else 0)
