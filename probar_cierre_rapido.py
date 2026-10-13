"""
Pruebas sin modelo del cierre rápido (mensaje_final): decisión del usuario del 2026-10-11
(cerebro/decisiones/cierre-rapido-mensaje-final.md).
  1. mensaje_final pasa por validar_finalizacion: si afirma algo sin verificar, se descarta y la tarea sigue.
  2. Con CIERRE_RAPIDO = False (perfil qwen9b) el ejecutor ignora mensaje_final y exige finalizar.
atender() se copia de agente_minimo.py con ast; el modelo es un guion de acciones y las herramientas son simuladas.
Textos de mensaje_final: los de Qwen 9B en la 65 × 3 con producción, semilla 11
(comparacion_modelos/datos/swa_cache/qwen65x3_A.json).
Uso: .venv\\Scripts\\python probar_cierre_rapido.py
"""
import ast
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import herramientas_grupo4
import modo_directo
from protecciones_ejecucion import nueva_proteccion, registrar_resultado, resultado_verificado, validar_finalizacion

BASE = Path(__file__).parent
fallos, ejecutadas = [], []


def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    print(("OK " if condicion else "MAL ") + nombre + (f": {detalle}" if detalle else ""))
    if not condicion:
        fallos.append(nombre)


NOMBRES = {"atender", "terminar", "rellenar_marcadores", "con_fecha", "DIAS", "MESES", "_tarea", "_decision",
           "_modos", "ACCIONES_A_VERIFICAR", "MAX_RECORDATORIOS", "MENSAJE_DETENIDO", "TEXTO_EXTERNO",
           "CON_MARCADORES"}


def cargar(guion, cierre_rapido=True):
    """atender() con un modelo que devuelve las acciones del guion en orden. Devuelve (ns, llamadas)."""
    arbol = ast.parse((BASE / "agente_minimo.py").read_text(encoding="utf-8"))
    nodos = [n for n in arbol.body if (isinstance(n, ast.FunctionDef) and n.name in NOMBRES)
             or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in NOMBRES for t in n.targets))]
    acciones, llamadas = list(guion), []

    def ejecutar(nombre, args):
        llamadas.append(nombre)
        if nombre == "volumen":
            return {"ok": True, "volumen_actual": args.get("cantidad", 60), "silenciado": args.get("accion") == "silenciar"}
        if nombre == "abrir_app":
            return {"ok": True, "app_abierta": args.get("nombre")}
        return {"ok": True}

    ns = {"json": json, "time": time, "datetime": datetime, "re": re, "modo_directo": modo_directo, "herramientas_grupo4": herramientas_grupo4,
          "nueva_proteccion": nueva_proteccion, "registrar_resultado": registrar_resultado,
          "resultado_verificado": resultado_verificado, "validar_finalizacion": validar_finalizacion,
          "Detenido": KeyError, "MAX_PASOS": 8, "CIERRE_RAPIDO": cierre_rapido, "CAMINO_RAPIDO": False, "print": lambda *a, **k: None,
          "emergencia": type("E", (), {"comprobar": staticmethod(lambda: None),
                                       "detenido": staticmethod(lambda: False)})(),
          "notificar": lambda *a, **k: None, "enviar_modos": lambda: None, "compactar_historial": lambda h: None,
          "memoria": type("M", (), {"registrar_bloqueo": staticmethod(lambda *a: None)})(),
          "experiencia_inicio": lambda pedido: "", "experiencia_paso": lambda *a: None, "experiencia_ayuda": lambda pedido: "Probé 5 caminos y ninguno funcionó.", "MAX_ALTERNATIVAS": 5,
          "pedir_accion": lambda historial: acciones.pop(0), "ejecutar": ejecutar}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "agente_minimo.py", "exec"), ns)
    return ns, llamadas


def paso(herramienta, argumentos, mensaje_final=None):
    accion = {"pensamiento": "p", "herramienta": herramienta, "argumentos": argumentos}
    if mensaje_final is not None:
        accion["mensaje_final"] = mensaje_final
    return accion


def fin(mensaje):
    return paso("finalizar", {"mensaje": mensaje, "exito": True})


# 1. Los textos de Qwen (semilla 11) con solo el primer paso hecho y verificado
CASOS = {
    29: ("sube el volumen y abre spotify", paso("volumen", {"accion": "subir", "cantidad": 10},
                                                "Listo, subí el volumen a 60% y abro Spotify."),
         paso("abrir_app", {"nombre": "Spotify"}), "Listo, subí el volumen y abrí Spotify."),
    30: ("abre la calculadora y pon el volumen al 20", paso("abrir_app", {"nombre": "Calculadora"},
                                                            "Listo, abrí la Calculadora y puse el volumen al 20%."),
         paso("volumen", {"accion": "fijar", "cantidad": 20}), "Listo, abrí la Calculadora y puse el volumen al 20%."),
    31: ("silencia el volumen y abre el bloc de notas", paso("volumen", {"accion": "silenciar"},
                                                             "Silencié el volumen. Ahora abro el Bloc de notas."),
         paso("abrir_app", {"nombre": "Bloc de notas"}), "Silencié el volumen y abrí el Bloc de notas."),
    34: ("pon el volumen al 40 y luego ábreme WhatsApp", paso("volumen", {"accion": "fijar", "cantidad": 40},
                                                              "Listo, puse el volumen al 40%."),
         paso("abrir_app", {"nombre": "WhatsApp"}), "Listo, puse el volumen al 40% y abrí WhatsApp."),
}

