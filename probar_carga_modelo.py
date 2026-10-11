"""Pruebas sin modelo: importar agente_minimo no carga Gemma; cargar_modelo() lo carga una vez y en el mismo punto
del arranque que antes (modo texto, voz.py, prueba_real.py, medir_ram.py). Usa un modelo falso: no toca la GPU."""
import ast
import sys
from pathlib import Path

BASE = Path(__file__).parent
fallos = []
ejecutadas = []


def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    print(("OK " if condicion else "MAL ") + nombre + (f": {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


import agente_minimo as a  # noqa: E402

ok("importar agente_minimo no carga el modelo", a.llm is None, repr(a.llm))
ok("importar agente_minimo no sincroniza las apps (Get-StartApps)", a._cache_apps == [], len(a._cache_apps))


class LlmFalso:
    interrumpir = None


creados, sincronizados = [], []
guardado = a.crear_llm, a.sincronizar_apps
a.crear_llm = lambda config, **k: creados.append(k) or LlmFalso()
a.sincronizar_apps = lambda: sincronizados.append(1)
try:
    primero = a.cargar_modelo()
    segundo = a.cargar_modelo()
finally:
    a.crear_llm, a.sincronizar_apps = guardado
ok("cargar_modelo crea el modelo una sola vez", len(creados) == 1 and primero is segundo is a.llm, creados)
ok("cargar_modelo espera a que se cierre un juego", creados and creados[0].get("esperar_juego") is True, creados)
ok("cargar_modelo conecta el atajo de emergencia", a.llm.interrumpir == a.emergencia.comprobar)
ok("cargar_modelo sincroniza las apps después de cargar", sincronizados == [1], sincronizados)
a.llm = None

# perfiles: "modelo_activo" elige gemma o qwen9b; volver a Gemma = cambiar esa clave (sin cargar ningún modelo)
import json  # noqa: E402

import modelo  # noqa: E402

crudo = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
ok("config.json tiene modelo_activo y los perfiles gemma y qwen9b",
   crudo.get("modelo_activo") in ("gemma", "qwen9b") and {"gemma", "qwen9b"} <= set(crudo.get("perfiles", {})),
   crudo.get("modelo_activo"))
ok("config.json no fija modelo ni mmproj fuera de los perfiles", not {"modelo", "mmproj", "swa_full"} & set(crudo))
gemma = modelo.aplicar_perfil({**json.loads(json.dumps(crudo)), "modelo_activo": "gemma"})
qwen = modelo.aplicar_perfil({**json.loads(json.dumps(crudo)), "modelo_activo": "qwen9b"})
ok("perfil gemma: Gemma Q5, su mmproj, sin swa_full ni sin_pensamiento",
   "gemma-4-12b" in gemma["modelo"] and gemma["mmproj"] == "modelos/mmproj/mmproj-F16.gguf"
   and "swa_full" not in gemma and not gemma.get("sin_pensamiento") and "perfiles" not in gemma, gemma.get("modelo"))
ok("perfil qwen9b: Qwen 9B Q5 (copia en C:), su mmproj, swa_full false y sin pensamiento",
   "Qwen3.5-9B" in qwen["modelo"] and qwen["mmproj"] == "modelos/comparacion/mmproj-F16.gguf"
   and qwen.get("swa_full") is False and qwen.get("sin_pensamiento") is True, qwen.get("modelo"))
ok("cierre rápido: gemma true, qwen9b false (el ejecutor ignora mensaje_final)",
   gemma.get("cierre_rapido") is True and qwen.get("cierre_rapido") is False)
ok("agente_minimo.CIERRE_RAPIDO sale del perfil activo",
   a.CIERRE_RAPIDO is (gemma if crudo["modelo_activo"] == "gemma" else qwen)["cierre_rapido"], a.CIERRE_RAPIDO)
ok("los dos perfiles comparten el resto (contexto, caché KV, flash attention, mmap, gramática)",
   all(gemma[k] == qwen[k] for k in ("n_ctx", "type_k", "type_v", "flash_attn", "use_mmap", "modo_gramatica")))
ok("ida y vuelta: qwen9b -> gemma da la misma config que gemma",
   modelo.aplicar_perfil({**json.loads(json.dumps(crudo)), "modelo_activo": "gemma"}) == gemma)
try:
    modelo.aplicar_perfil({**json.loads(json.dumps(crudo)), "modelo_activo": "otro"})
    ok("modelo_activo desconocido -> error", False)
except ValueError as e:
    ok("modelo_activo desconocido -> error", "otro" in str(e))
ok("sin perfiles (copias del banco) la config no cambia", modelo.aplicar_perfil({"modelo": "x"}) == {"modelo": "x"})
ok("agente_minimo usa el perfil activo", a.CONFIG["modelo"].name in (Path(gemma["modelo"]).name,
                                                                     Path(qwen["modelo"]).name)
   and a.CONFIG.get("modelo_activo") == crudo["modelo_activo"], a.CONFIG.get("modelo_activo"))

# crear_llm: swa_full del perfil a llama-cpp-python (sin la clave, su valor por defecto) y plantilla sin pensamiento
argumentos, manejadores = [], []
guardado = modelo.LlamaRapida, modelo.manejador_sin_pensamiento
modelo.LlamaRapida = lambda **k: argumentos.append(k) or LlmFalso()
modelo.manejador_sin_pensamiento = lambda llm: manejadores.append(llm) or "manejador"
try:
    llm_qwen = modelo.crear_llm(qwen, comprobar_juego=False)
    llm_gemma = modelo.crear_llm(gemma, comprobar_juego=False)
finally:
    modelo.LlamaRapida, modelo.manejador_sin_pensamiento = guardado
ok("crear_llm: qwen9b pasa swa_full=False", argumentos[0].get("swa_full") is False, argumentos[0].get("swa_full"))
ok("crear_llm: gemma, el valor por defecto de llama-cpp-python", argumentos[1].get("swa_full") is None)
ok("crear_llm: solo qwen9b usa la plantilla sin pensamiento",
   getattr(llm_qwen, "chat_handler", None) == "manejador" and not hasattr(llm_gemma, "chat_handler")
   and len(manejadores) == 1)
ok("la plantilla sin pensamiento es la del banco",
   modelo.SIN_PENSAMIENTO in (BASE / "comparacion_modelos" / "ejecutar.py").read_text(encoding="utf-8"))


def primera_sentencia(ruta, funcion=None):
    arbol = ast.parse((BASE / ruta).read_text(encoding="utf-8"))
    if funcion:
        cuerpo = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == funcion).body
    else:  # el bloque if __name__ == "__main__"
        cuerpo = next(n for n in arbol.body if isinstance(n, ast.If) and "__main__" in ast.unparse(n.test)).body
    sentencias = [ast.unparse(n) for n in cuerpo]
    return next(s for s in sentencias if "salida_utf8()" not in s)  # la salida UTF-8 va antes (probar_salida_utf8)


ok("modo texto: lo primero del arranque es cargar_modelo()",
   primera_sentencia("agente_minimo.py") == "cargar_modelo()", primera_sentencia("agente_minimo.py"))
ok("voz.py: preparar() carga el modelo antes que Whisper y Piper",
   primera_sentencia("voz.py", "preparar") == "a.cargar_modelo()", primera_sentencia("voz.py", "preparar"))
for ruta in ("prueba_real.py", "medir_ram.py"):
    ok(f"{ruta} llama a cargar_modelo()", "a.cargar_modelo()" in (BASE / ruta).read_text(encoding="utf-8"))

print(f"{len(ejecutadas) - len(fallos)}/{len(ejecutadas)} OK")
sys.exit(1 if fallos else 0)
