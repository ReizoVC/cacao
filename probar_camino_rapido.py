"""
Pruebas sin modelo del camino rápido (camino_rapido.py y su enganche en agente_minimo.atender()).
  1. Las 17 frases de cerebro/pruebas/frases-simples.md entran con la herramienta y los argumentos esperados.
  2. Una batería de frases que NO deben entrar: negaciones, condiciones, compuestos, casi iguales, números raros, apps
     desconocidas o genéricas, rutas y URLs.
  3. El agente (atender y atender_con_memoria copiados con ast, sin modelo): pasa por el MISMO ejecutar(), responde
     con el resultado verificado, cede al modelo si no se verifica, respeta rechazo, bloqueo y atajo de emergencia.
  4. Modo juego: solo el volumen, sin llamar al modelo ni cargarlo; lo demás sigue en pausa.
  5. Mutaciones: quitar cada freno hace fallar al menos una prueba.
Uso: .venv\\Scripts\\python probar_camino_rapido.py
"""
import ast
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import camino_rapido as cr
import herramientas_grupo4
import modo_directo
from protecciones_ejecucion import (cierre_no_pedido, nueva_proteccion, quitar_forzar_no_pedido, registrar_resultado,
                                    resultado_verificado, validar_finalizacion)

BASE = Path(__file__).parent
FUENTE = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
APPS = {"spotify": "Spotify", "la calculadora": "Calculadora", "calculadora": "Calculadora",
        "el bloc de notas": "Bloc de notas", "google chrome": "Google Chrome", "discord": "Discord"}


def resolver(nombre):
    """Como resolver_app_rapido, pero permisivo a propósito: el resolvedor real usa búsqueda aproximada y podría dar
    «Spotify» para «spotify y discord»; así las pruebas dependen de los frenos de camino_rapido, no del resolvedor."""
    return any(app in nombre for app in APPS)


