"""
Pruebas sin modelo ni micrófono de la escucha de seguimiento (seguimiento.py) y de su uso en voz.py:
  1. Seguimiento con audio sintético y un reloj falso: nadie habla (termina a los 8 s), la cola de la voz de Cacao
     (primeros 0,4 s), un clic suelto, voz que empieza y termina en un silencio (con medio segundo de antes), bloques
     de 416 muestras como los del G435, otra app sonando al abrir, antes de hablar o mientras se graba, y cerrar;
  2. voz.py (funciones extraídas con ast; importar voz cargaría Gemma y Whisper): DespuesDeResponder avisa a la isla
     con fin_habla al terminar de hablar y abre la escucha solo con los modos «seguimiento» y «escucha» activos, sin
     modo juego ni emergencia; lo dicho llega como pedido normal por los mismos frenos; Ctrl+Espacio la cierra;
  3. el agente marca en la respuesta a la isla si se va a leer en voz alta.
Uso: .venv\\Scripts\\python probar_seguimiento.py
"""
import ast
import queue
import sys
import threading
import time
import types
from pathlib import Path

import numpy as np

import palabra_activacion as pa
import seguimiento as sg
from microfono import UMBRAL_VOZ

BASE = Path(__file__).parent
resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


def silencio(s):
    return (np.random.default_rng(1).normal(0, 60, int(s * pa.TASA))).astype(np.int16)


def voz(s, f=180):
    return (6000 * np.sin(np.arange(int(s * pa.TASA)) / pa.TASA * 2 * np.pi * f)).astype(np.int16)


class Reloj:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def alimentar(s, reloj, audio, bloque=416):
    """Pasa el audio en bloques como el micrófono, avanzando el reloj al ritmo del audio."""
    for i in range(0, len(audio), bloque):
        trozo = audio[i:i + bloque]
        reloj.t += len(trozo) / pa.TASA
        s.procesar(trozo)


def nuevo(mirar=None, reloj=None):
    empezadas = []
    s = sg.Seguimiento(pa.TASA, UMBRAL_VOZ, mirar_audio=mirar, al_empezar=lambda: empezadas.append(1),
                       reloj=reloj or Reloj(), hilo=False)
    return s, empezadas