print("-- con cierre rápido (perfil gemma): mensaje_final pasa por validar_finalizacion")
for i, (pedido, primero, segundo, final) in CASOS.items():
    ns, llamadas = cargar([primero, segundo, fin(final)])
    respuesta = ns["atender"](pedido, [{"role": "system", "content": "s"}])
    rechazado = llamadas == [primero["herramienta"], segundo["herramienta"]]
    if i == 30:  # afirma el volumen sin haberlo tocado: se descarta y sigue
        ok(f"#{i}: mensaje_final que afirma lo no hecho se descarta y la tarea sigue",
           rechazado and ns["_tarea"]["proteccion"]["correcciones"] == 1 and respuesta == final, (llamadas, respuesta))
    else:  # no afirma nada sin evidencia («abro», o solo el volumen): validar_finalizacion lo acepta
        ok(f"#{i}: mensaje_final sin afirmaciones falsas se acepta (límite conocido: tarea a medias)",
           llamadas == [primero["herramienta"]] and respuesta == primero["mensaje_final"], (llamadas, respuesta))

# los otros (c) de las semillas 22 y 33 (qwen65x3s2233_A.json): afirman la app que no se abrió
for i, primero, mensaje in [(31, paso("volumen", {"accion": "silenciar"}), "Silencié el volumen y abrí el Bloc de notas."),
                            (34, paso("volumen", {"accion": "fijar", "cantidad": 40}),
                             "Listo, puse el volumen al 40% y abrí WhatsApp.")]:
    ns, llamadas = cargar([{**primero, "mensaje_final": mensaje}, fin("No pude abrirla.")])
    respuesta = ns["atender"](CASOS[i][0], [{"role": "system", "content": "s"}])
    ok(f"#{i} (s22/s33): «{mensaje}» se descarta", respuesta == "No pude abrirla."
       and ns["_tarea"]["proteccion"]["correcciones"] == 1, (llamadas, respuesta))

ns, llamadas = cargar([paso("volumen", {"accion": "fijar", "cantidad": 30},"Listo, puse el volumen al {volumen_actual}%.")])
respuesta = ns["atender"]("pon el volumen al 30", [{"role": "system", "content": "s"}])
ok("tarea de un paso verificada: sigue respondiendo con mensaje_final sin otra llamada",
   llamadas == ["volumen"] and respuesta == "Listo, puse el volumen al 30%.", (llamadas, respuesta))

falso = paso("abrir_app", {"nombre": "Calculadora"}, "Listo, abrí la Calculadora y puse el volumen al 20%.")
ns, llamadas = cargar([falso, dict(falso)])
respuesta = ns["atender"]("abre la calculadora y pon el volumen al 20", [{"role": "system", "content": "s"}])
ok("dos mensaje_final sin evidencia: cuentan como correcciones y la tarea termina preguntando",
   ns["_tarea"]["proteccion"]["correcciones"] == 2 and respuesta.endswith("¿Cómo quieres que continúe?"),
   (llamadas, respuesta))

print("-- sin cierre rápido (perfil qwen9b, CIERRE_RAPIDO = False): se ignora mensaje_final y se exige finalizar")
for i, (pedido, primero, segundo, final) in CASOS.items():
    ns, llamadas = cargar([primero, segundo, fin(final)], cierre_rapido=False)
    respuesta = ns["atender"](pedido, [{"role": "system", "content": "s"}])
    ok(f"#{i}: el modelo sigue hasta finalizar, sin contar correcciones",
       llamadas == [primero["herramienta"], segundo["herramienta"]] and respuesta == final
       and ns["_tarea"]["proteccion"]["correcciones"] == 0, (llamadas, respuesta))
ns, llamadas = cargar([paso("volumen", {"accion": "fijar", "cantidad": 30}, "Listo, puse el volumen al 30%."),
                       fin("Volumen al 30%.")], cierre_rapido=False)
respuesta = ns["atender"]("pon el volumen al 30", [{"role": "system", "content": "s"}])
ok("tarea de un paso: responde con finalizar, no con mensaje_final",
   llamadas == ["volumen"] and respuesta == "Volumen al 30%.", (llamadas, respuesta))

print(f"{len(ejecutadas) - len(fallos)}/{len(ejecutadas)} OK")
sys.exit(1 if fallos else 0)