ENTRAN = {  # las 17 frases (pruebas.json y pruebas_nuevas_30.json)
    "baja el volumen": ("volumen", {"accion": "bajar", "cantidad": 10}),
    "sube el volumen un poco": ("volumen", {"accion": "subir", "cantidad": 10}),
    "pon el volumen al 30": ("volumen", {"accion": "fijar", "cantidad": 30}),
    "silencia el sonido": ("volumen", {"accion": "silenciar"}),
    "quita el silencio": ("volumen", {"accion": "activar"}),
    "¿a cuánto está el volumen?": ("volumen", {"accion": "consultar"}),
    "pon el volumen al máximo": ("volumen", {"accion": "fijar", "cantidad": 100}),
    "abre spotify": ("abrir_app", {"nombre": "spotify"}),
    "abre la calculadora": ("abrir_app", {"nombre": "la calculadora"}),
    "abre el bloc de notas": ("abrir_app", {"nombre": "el bloc de notas"}),
    "abre Google Chrome": ("abrir_app", {"nombre": "google chrome"}),
    "abre discord": ("abrir_app", {"nombre": "discord"}),
    "deja de registrar lo que hago": ("registro_habitos", {"accion": "pausar"}),
    "déjame el sonido a cuarenta y cinco por ciento": ("volumen", {"accion": "fijar", "cantidad": 45}),
    "vuelve a activar el audio del equipo": ("volumen", {"accion": "activar"}),
    "inicia la aplicación de calculadora": ("abrir_app", {"nombre": "calculadora"}),
    "reanuda el registro de mis hábitos": ("registro_habitos", {"accion": "reanudar"}),
}
VARIANTES = {  # mismas órdenes con «Cacao», «por favor», mayúsculas y puntuación
    "Cacao, pon el volumen al 30.": ("volumen", {"accion": "fijar", "cantidad": 30}),
    "por favor, baja el volumen": ("volumen", {"accion": "bajar", "cantidad": 10}),
    "PON EL VOLUMEN AL 30%": ("volumen", {"accion": "fijar", "cantidad": 30}),
    "pon el volumen a cien": ("volumen", {"accion": "fijar", "cantidad": 100}),
    "pon el volumen al 0": ("volumen", {"accion": "fijar", "cantidad": 0}),
    "silencia": ("volumen", {"accion": "silenciar"}),
}
NO_ENTRAN = [
    # negaciones y condiciones
    "no subas el volumen", "no abras spotify", "no pongas el volumen al 30", "si puedes, abre spotify",
    "si está muy alto, baja el volumen", "baja el volumen si está alto", "nunca silencies el sonido",
    # compuestos
    "sube el volumen y abre spotify", "abre la calculadora y pon el volumen al 20", "abre spotify y busca jazz",
    "silencia el volumen y abre el bloc de notas", "pon el volumen al 40 y luego ábreme WhatsApp",
    "abre spotify, chrome y discord", "abre spotify y discord", "baja el volumen y después súbelo",
    "ajusta el audio al veinticinco por ciento y abre Spotify", "primero abre el bloc de notas y después silencia el equipo",
    # casi iguales / paráfrasis / preguntas
    "está muy fuerte", "no escucho nada", "ponlo más bajito", "haz que se escuche un poco menos fuerte",
    "¿abro spotify?", "abro spotify", "quiero usar Discord, ábrelo", "abre spotify en el portátil",
    "abre spotify otra vez", "baja el volumen de spotify", "sube el volumen de discord", "baja el brillo",
    "pon el volumen al 30 en spotify", "silencia discord", "abre el navegador", "abre algo para escribir",
    "abre el editor de código", "abre el de fotos", "cierra spotify", "abre la carpeta de descargas",
    "deja de registrar lo que hago en discord", "¿qué apps de música tengo?", "hola, ¿cómo estás?",
    # números raros
    "pon el volumen al 150", "pon el volumen al 101", "pon el volumen al -5", "pon el volumen al 30.5",
    "pon el volumen al treinta y cero", "pon el volumen a mil", "pon el volumen al cuarenta y doce",
    "pon el volumen al 30 o 40", "pon el volumen al máximo y abre spotify",
    # apps desconocidas, rutas y URLs
    "abre fotoshop pro ultra edición", "abre C:\\Windows\\regedit.exe", "abre www.google.com",
    "abre youtube.com", "abre notas.txt", "abre https://ejemplo.com", "abre la app que usé ayer",
    "", "   ",
]
fallos, ejecutadas = [], []
silencio = False  # durante las mutaciones los fallos son lo esperado: no se imprimen


def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    if not condicion:
        if not silencio:
            print("MAL " + nombre + (f": {detalle}" if detalle else ""))
        fallos.append(nombre)


def pruebas_reconocedor(rec=None):
    """Devuelve el número de fallos (para las mutaciones); imprime solo los fallos."""
    rec = rec or cr.reconocer
    antes = len(fallos)
    for frase, esperado in {**ENTRAN, **VARIANTES}.items():
        ok(f"entra: {frase}", rec(frase, resolver) == esperado, rec(frase, resolver))
    for frase in NO_ENTRAN:
        ok(f"no entra: {frase!r}", rec(frase, resolver) is None, rec(frase, resolver))
    ok("sin resolvedor, abrir_app no entra", rec("abre spotify") is None)
    ok("app que el resolvedor no da: al modelo", rec("abre winamp", resolver) is None)
    ok("en pausa: el volumen sí", rec("pon el volumen al 30", resolver, solo={"volumen"}) is not None)
    for frase in ("abre spotify", "deja de registrar lo que hago", "reanuda el registro de mis hábitos"):
        ok(f"en pausa no entra: {frase}", rec(frase, resolver, solo={"volumen"}) is None)
    return len(fallos) - antes


