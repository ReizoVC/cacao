"""La gramática de producción (esquema de agente_minimo.py compilado con la regla "char" estricta de modelo.py) no
deja escribir caracteres de control crudos dentro de las cadenas JSON. Carga solo el vocabulario de Gemma
(vocab_only, sin pesos, 0 capas en la GPU) y pasa cada respuesta token a token por el muestreador de gramática de
llama.cpp: sin generar nada. Compara con la regla original de llama-cpp-python 0.3.36 para que la prueba muestre el
fallo que corrige. Uso: .venv\\Scripts\\python probar_gramatica_json.py"""
import ctypes
import json
import math
import sys

import llama_cpp
from llama_cpp import llama_grammar

import modelo  # aplica la regla estricta al importarse
from guardia_juego import exigir_gpu_libre

fallos = []
ejecutadas = []


def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    print(("OK " if condicion else "MAL ") + nombre + (f": {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


# la de llama-cpp-python 0.3.36 (llama_grammar.PRIMITIVE_RULES["char"]) antes del cambio de modelo.py
CHAR_ORIGINAL = r'[^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])'


def gramatica(esquema, regla_char):
    anterior = llama_grammar.PRIMITIVE_RULES["char"]
    llama_grammar.PRIMITIVE_RULES["char"] = llama_grammar.BuiltinRule(regla_char, [])
    try:  # lo mismo que hace create_chat_completion con response_format (LlamaGrammar.from_json_schema)
        return llama_grammar.json_schema_to_gbnf(json.dumps(esquema))
    finally:
        llama_grammar.PRIMITIVE_RULES["char"] = anterior


exigir_gpu_libre("el vocabulario de Gemma")
import agente_minimo as a  # noqa: E402  (solo el esquema: importar no carga el modelo)

ok("modelo.py deja la regla char estricta en este proceso",
   llama_grammar.PRIMITIVE_RULES["char"].content == modelo.CHAR_ESTRICTO)
ESTRICTA = llama_grammar.json_schema_to_gbnf(json.dumps(a.ESQUEMA_ACCION))
ORIGINAL = gramatica(a.ESQUEMA_ACCION, CHAR_ORIGINAL)
ok("la gramática del esquema de producción usa la regla estricta", r"\x00-\x1F" in ESTRICTA)

params = llama_cpp.llama_model_default_params()
params.vocab_only = True
params.n_gpu_layers = 0
llama_cpp.llama_backend_init()
modelo_vocab = llama_cpp.llama_model_load_from_file(str(a.CONFIG["modelo"]).encode("utf-8"), params)
if not modelo_vocab:
    sys.exit(f"No pude leer el vocabulario de {a.CONFIG['modelo']}")
vocab = llama_cpp.llama_model_get_vocab(modelo_vocab)
EOS = llama_cpp.llama_vocab_eos(vocab)


def tokens(texto):
    datos = texto.encode("utf-8")
    buf = (llama_cpp.llama_token * (len(datos) + 8))()
    n = llama_cpp.llama_tokenize(vocab, datos, len(datos), buf, len(buf), False, False)
    return list(buf[:n])


def acepta(gbnf, texto):
    """True si la gramática deja generar el texto completo y terminar ahí (EOS permitido al final)."""
    muestreador = llama_cpp.llama_sampler_init_grammar(vocab, gbnf.encode("utf-8"), b"root")
    try:
        for t in tokens(texto) + [EOS]:
            dato = (llama_cpp.llama_token_data * 1)()
            dato[0].id, dato[0].logit, dato[0].p = t, 0.0, 0.0
            candidatos = llama_cpp.llama_token_data_array(data=dato, size=1, selected=-1, sorted=False)
            llama_cpp.llama_sampler_apply(muestreador, ctypes.byref(candidatos))
            if math.isinf(dato[0].logit):
                return False
            if t != EOS:
                llama_cpp.llama_sampler_accept(muestreador, t)
        return True
    finally:
        llama_cpp.llama_sampler_free(muestreador)


def accion(pensamiento, herramienta="abrir_app", argumentos=None):
    # json.dumps escapa los controles; para el caso crudo se reemplaza el escape por el carácter real
    return json.dumps({"pensamiento": pensamiento, "herramienta": herramienta,
                       "argumentos": argumentos if argumentos is not None else {"nombre": "calculadora"}},
                      ensure_ascii=False, separators=(",", ":"))


valido = accion("Abro la calculadora.")
ok("acepta una acción normal", acepta(ESTRICTA, valido) and json.loads(valido))

escapado = accion("Primero listo las apps.\nLuego abro la calculadora.")  # queda como \n escapado
ok("acepta un salto de línea escapado (\\n) en el razonamiento", acepta(ESTRICTA, escapado))
ok("el escapado se lee con json.loads", "\n" in json.loads(escapado)["pensamiento"])

crudo = escapado.replace("\\n", "\n")  # salto de línea literal dentro de la cadena
try:
    json.loads(crudo)
    crudo_invalido = False
except json.JSONDecodeError:
    crudo_invalido = True
ok("json.loads rechaza el salto de línea crudo (el fallo de producción)", crudo_invalido)
ok("la regla original de 0.3.36 dejaba generarlo", acepta(ORIGINAL, crudo))
ok("la gramática de producción ya no deja generarlo", not acepta(ESTRICTA, crudo))

tab = accion("Abro\tla calculadora.").replace("\\t", "\t")
ok("tampoco deja un tabulador crudo", not acepta(ESTRICTA, tab))

final_crudo = accion("Respondo.", "finalizar", {"mensaje": "Hecho.\nAlgo más", "exito": True}).replace("\\n", "\n")
ok("tampoco en argumentos (mensaje de finalizar)", not acepta(ESTRICTA, final_crudo))

acentos = accion("Pongo «Año nuevo» en Spotify: canción, ñandú, 30 %.")
ok("no afecta a tildes, eñes ni comillas latinas", acepta(ESTRICTA, acentos))

llama_cpp.llama_model_free(modelo_vocab)
print(f"{len(ejecutadas) - len(fallos)}/{len(ejecutadas)} OK")
sys.exit(1 if fallos else 0)