def pruebas_seguimiento():
    reloj = Reloj()
    s, empezadas = nuevo(reloj=reloj)
    ok("se abre sin otra app sonando", s.abrir(8) and s.abierta)
    alimentar(s, reloj, silencio(8.5))
    ok("nadie habla: termina a los 8 s (más 0,4 de margen)", not s.abierta and s.cola.get_nowait() == ("fin", "tiempo"))

    reloj = Reloj()
    s, empezadas = nuevo(reloj=reloj)
    s.abrir(8)
    alimentar(s, reloj, voz(0.3))  # la cola de la voz de Cacao en los altavoces
    alimentar(s, reloj, silencio(0.5))
    ok("los primeros 0,4 s (cola de la voz de Cacao) no cuentan", s.abierta and s.cola.empty() and not empezadas)
    alimentar(s, reloj, np.concatenate([voz(0.06), silencio(0.5)]))
    ok("un clic o una tecla (60 ms) no abren la grabación", s.abierta and s.cola.empty() and not empezadas)
    alimentar(s, reloj, np.concatenate([silencio(0.6), voz(1.5), silencio(1.2)]))
    time.sleep(0.05)  # al_empezar va en un hilo
    llegado = s.cola.get_nowait() if not s.cola.empty() else None
    ok("habla: graba hasta el silencio y lo entrega", llegado and llegado[0] == "seguimiento" and not llegado[2]
       and not s.abierta, llegado and (llegado[0], len(llegado[1]) / pa.TASA))
    ok("la grabación trae medio segundo de antes y la voz entera", llegado and 1.9 <= len(llegado[1]) / pa.TASA <= 3.0,
       llegado and round(len(llegado[1]) / pa.TASA, 2))
    ok("al empezar a hablar avisa (la isla pasa a «Te escucho»)", empezadas == [1])
    alimentar(s, reloj, voz(1.0))
    ok("cerrada, ya no graba nada más", s.cola.empty())

    for bloque in (160, 1000):
        reloj = Reloj()
        s, _ = nuevo(reloj=reloj)
        s.abrir(8)
        a = np.concatenate([silencio(1.0), voz(1.0), silencio(1.2)])
        alimentar(s, reloj, a, bloque=bloque)
        ok(f"bloques de {bloque} muestras: termina igual", not s.cola.empty() and s.cola.get_nowait()[0] == "seguimiento")

    sonando = {"si": True}
    s, _ = nuevo(mirar=lambda: sonando["si"])
    ok("otra app sonando al terminar de hablar: no se abre", not s.abrir(8) and not s.abierta)

    reloj = Reloj()
    sonando["si"] = False
    s, _ = nuevo(mirar=lambda: sonando["si"], reloj=reloj)
    s.abrir(8)
    alimentar(s, reloj, silencio(1.0))
    sonando["si"] = True
    time.sleep(0.4)  # el vigía mira cada 0,15 s
    alimentar(s, reloj, silencio(0.1))
    ok("otra app empieza a sonar antes de que hables: se cierra", not s.abierta
       and s.cola.get_nowait() == ("fin", "otro_audio"))

    reloj = Reloj()
    sonando["si"] = False
    s, _ = nuevo(mirar=lambda: sonando["si"], reloj=reloj)
    s.abrir(8)
    alimentar(s, reloj, np.concatenate([silencio(0.6), voz(0.5)]))
    sonando["si"] = True
    time.sleep(0.4)
    alimentar(s, reloj, np.concatenate([voz(0.5), silencio(1.2)]))
    llegado = s.cola.get_nowait() if not s.cola.empty() else None
    ok("otra app suena mientras grabas: la grabación llega marcada", llegado and llegado[0] == "seguimiento"
       and llegado[2] is True)

    reloj = Reloj()
    s, _ = nuevo(reloj=reloj)
    s.abrir(8)
    alimentar(s, reloj, np.concatenate([silencio(0.6), voz(0.5)]))
    s.cerrar()
    alimentar(s, reloj, np.concatenate([voz(0.5), silencio(1.2)]))
    ok("cerrar (Ctrl+Espacio, un pedido escrito): no entrega nada", not s.abierta and s.cola.empty())
    s.recibir(voz(0.1).reshape(-1, 1))
    ok("cerrada, el micrófono no le pasa audio", s._entrada.empty())


# ---------- voz.py sin modelo ----------