# ---------- el agente, sin modelo ----------
NOMBRES = {"atender", "atender_con_memoria", "paso_rapido", "terminar", "rellenar_marcadores", "con_fecha", "DIAS",
           "MESES", "_tarea", "_decision", "_modos", "ACCIONES_A_VERIFICAR", "MAX_RECORDATORIOS", "MENSAJE_DETENIDO",
           "TEXTO_EXTERNO", "CON_MARCADORES", "ejecutar", "decision_modo", "GUARDAN_SOBRE_REIZO", "SOLO_CONSULTAN",
           "camino_conocido", "anotar_intento", "legible", "nombre_app", "NOMBRES_APPS", "comando_modo_juego"}


class Detenido(Exception):
    pass


def cargar(fuente=FUENTE, resultados=None, modelo=None, detenido=False, pulsa_atajo=False, en_pausa=False):
    """atender y compañía copiados de agente_minimo con ast. resultados: {herramienta: resultado simulado}.
    modelo: lista de acciones del modelo (si se le llama sin acciones, la prueba falla)."""
    arbol = ast.parse(fuente)
    nodos = [n for n in arbol.body if (isinstance(n, ast.FunctionDef) and n.name in NOMBRES)
             or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in NOMBRES for t in n.targets))]
    catalogo = json.loads((BASE / "herramientas.json").read_text(encoding="utf-8"))
    acciones = list(modelo or [])
    traza = {"implementaciones": [], "decision_modo": 0, "modelo": 0, "carga_modelo": 0, "confirmaciones": 0}

    def pedir_accion(historial):
        traza["modelo"] += 1
        if not acciones:
            raise AssertionError("se llamó al modelo")
        return acciones.pop(0)

    def implementacion(nombre):
        def f(**args):
            traza["implementaciones"].append((nombre, args))
            return dict((resultados or {}).get(nombre, {"ok": True}))
        return f

    class Emergencia:
        momento = None

        @staticmethod
        def detenido():
            return detenido

        @staticmethod
        def comprobar():
            if pulsa_atajo:
                raise Detenido("Detenido por el atajo.")

    juego = type("J", (), {"en_pausa": staticmethod(lambda: en_pausa), "mensaje": staticmethod(lambda: "PAUSA"),
                           "ya_termine": staticmethod(lambda: "fin"), "estoy_jugando": staticmethod(lambda: "juego")})()

    class Planificador:
        indice_cambiado = False

        def pedido(self):
            traza["carga_modelo"] += 1  # reservar el modelo: en pausa no debe ocurrir
            import contextlib
            return contextlib.nullcontext()

    ns = {"json": json, "re": re, "time": time, "datetime": datetime, "print": lambda *a, **k: None,
          "modo_directo": modo_directo, "herramientas_grupo4": herramientas_grupo4, "camino_rapido": cr,
          "CAMINO_RAPIDO": True, "CIERRE_RAPIDO": True, "resolver_app_rapido": resolver,
          "nueva_proteccion": nueva_proteccion, "registrar_resultado": registrar_resultado,
          "resultado_verificado": resultado_verificado, "validar_finalizacion": validar_finalizacion,
          "cierre_no_pedido": cierre_no_pedido, "quitar_forzar_no_pedido": quitar_forzar_no_pedido,
          "Detenido": Detenido, "emergencia": Emergencia(), "MAX_PASOS": 6, "PLANIFICADORES": {},
          "HERRAMIENTAS": {h["nombre"]: h for h in catalogo["herramientas"]},
          "confirmar": lambda *a, **k: traza.__setitem__("confirmaciones", traza["confirmaciones"] + 1) or True,
          "notificar": lambda *a, **k: None, "enviar_modos": lambda: None, "compactar_historial": lambda h: None,
          "memoria": type("M", (), {"registrar_bloqueo": staticmethod(lambda *a: None)})(),
          "obstaculos": type("O", (), {"consultar": staticmethod(lambda *a: None), "contar_uso": staticmethod(lambda *a: None),
                                        "nombre_atajo": staticmethod(lambda t: ""), "para_prompt": staticmethod(lambda: [])})(),
          "pedir_accion": pedir_accion, "_modo_juego": juego, "normalizar": cr.normalizar,
          "FRASES_TERMINE": ["ya termine"], "FRASES_JUGANDO": ["estoy jugando"], "_isla": None}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "agente_minimo.py", "exec"), ns)
    ns["IMPLEMENTACIONES"] = {h: implementacion(h) for h in ns["HERRAMIENTAS"]}
    ns["_politica"] = None
    decision = ns["decision_modo"]

    def decision_espia(nombre, args):  # prueba de que la acción pasa por el ejecutor de siempre
        traza["decision_modo"] += 1
        return decision(nombre, args)

    ns["decision_modo"] = decision_espia
    ns["traza"] = traza
    return ns


