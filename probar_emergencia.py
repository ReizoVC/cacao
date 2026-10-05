"""
Prueba programática del atajo de emergencia con el agente completo (herramientas simuladas). No pulsa teclas:
envía al hilo del atajo el mismo mensaje WM_HOTKEY que manda Windows cuando se pulsa ctrl+alt+shift+q.
Uso: .venv\\Scripts\\python probar_emergencia.py
"""
import json
import threading
import time
from pathlib import Path

import benchmark_gramatica as b

em = b.emergencia
filas = []


def registrar(nombre, ok, **datos):
    filas.append({"prueba": nombre, "ok": ok, **datos})
    print(f"{'OK ' if ok else 'MAL'} {nombre}: {json.dumps(datos, ensure_ascii=False)}", flush=True)


if __name__ == "__main__":
    registrar("Windows aceptó registrar el atajo", bool(em.registrado), atajo=em.atajo)
    b.correr("topk", 1, "hola")

    # 1) mientras el modelo genera: se dispara a los 0,8 s de empezar una respuesta larga
    for retraso in (0.8, 1.5):
        momento = {}

        def disparar():
            momento["t"] = time.perf_counter()
            em.simular_atajo()

        threading.Timer(retraso, disparar).start()
        t0 = time.perf_counter()
        r = b.correr("topk", 11, "cuéntame una historia larga sobre un dragón y un caballero")
        fin = time.perf_counter()
        latencia = (fin - momento["t"]) * 1000 if "t" in momento else None
        registrar(f"corta durante la generación (atajo a los {retraso} s)",
                  r["respuesta"] is not None and "atajo de emergencia" in r["respuesta"],
                  respuesta=r["respuesta"], segundos_totales=round(fin - t0, 2),
                  ms_desde_el_atajo=round(latencia, 1) if latencia else None, tokens=r.get("tokens"))
        em.reanudar()

    # 2) mientras se espera una confirmación: el atajo llega antes de responder "s"; la herramienta no se ejecuta
    entrada_original = b.ns["confirmar"]

    def confirmar_tras_atajo(*_a, **_k):
        em.simular_atajo()
        time.sleep(0.05)  # deja que el hilo del atajo procese el mensaje
        return True

    b.ns["confirmar"] = confirmar_tras_atajo
    r = b.correr("topk", 11, "renombra Spark.txt de mis descargas a spark_copia.txt")
    b.ns["confirmar"] = entrada_original
    ejecutadas = [p for p in r["planes"] if p["herramienta"] == "mover_archivo"]
    registrar("corta al confirmar y no ejecuta la herramienta",
              r["respuesta"] is not None and "atajo de emergencia" in r["respuesta"] and not ejecutadas,
              herramientas=r["herramientas"], respuesta=r["respuesta"], mover_ejecutado=bool(ejecutadas))
    em.reanudar()

    # 3) pulsado ENTRE tareas: no se descarta; las tareas siguientes no empiezan hasta reanudar
    em.simular_atajo()  # pulsado mientras el agente esperaba un pedido
    time.sleep(0.05)
    for frase in ("pon el volumen al 30", "¿qué apps de música tengo?"):
        r = b.correr("topk", 11, frase)
        registrar(f"detenido entre tareas: no ejecuta «{frase}»",
                  r["herramientas"] == [] and r["respuesta"] == b.ns["MENSAJE_DETENIDO"],
                  herramientas=r["herramientas"], respuesta=r["respuesta"])

    # 4) tras reanudar, la tarea siguiente funciona normal
    em.reanudar()
    r = b.correr("topk", 11, "pon el volumen al 30")
    registrar("tras reanudar, la tarea siguiente funciona", r["herramientas"] == ["volumen"] and r["error"] is None,
              herramientas=r["herramientas"], respuesta=r["respuesta"])
    registrar("cuenta todas las pulsaciones", em.pulsaciones == 4, pulsaciones=em.pulsaciones)

    Path(__file__).with_name("resultados_emergencia.json").write_text(
        json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nTODO OK" if all(f["ok"] for f in filas) else "\nHAY FALLOS")
