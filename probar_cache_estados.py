"""
Pruebas sin modelo de la caché por estados de producción (cache_estados.py, perfil qwen9b "cache_estados": true).
Un Llama falso (sin GPU) sustituye a LlamaRapida y a las funciones de estado de llama.cpp.
  1. modelo.crear_llm crea la caché solo si el perfil la pide (qwen9b sí, gemma no).
  2. Restaura el estado del prompt de sistema antes de cada llamada; nada antes de que pedir_accion lo indique.
  3. Visión: si el estado ya tiene el prompt entero, no se restaura (se borraría la imagen evaluada).
  4. Prompt de sistema nuevo: estado nuevo. Atajo de emergencia mientras se crea: no queda un estado a medias.
  5. Modo juego: al descargar y recargar el modelo, el nuevo trae una caché nueva y vacía; el estado viejo no se usa.
Uso: .venv\\Scripts\\python probar_cache_estados.py
"""
import json
import sys

import numpy as np

import llama_cpp

fallos, ejecutadas = [], []


def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    print(("OK " if condicion else "MAL ") + nombre + (f": {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


def tokens_de(texto):
    return [ord(c) for c in texto]


estados = {"guardados": 0, "restaurados": 0}
llama_cpp.llama_state_get_size = lambda ctx: 64
llama_cpp.llama_state_get_data = lambda ctx, buffer, n: (estados.__setitem__("guardados", estados["guardados"] + 1)
                                                         or 16)
llama_cpp.llama_state_set_data = lambda ctx, datos, n: (estados.__setitem__("restaurados", estados["restaurados"] + 1)
                                                       or n)


class Ctx:
    def __init__(self):
        self.ctx = object()

    def kv_cache_seq_rm(self, *args):
        return True

    def kv_cache_clear(self):
        pass


class LlamaFalso:
    n_batch = 4

    def __init__(self, **kwargs):
        self.input_ids = np.zeros(4000, dtype=np.intc)
        self.n_tokens = 0
        self._requires_eval = True
        self._ctx = Ctx()
        self.generadas, self.cerrado, self.interrumpir_eval = [], False, False

    def reset(self):
        self.n_tokens = 0

    def eval(self, tokens):
        if self.interrumpir_eval:
            raise KeyboardInterrupt("atajo de emergencia")
        self.input_ids[self.n_tokens:self.n_tokens + len(tokens)] = tokens
        self.n_tokens += len(tokens)

    def generate(self, tokens, *args, **kwargs):
        self.generadas.append((list(tokens), self.n_tokens))
        yield 0

    def create_chat_completion(self, messages, max_tokens=None, **kwargs):
        tokens = [1]
        for m in messages:
            tokens += tokens_de(m["content"] if isinstance(m["content"], str) else "img") + [2]
        for _ in self.generate(tokens):
            break
        return {"choices": [{"message": {"content": json.dumps(
            {"pensamiento": "p", "herramienta": "finalizar", "argumentos": {"mensaje": "ok", "exito": True}})}}],
            "usage": {"completion_tokens": 1}}

    def close(self):
        self.cerrado = True


import modelo  # noqa: E402

guardado = modelo.LlamaRapida
modelo.LlamaRapida = LlamaFalso
try:
    base = {"modelo": "x", "n_gpu_layers": -1, "n_ctx": 4096, "flash_attn": True, "type_k": "q8_0", "type_v": "q8_0",
            "modo_gramatica": "topk"}
    con = modelo.crear_llm({**base, "cache_estados": True}, comprobar_juego=False)
    sin = modelo.crear_llm(base, comprobar_juego=False)
finally:
    modelo.LlamaRapida = guardado
ok("crear_llm: con cache_estados hay caché", getattr(con, "cache_estados", None) is not None)
ok("crear_llm: sin la clave (gemma) no hay caché", getattr(sin, "cache_estados", None) is None)
crudo = json.loads(open("config.json", encoding="utf-8").read())
ok("config.json: cache_estados solo en el perfil qwen9b", crudo["perfiles"]["qwen9b"].get("cache_estados") is True
   and "cache_estados" not in crudo["perfiles"]["gemma"] and "cache_estados" not in crudo)

llm, cache = con, con.cache_estados
sistema = [{"role": "system", "content": "sistema largo de prueba"}]
llm.create_chat_completion(sistema + [{"role": "user", "content": "hola"}])
ok("sin el prompt de sistema indicado no se restaura nada", estados["restaurados"] == 0
   and cache.stats["estados_creados"] == 0)
cache.sistema(sistema[0]["content"])
llm.create_chat_completion(sistema + [{"role": "user", "content": "hola"}])
p = len(cache.prefijo)
ok("crea el estado alineado a n_batch y lo restaura", cache.stats["estados_creados"] == 1 and estados["restaurados"] == 1
   and p % llm.n_batch == 0 and p > 0 and llm.generadas[-1][1] == p, (p, cache.stats))
llm.create_chat_completion(sistema + [{"role": "user", "content": "otra cosa"}])
ok("la llamada siguiente vuelve a restaurar, sin crear otro estado", estados["restaurados"] == 2
   and cache.stats["estados_creados"] == 1)
# visión: el manejador multimodal ya evaluó el prompt entero y llama a generate con ese mismo prompt
prompt = [1] + tokens_de(sistema[0]["content"]) + [2] + tokens_de("img") + [2]
llm.input_ids[:len(prompt)] = prompt
llm.n_tokens = len(prompt)
list(llm.generate(prompt))
ok("visión: con el prompt entero ya evaluado no se restaura", estados["restaurados"] == 2
   and cache.stats["ya_evaluado"] == 1 and llm.generadas[-1][1] == len(prompt))
# prompt de sistema nuevo (índice de la wiki, obstáculos): estado nuevo
cache.sistema("sistema distinto de prueba")
llm.create_chat_completion([{"role": "system", "content": "sistema distinto de prueba"},
                            {"role": "user", "content": "hola"}])
ok("prompt de sistema nuevo: estado nuevo", cache.stats["estados_creados"] == 2 and estados["restaurados"] == 3)
# atajo de emergencia mientras se crea el estado: no queda un estado a medias
cache.sistema("un tercer sistema")
llm.interrumpir_eval = True
try:
    llm.create_chat_completion([{"role": "system", "content": "un tercer sistema"}, {"role": "user", "content": "x"}])
    interrumpido = False
except KeyboardInterrupt:
    interrumpido = True
llm.interrumpir_eval = False
ok("atajo durante la creación: se corta y no queda estado", interrumpido and cache.datos is None and cache.texto is None)
llm.create_chat_completion([{"role": "system", "content": "un tercer sistema"}, {"role": "user", "content": "x"}])
ok("la llamada siguiente vuelve a crear el estado", cache.stats["estados_creados"] == 3 and cache.datos is not None)

# modo juego: descargar y recargar el modelo (agente_minimo.descargar_modelos / cargar_modelos)
import agente_minimo as a  # noqa: E402

nuevos = []


def crear_falso(config, **kwargs):
    """El crear_llm de verdad (la caché la pone modelo.crear_llm), con LlamaFalso en vez de LlamaRapida."""
    real = modelo.LlamaRapida
    modelo.LlamaRapida = LlamaFalso
    try:
        llm_nuevo = modelo.crear_llm({**base, **{k: v for k, v in config.items() if k == "cache_estados"}},
                                     comprobar_juego=False)
    finally:
        modelo.LlamaRapida = real
    nuevos.append(llm_nuevo)
    return llm_nuevo


reales = a.crear_llm, a.vision, a.EXTRAS_MODO_JUEGO[:], a.CONFIG
a.crear_llm, a.vision = crear_falso, None
a.EXTRAS_MODO_JUEGO.clear()
a.CONFIG = {**a.CONFIG, "cache_estados": True}
try:
    a.llm = llm
    a.descargar_modelos()
    ok("modo juego: al descargar, el modelo (y su caché) se sueltan", a.llm is None and llm.cerrado)
    a.cargar_modelos()
    nuevo = a.llm
    ok("al recargar: modelo nuevo con caché nueva y vacía", nuevo is not llm and nuevo.cache_estados is not cache
       and nuevo.cache_estados.datos is None and nuevo.cache_estados.stats["estados_creados"] == 0)
    restaurados_viejos = cache.stats["restauraciones"]
    a.pedir_accion([{"role": "system", "content": "sistema tras el juego"}, {"role": "user", "content": "hola"}])
    ok("pedir_accion usa la caché del modelo nuevo; la vieja no se toca",
       nuevo.cache_estados.stats["estados_creados"] == 1 and nuevo.cache_estados.stats["restauraciones"] == 1
       and cache.stats["restauraciones"] == restaurados_viejos, nuevo.cache_estados.stats)
finally:
    a.crear_llm, a.vision, a.CONFIG = reales[0], reales[1], reales[3]
    a.EXTRAS_MODO_JUEGO[:] = reales[2]
    a.llm = None

print(f"{len(ejecutadas) - len(fallos)}/{len(ejecutadas)} OK")
sys.exit(1 if fallos else 0)