VOLUMEN_OK = {"volumen": {"ok": True, "volumen_actual": 30, "silenciado": False}}


def pruebas_agente(fuente=FUENTE):
    antes = len(fallos)
    h = [{"role": "system", "content": "s"}]
    ns = cargar(fuente, VOLUMEN_OK)
    r = ns["atender"]("pon el volumen al 30", h)
    t = ns["traza"]
    ok("agente: volumen sin modelo, por el mismo ejecutor y con respuesta verificada",
       r == "Listo, puse el volumen al 30%." and t["modelo"] == 0 and t["decision_modo"] == 1
       and t["implementaciones"] == [("volumen", {"accion": "fijar", "cantidad": 30})], (r, t))
    ok("agente: el historial queda coherente (acción, resultado y finalizar)",
       [m["role"] for m in h] == ["system", "user", "assistant", "user", "assistant"]
       and json.loads(h[-1]["content"])["herramienta"] == "finalizar", [m["role"] for m in h])
    # no verificado (la app no se abrió): sigue el modelo con lo ocurrido en el historial
    ns = cargar(fuente, {"abrir_app": {"ok": False, "error": "No encontré esa app"}},
                modelo=[{"pensamiento": "p", "herramienta": "finalizar", "argumentos": {"mensaje": "No pude.", "exito": False}}])
    r = ns["atender"]("abre spotify", [{"role": "system", "content": "s"}])
    ok("agente: sin verificar, la tarea pasa al modelo", r == "No pude." and ns["traza"]["modelo"] == 1, (r, ns["traza"]))
    # rechazo y bloqueo terminan como hoy, sin el modelo
    ns = cargar(fuente, {"abrir_app": {"ok": False, "rechazado": True, "error": "no"}})
    r = ns["atender"]("abre spotify", [{"role": "system", "content": "s"}])
    ok("agente: un «no» termina la tarea", r == "No lo hice porque no lo autorizaste." and ns["traza"]["modelo"] == 0, r)
    ns = cargar(fuente, {"abrir_app": {"ok": False, "bloqueado": True, "error": "Bloqueada."}})
    r = ns["atender"]("abre spotify", [{"role": "system", "content": "s"}])
    ok("agente: un bloqueo termina la tarea", r == "No lo hice: Bloqueada." and ns["traza"]["modelo"] == 0, r)
    # atajo de emergencia: antes de empezar y durante el paso
    ns = cargar(fuente, VOLUMEN_OK, detenido=True)
    r = ns["atender"]("pon el volumen al 30", [{"role": "system", "content": "s"}])
    ok("agente: detenido, no ejecuta nada", not ns["traza"]["implementaciones"] and r == ns["MENSAJE_DETENIDO"], r)
    ns = cargar(fuente, VOLUMEN_OK, pulsa_atajo=True)
    r = ns["atender"]("pon el volumen al 30", [{"role": "system", "content": "s"}])
    ok("agente: atajo de emergencia durante el camino rápido, no ejecuta", not ns["traza"]["implementaciones"], r)
    # interruptor apagado: todo al modelo
    ns = cargar(fuente, VOLUMEN_OK, modelo=[{"pensamiento": "p", "herramienta": "finalizar",
                                             "argumentos": {"mensaje": "modelo", "exito": True}}])
    ns["CAMINO_RAPIDO"] = False
    r = ns["atender"]("pon el volumen al 30", [{"role": "system", "content": "s"}])
    ok("agente: con camino_rapido apagado decide el modelo", r == "modelo" and ns["traza"]["modelo"] == 1, r)
    # pedido que no entra: decide el modelo
    ns = cargar(fuente, VOLUMEN_OK, modelo=[{"pensamiento": "p", "herramienta": "finalizar",
                                             "argumentos": {"mensaje": "modelo", "exito": True}}])
    r = ns["atender"]("sube el volumen y abre spotify", [{"role": "system", "content": "s"}])
    ok("agente: un compuesto va al modelo", r == "modelo" and not ns["traza"]["implementaciones"], r)
    return len(fallos) - antes


