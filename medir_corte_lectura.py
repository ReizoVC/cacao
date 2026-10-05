"""
Mide cuánto tarda el atajo de emergencia en cortar cuando se pulsa mientras el modelo LEE un prompt largo
(como el resultado de listar_carpeta con 100 archivos), antes y después de comprobarlo entre bloques de n_batch.
Herramientas simuladas (benchmark_gramatica); el atajo se envía con simular_atajo (mismo WM_HOTKEY que Windows).
Uso: .venv\\Scripts\\python medir_corte_lectura.py   -> resultados_corte_lectura.json
"""
import json
import threading
import time
import types
from pathlib import Path

from llama_cpp import Llama

import benchmark_gramatica as b

em = b.emergencia
# texto largo para que la lectura dure varios segundos (unas 6700 fichas)
LINEAS = [f"Archivo {i}: informe_{i}_version_{i * 7 % 13}.pdf, modificado el día {i % 28 + 1}, tamaño {i * 37} KB."
          for i in range(200)]
FRASE = "Resume en una frase esta lista de archivos:\n" + "\n".join(LINEAS)
filas = []


def medir(nombre, retraso):
    momento = {}

    def disparar():
        momento["t"] = time.perf_counter()
        em.simular_atajo()

    threading.Timer(retraso, disparar).start()
    t0 = time.perf_counter()
    r = b.correr("topk", 11, FRASE)
    fin = time.perf_counter()
    em.reanudar()
    fila = {"variante": nombre, "atajo_a_los_s": retraso, "segundos_totales": round(fin - t0, 2),
            "ms_desde_el_atajo": round((fin - momento["t"]) * 1000) if "t" in momento else None,
            "cortada": r["respuesta"] is not None and "atajo de emergencia" in r["respuesta"],
            "tokens_generados": r.get("n_sample", 0)}
    filas.append(fila)
    print(json.dumps(fila, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    b.correr("topk", 1, "hola")  # calentamiento
    n = len(b.llm.tokenize(FRASE.encode("utf-8"), add_bos=False))
    print(f"prompt de la tarea: {n} fichas; n_batch={b.llm.n_batch}")
    # referencia: cuánto dura la lectura sin cortar
    t = time.perf_counter()
    b.llm.reset()
    b.llm.eval(b.llm.tokenize(FRASE.encode("utf-8")))
    lectura = time.perf_counter() - t
    print(f"lectura completa: {lectura:.2f} s")
    nueva = b._eval
    for variante, funcion in (("antes (eval original)", types.MethodType(Llama.eval, b.llm)),
                              ("después (comprueba entre bloques)", nueva)):
        b._eval = funcion
        for retraso in (0.3, lectura / 2):
            b.llm.reset()  # que la lectura empiece desde cero, sin reutilizar la caché
            medir(variante, round(retraso, 2))
    b._eval = nueva
    # tras un corte a mitad de lectura (sin reset), la caché queda coherente y la tarea siguiente funciona
    threading.Timer(1.0, em.simular_atajo).start()
    b.correr("topk", 11, FRASE)
    em.reanudar()
    r = b.correr("topk", 11, "pon el volumen al 30")
    siguiente = {"herramientas": r["herramientas"], "respuesta": r["respuesta"], "error": r["error"]}
    print("tarea siguiente tras cortar a mitad de lectura:", siguiente)
    Path(__file__).with_name("resultados_corte_lectura.json").write_text(
        json.dumps({"fichas_prompt": n, "lectura_s": round(lectura, 2), "filas": filas, "tarea_siguiente": siguiente}, ensure_ascii=False,
                   indent=1), encoding="utf-8")