def cargar_voz(transcripcion, modos, en_pausa=False, detenido=False):
    import pedidos
    import transcripcion as tr
    from microfono import analizar_audio
    arbol = ast.parse((BASE / "voz.py").read_text(encoding="utf-8"))
    nombres = {"escuchar", "filtrar", "esperar_disparo", "a_la_isla", "DespuesDeResponder"}
    nodos = [n for n in arbol.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in nombres]
    a_isla, notificaciones, contados = [], [], []

    class Isla:
        def enviar(self, m):
            a_isla.append(m)

    agente = types.SimpleNamespace(
        _modos=dict(modos), _isla=Isla(), notificar=lambda e, d="": notificaciones.append(e),
        _modo_juego=types.SimpleNamespace(en_pausa=lambda: "Roblox" if en_pausa else None),
        emergencia=types.SimpleNamespace(detenido=lambda: detenido), cola_pedidos=pedidos.ColaPedidos(),
        normalizar=lambda t: t.lower(), FRASES_TERMINE=[], FRASES_JUGANDO=[])

    class Transcriptor:
        def transcribir(self, _wav):
            return transcripcion

    class Locutor:
        def __init__(self):
            self.habla = True

        def hablando(self):
            return self.habla

    class Oido:
        segundos = 8

        def __init__(self):
            self.cola, self.abierta, self.aperturas, self.cierres = queue.Queue(), False, [], 0
            self.permitir = True

        def abrir(self, segundos):
            self.aperturas.append(segundos)
            self.abierta = self.permitir
            return self.permitir

        def cerrar(self, motivo=None):
            self.abierta = False
            self.cierres += 1

    pa_falso = types.SimpleNamespace(empieza_con_la_palabra=pa.empieza_con_la_palabra,
                                     quitar_palabra=pa.quitar_palabra, contar=lambda e: contados.append(e))
    locutor, oido = Locutor(), Oido()
    ns = {"a": agente, "time": time, "queue": queue, "np": np, "analizar_audio": analizar_audio, "a_wav": tr.a_wav,
          "transcripcion_plausible": tr.transcripcion_plausible, "contar_palabras": tr.contar_palabras,
          "CONFIG_VOZ": {"min_voz_s": 0.15, "max_grabacion_s": 30}, "palabra_activacion": pa_falso,
          "print": lambda *x, **k: None}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "voz.py", "exec"), ns)
    despues = ns["DespuesDeResponder"](locutor, oido)
    ns["_piezas"] = {"escucha": types.SimpleNamespace(cola=queue.Queue()), "seguimiento": oido, "despues": despues}
    return types.SimpleNamespace(ns=ns, isla=a_isla, notif=notificaciones, contados=contados, locutor=locutor,
                                 oido=oido, despues=despues, transcriptor=Transcriptor())


class Atajo:
    def __init__(self):
        self.pulsado = threading.Event()