def pruebas_modo_juego(fuente=FUENTE):
    antes = len(fallos)
    ns = cargar(fuente, VOLUMEN_OK, en_pausa=True)
    r = ns["atender_con_memoria"]("pon el volumen al 30", [{"role": "system", "content": "s"}], ns["Planificador"]()
                                  if "Planificador" in ns else None)
    t = ns["traza"]
    ok("pausa: el volumen se ejecuta sin modelo y sin reservarlo", r == "Listo, puse el volumen al 30%."
       and t["modelo"] == 0 and t["carga_modelo"] == 0 and t["decision_modo"] == 1, (r, t))
    for frase in ("abre spotify", "deja de registrar lo que hago", "qué hora es"):
        ns = cargar(fuente, VOLUMEN_OK, en_pausa=True)
        r = ns["atender_con_memoria"](frase, [{"role": "system", "content": "s"}], None)
        ok(f"pausa: «{frase}» sigue en pausa", r == "PAUSA" and not ns["traza"]["implementaciones"]
           and ns["traza"]["modelo"] == 0, r)
    ns = cargar(fuente, {"volumen": {"ok": False, "error": "sin audio"}}, en_pausa=True)
    r = ns["atender_con_memoria"]("pon el volumen al 30", [{"role": "system", "content": "s"}], None)
    ok("pausa: si el volumen falla, no se llama al modelo", ns["traza"]["modelo"] == 0
       and r == "No pude hacerlo durante la pausa del modo juego.", r)
    # el camino rápido no toca la GPU ni el detector de juego
    fuente_cr = (BASE / "camino_rapido.py").read_text(encoding="utf-8")
    ok("camino_rapido.py no importa modelo, guardia_juego ni nada de la GPU",
       not re.search(r"^\s*(?:import|from)\s+(?:modelo|guardia_juego|llama_cpp|transcripcion|vision)\b", fuente_cr, re.M))
    guardia = (BASE / "guardia_juego.py").read_text(encoding="utf-8")
    ok("guardia_juego no menciona el camino rápido (no se relaja)", "camino" not in guardia.lower())
    voz = (BASE / "voz.py").read_text(encoding="utf-8")
    ok("voz: en pausa solo deja pasar el volumen del camino rápido",
       'a.camino_rapido.reconocer(texto, solo={"volumen"})' in voz)
    return len(fallos) - antes


def mutaciones():
    """Cada mutación quita un freno; alguna prueba tiene que fallar."""
    global fallos, silencio
    silencio = True
    resultados = {}
    guardados = (cr._NO_EN_NOMBRE, cr._COMPILADOS, cr.numero)

    def probar(nombre, preparar, prueba, fuente=FUENTE):
        global fallos
        reales = list(fallos)
        try:
            preparar()
            detectada = prueba(fuente) > 0 if fuente is not FUENTE or prueba is not pruebas_reconocedor else prueba() > 0
        finally:
            cr._NO_EN_NOMBRE, cr._COMPILADOS, cr.numero = guardados
            fallos = reales
        resultados[nombre] = detectada

    def busqueda():
        cr._COMPILADOS = [(type("P", (), {"fullmatch": p.search})(), h, a) for p, h, a in guardados[1]]

    def sin_rango():
        real = guardados[2]
        cr.numero = lambda t: (int(t) if t.lstrip("-").isdigit() else real(t))

    probar("sin la lista de palabras prohibidas en el nombre", lambda: setattr(cr, "_NO_EN_NOMBRE", set()),
           lambda *_: pruebas_reconocedor())
    probar("search en vez de frase entera", busqueda, lambda *_: pruebas_reconocedor())
    probar("sin comprobar el rango del número", sin_rango, lambda *_: pruebas_reconocedor())
    mutadas = {
        "sin emergencia.comprobar() en paso_rapido": FUENTE.replace(
            '    emergencia.comprobar()\n    resultado = ejecutar(nombre, args)\n    _tarea["herramientas"].append((nombre, args))\n    historial.append({"role": "user", "content": f"Resultado de {nombre}',
            '    resultado = ejecutar(nombre, args)\n    _tarea["herramientas"].append((nombre, args))\n    historial.append({"role": "user", "content": f"Resultado de {nombre}'),
        "paso_rapido sin ejecutar() (directo a la implementación)": FUENTE.replace(
            "    resultado = ejecutar(nombre, args)\n    _tarea[\"herramientas\"].append((nombre, args))\n    historial.append({\"role\": \"user\", \"content\": f\"Resultado de {nombre}",
            "    resultado = IMPLEMENTACIONES[nombre](**args)\n    _tarea[\"herramientas\"].append((nombre, args))\n    historial.append({\"role\": \"user\", \"content\": f\"Resultado de {nombre}"),
        "sin verificar el resultado antes de responder": FUENTE.replace(
            "    if resultado_verificado(nombre, args, resultado):\n        return terminar(historial, camino_rapido.respuesta(",
            "    if True:\n        return terminar(historial, camino_rapido.respuesta("),
        "pausa sin limitar al volumen": FUENTE.replace(
            'if CAMINO_RAPIDO and camino_rapido.reconocer(pedido, solo={"volumen"}):',
            "if CAMINO_RAPIDO and camino_rapido.reconocer(pedido, resolver_app_rapido):"),
        "pausa que cae al modelo si el volumen falla": FUENTE.replace(
            '        if en_pausa:  # sin modelo: lo que no resolvió el camino rápido no se hace\n', '        if False:\n'),
    }
    for nombre, fuente in mutadas.items():
        if fuente == FUENTE:
            resultados[nombre] = "la mutación no se aplicó (el código cambió)"
            continue
        reales = list(fallos)
        try:
            detectada = (pruebas_agente(fuente) + pruebas_modo_juego(fuente)) > 0
        except Exception:  # una mutación que rompe el flujo también se detecta
            detectada = True
        fallos = reales
        resultados[nombre] = detectada
    silencio = False
    for nombre, detectada in resultados.items():
        ok(f"mutación detectada: {nombre}", detectada is True, detectada)


if __name__ == "__main__":
    pruebas_reconocedor()
    ok("números en palabras", [cr.numero(x) for x in ("cuarenta y cinco", "veinticinco", "cien", "cero", "treinta")]
       == [45, 25, 100, 0, 30])
    ok("números fuera de rango o raros", all(cr.numero(x) is None for x in ("150", "mil", "cuarenta y doce", "treinta y cero")))
    pruebas_agente()
    pruebas_modo_juego()
    mutaciones()
    print(f"{len(ejecutadas) - len(fallos)}/{len(ejecutadas)} OK")
    sys.exit(1 if fallos else 0)