def pruebas_voz():
    activos = {"seguimiento": True, "escucha": True}
    v = cargar_voz("Y ahora bájalo un poco.", activos)
    v.despues.empezar()
    v.despues.revisar()
    ok("mientras Cacao habla: ni fin_habla ni escucha", not v.isla and not v.oido.aperturas)
    v.locutor.habla = False
    v.despues.revisar()
    ok("termina de hablar: fin_habla a la isla", {"tipo": "fin_habla"} in v.isla)
    ok("y abre la escucha de 8 s con el indicador", v.oido.aperturas == [8]
       and {"tipo": "seguimiento", "activo": True, "segundos": 8} in v.isla)
    v.oido.cola.put(("seguimiento", np.concatenate([silencio(0.3), voz(1.2), silencio(0.5)]), False))
    _, datos, texto, _ = v.ns["escuchar"](Atajo(), None, v.transcriptor)
    ok("lo dicho llega como pedido normal (sin «Cacao»)", texto == "Y ahora bájalo un poco."
       and datos.get("disparo") == "seguimiento" and v.contados == ["seguimiento"], (texto, datos.get("freno")))

    v = cargar_voz("Cacao, abre la calculadora.", activos)
    v.oido.cola.put(("seguimiento", np.concatenate([voz(1.5), silencio(0.5)]), False))
    _, _, texto, _ = v.ns["escuchar"](Atajo(), None, v.transcriptor)
    ok("si dices «Cacao, …» igual vale (se quita la palabra)", texto == "abre la calculadora.", texto)

    v = cargar_voz("Gracias por ver el video.", activos)
    v.oido.cola.put(("seguimiento", np.concatenate([voz(0.2), silencio(1.0)]), False))
    _, datos, texto, _ = v.ns["escuchar"](Atajo(), None, v.transcriptor)
    ok("mismos frenos: una frase que Whisper inventa se descarta", texto is None and datos.get("freno"),
       datos.get("freno"))
    v = cargar_voz("", activos)
    v.oido.cola.put(("seguimiento", silencio(1.0), False))
    _, datos, texto, _ = v.ns["escuchar"](Atajo(), None, v.transcriptor)
    ok("mismos frenos: casi sin voz no se transcribe", texto is None and datos.get("freno") == "silencio",
       datos.get("freno"))
    ok("descartado: la isla vuelve a reposo y no cuenta como pedido", "reposo" in v.notif and not v.contados)
    v = cargar_voz("Sube el volumen.", activos)
    v.oido.cola.put(("seguimiento", np.concatenate([voz(1.2), silencio(0.5)]), True))
    _, datos, texto, _ = v.ns["escuchar"](Atajo(), None, v.transcriptor)
    ok("con otra app sonando mientras hablabas, no vale", texto is None and datos.get("freno") == "otro_audio")

    for cambio, nombre in (({"seguimiento": False}, "modo «seguimiento» apagado"),
                           ({"escucha": False}, "escucha de «Cacao» apagada")):
        v = cargar_voz("x", {**activos, **cambio})
        v.locutor.habla = False
        v.despues.empezar()
        v.despues.revisar()
        ok(f"{nombre}: fin_habla sí, escucha no", {"tipo": "fin_habla"} in v.isla and not v.oido.aperturas)
    for kw, nombre in (({"en_pausa": True}, "modo juego"), ({"detenido": True}, "detenido por la emergencia")):
        v = cargar_voz("x", activos, **kw)
        v.locutor.habla = False
        v.despues.empezar()
        v.despues.revisar()
        ok(f"{nombre}: sin escucha de seguimiento", not v.oido.aperturas)
    v = cargar_voz("x", activos)
    v.oido.permitir = False  # otra app sonando
    v.locutor.habla = False
    v.despues.empezar()
    v.despues.revisar()
    ok("otra app sonando: no se abre ni sale el indicador", v.oido.aperturas == [8]
       and not any(m.get("tipo") == "seguimiento" for m in v.isla))

    v = cargar_voz("Pon música.", activos)
    v.locutor.habla = False
    v.despues.empezar()
    v.despues.revisar()
    v.oido.cerrar()  # venció sin que nadie hablara
    v.despues.revisar()
    ok("al terminar sin que hables, el indicador se apaga", v.isla[-1] == {"tipo": "seguimiento", "activo": False})

    # Ctrl+Espacio durante la escucha: la cierra y graba como siempre
    v = cargar_voz("Sube el volumen.", activos)
    v.locutor.habla = False
    v.despues.empezar()
    v.despues.revisar()

    class Mic:
        def grabar_hasta(self, sigue):
            return np.concatenate([voz(1.2), silencio(0.3)]), 1.5, time.perf_counter()

    atajo = Atajo()
    atajo.pulsado.set()
    atajo.sigue_pulsado = lambda: False
    _, datos, texto, _ = v.ns["escuchar"](atajo, Mic(), v.transcriptor)
    ok("Ctrl+Espacio durante la escucha: la cierra y graba como siempre", v.oido.cierres == 1
       and texto == "Sube el volumen." and v.isla[-1] == {"tipo": "seguimiento", "activo": False})
    v = cargar_voz("x", activos)
    v.despues.empezar()  # aún hablando
    atajo = Atajo()
    atajo.pulsado.set()
    atajo.sigue_pulsado = lambda: False
    v.ns["escuchar"](atajo, Mic(), v.transcriptor)
    ok("Ctrl+Espacio mientras habla: fin_habla para que la isla no se quede esperando",
       v.isla == [{"tipo": "fin_habla"}] and not v.oido.aperturas)


def pruebas_agente():
    fuente = (BASE / "agente_minimo.py").read_text(encoding="utf-8")
    ok("la respuesta a la isla dice si se lee en voz alta", '"habla": bool(voz)' in fuente)
    fuente_voz = (BASE / "voz.py").read_text(encoding="utf-8")
    ok("la palabra «Cacao» se ignora mientras la escucha de seguimiento está abierta",
       '_piezas["seguimiento"].abierta' in fuente_voz.split("def crear_escucha", 1)[1].split("def crear_seguimiento", 1)[0])
    ok("lo oído en la escucha de seguimiento que no es pedido no se guarda",
       'datos.get("disparo") != "seguimiento"' in fuente_voz)


if __name__ == "__main__":
    for parte in (pruebas_seguimiento, pruebas_voz, pruebas_agente):
        print(f"\n== {parte.__name__} ==")
        parte()
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
