"""
Pruebas sin GPU ni altavoz de tts_qwen.py (Qwen3-TTS con Piper de respaldo) y de su uso en voz.py.

El servidor es un proceso FALSO (este mismo archivo con --falso <modo>) que habla el mismo protocolo por tubería que
tts_qwen_motor/servidor.cpp. Piper y la salida de audio también son falsos.
  1. texto: números y símbolos a palabras; trozos (oraciones; la primera, si es larga, por comas);
  2. interfaz: la misma que voz.Locutor (hablar, callar, hablando, salida, voz, tasa); crear_locutor según
     voz.tts_motor (Piper por defecto);
  3. respaldo a Piper: caída, cuelgue, lentitud, error, no arranca, a mitad de respuesta, límite de rearranques,
     hash malo o archivo que falta, VRAM corta, perfil sin medir (Gemma), juego abierto;
  4. modo juego: descargar (la pausa habla con Piper) y cargar (vuelve tras comprobarlo todo); callar y cortar;
  5. voz.py: interruptor por defecto, orden de carga (tras el LLM y Whisper), modo juego y cierre;
  6. mutaciones: quitar cada freno hace fallar alguna prueba.
Uso: .venv\\Scripts\\python probar_tts_qwen.py
"""
import ast
import hashlib
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

BASE = Path(__file__).parent
TASA = 24000


# ---------- servidor falso (proceso hijo) ----------

def servidor_falso(modo):
    """Protocolo de servidor.cpp. Modos: normal, no_arranca, cae_en:N, cuelga_en:N, lento, error_en:N."""
    import numpy as np
    salida = sys.stdout.buffer
    if modo == "no_arranca":
        return
    salida.write(f"LISTO {TASA}\n".encode())
    salida.flush()
    nombre, _, n = modo.partition(":")
    n = int(n or 0)
    pedidos = 0
    for linea in sys.stdin.buffer:
        linea = linea.decode("utf-8").rstrip("\n")
        if linea == "SALIR":
            return
        ident, _, texto = linea.partition("\t")
        pedidos += 1
        if nombre == "cae_en" and pedidos >= n:
            return
        if nombre == "cuelga_en" and pedidos >= n:
            time.sleep(3600)
        if nombre == "error_en" and pedidos >= n:
            salida.write(f"E {ident} step_gen\n".encode())
            salida.flush()
            continue
        time.sleep(1.5 if nombre == "lento" else 0.01)
        audio = (np.ones(int(TASA * 0.002 * len(texto)), dtype=np.int16) * (len(texto) % 100))
        salida.write(f"A {ident} {len(audio)} {TASA}\n".encode())
        salida.write(audio.tobytes())
        salida.flush()


if __name__ == "__main__" and "--falso" in sys.argv:
    servidor_falso(sys.argv[sys.argv.index("--falso") + 1])
    sys.exit(0)


# ---------- pruebas ----------

import tts_qwen as tq  # noqa: E402

NORMALIZAR = tq.normalizar_texto  # el real, para calcular lo esperado aunque una mutación lo cambie

resultados, silencio = [], False


def ok(nombre, condicion, detalle=""):
    """Durante las mutaciones (silencio) no cuenta ni imprime: solo devuelve el resultado."""
    if not silencio:
        resultados.append((nombre, bool(condicion)))
        print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)
    return bool(condicion)


class PiperFalso:
    def __init__(self):
        self.dicho, self.tasa, self.voz = [], 22050, object()
        self.salida = type("S", (), {"latency": 0.05})()
        import threading as th
        self._callar, self._hilo = th.Event(), None

    def hablar(self, texto, al_empezar=None, cortar=lambda: False):
        self.callar()
        self._callar.clear()
        self._hilo = threading.Thread(target=self._decir, args=(texto, al_empezar, cortar), daemon=True)
        self._hilo.start()

    def _decir(self, texto, al_empezar, cortar):
        if al_empezar:
            al_empezar(time.perf_counter())
        self.dicho.append(texto)
        time.sleep(0.02)

    def callar(self):
        self._callar.set()
        if self._hilo is not None:
            self._hilo.join(2)

    def hablando(self):
        return self._hilo is not None and self._hilo.is_alive()


class SalidaFalsa:
    def __init__(self, tasa):
        self.tasa, self.escrito, self.latency = tasa, [], 0.03

    def write(self, datos):
        self.escrito.append(len(datos))
        time.sleep(len(datos) / self.tasa / 20)  # 20 veces más rápido que el tiempo real


class Motor:
    """Carpeta con archivos de mentira y su manifiesto de hashes."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="cacao_tts_prueba_"))
        archivos = {}
        for rel in ("bin/tts_qwen_servidor.exe", tq.MODELO, tq.MMPROJ, tq.VOZ):
            p = self.dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(rel.encode() * 10)
            archivos[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        self.manifiesto = self.dir / "hashes.json"
        self.manifiesto.write_text(json.dumps({"archivos": archivos}), encoding="utf-8")


def locutor(modo="normal", perfil="qwen9b", libre=8000, juego=None, motor=None, modos=None):
    """LocutorQwen con el servidor falso. modos: lista de modos para arranques sucesivos."""
    motor = motor or Motor()
    secuencia = list(modos or [modo])
    creados = []

    def crear():
        m = secuencia.pop(0) if len(secuencia) > 1 else secuencia[0]
        p = tq.ProcesoTTS([sys.executable, str(Path(__file__).resolve()), "--falso", m], espera_arranque=10)
        creados.append(p)
        return p

    piper = PiperFalso()
    loc = tq.LocutorQwen(piper, perfil, carpeta=motor.dir, manifiesto=motor.manifiesto, crear_salida=SalidaFalsa,
                         crear_proceso=crear, libre=lambda: libre, juego=lambda: juego, avisar=lambda *_: None)
    loc.creados = creados
    return loc, piper


def esperar(cond, s=10):
    limite = time.monotonic() + s
    while time.monotonic() < limite:
        if cond():
            return True
        time.sleep(0.02)
    return False


def decir(loc, texto, cortar=lambda: False):
    inicio = {}
    loc.hablar(texto, al_empezar=lambda t: inicio.setdefault("t", t), cortar=cortar)
    esperar(lambda: not loc.hablando())
    return inicio


def pruebas_texto():
    casos = {
        "El volumen está al 45%.": "El volumen está al cuarenta y cinco por ciento.",
        "Son las 10:30.": "Son las diez treinta.",
        "Son las 9:00.": "Son las nueve en punto.",
        "Hay 1.234.567 archivos.": "Hay un millón doscientos treinta y cuatro mil quinientos sesenta y siete archivos.",
        "Ocupa 3,5 GB y 2.75 MB.": "Ocupa tres coma cinco GB y dos coma setenta y cinco MB.",
        "Tengo 21000 y 101.": "Tengo veintiún mil y ciento uno.",
        "Cuesta $20 o 15€.": "Cuesta veinte dólares o quince euros.",
        "Hace 21°C.": "Hace veintiuno grados.",
        "Versión 2.0.1": "Versión dos punto cero punto uno",
        "A & B + C": "A y B más C",
        "Hola, Cacao.": "Hola, Cacao.",
    }
    n = 0
    for entrada, esperado in casos.items():
        n += not ok(f"texto: {entrada}", tq.normalizar_texto(entrada) == esperado, tq.normalizar_texto(entrada))
    n += not ok("número 1 000 000", tq.numero_a_palabras(1_000_000) == "un millón")
    n += not ok("número 2 500 000", tq.numero_a_palabras(2_500_000) == "dos millones quinientos mil")
    n += not ok("número 100 y 115", (tq.numero_a_palabras(100), tq.numero_a_palabras(115)) == ("cien", "ciento quince"))
    trozos = {
        "Hecho.": ["Hecho."],
        "Buenos días. Hoy es lunes.": ["Buenos días.", "Hoy es lunes."],
        "Tienes tres ventanas abiertas: el navegador, el bloc de notas y la terminal.":
            ["Tienes tres ventanas abiertas: el navegador,", "el bloc de notas y la terminal."],
        "En la carpeta de descargas hay doce archivos; el más reciente es un documento PDF de esta mañana.":
            ["En la carpeta de descargas hay doce archivos;", "el más reciente es un documento PDF de esta mañana."],
        "Listo, abrí Spotify.": ["Listo, abrí Spotify."],  # corta: no se parte
        "No encontré esa aplicación, lo siento mucho de verdad. ¿Quieres otra, parecida o distinta?":
            ["No encontré esa aplicación, lo siento mucho de verdad.", "¿Quieres otra, parecida o distinta?"],
        "": [],
    }
    for entrada, esperado in trozos.items():
        n += not ok(f"trozos: {entrada[:40]!r}", tq.partir(entrada) == esperado, tq.partir(entrada))
    larga = "uno, dos, tres, cuatro, cinco, seis, siete, ocho, nueve, diez, once, doce, trece, catorce."
    n += not ok("trozos: sin trozos de menos de 20 caracteres", all(len(t) >= tq.TROZO_MIN for t in tq.partir(larga)),
                tq.partir(larga))
    n += not ok("trozos: no pierden texto", " ".join(tq.partir(larga)) == larga)
    return n


def pruebas_interfaz():
    n = 0
    arbol = ast.parse((BASE / "voz.py").read_text(encoding="utf-8"))
    clase = next(c for c in arbol.body if isinstance(c, ast.ClassDef) and c.name == "Locutor")
    metodos = {f.name: [a.arg for a in f.args.args] for f in clase.body if isinstance(f, ast.FunctionDef)}
    for nombre in ("hablar", "callar", "hablando"):
        firma = [a for a in getattr(tq.LocutorQwen, nombre).__code__.co_varnames[
            :getattr(tq.LocutorQwen, nombre).__code__.co_argcount]]
        n += not ok(f"interfaz: {nombre}{tuple(metodos[nombre][1:])}", firma == metodos[nombre], firma)
    loc, piper = locutor()
    n += not ok("interfaz: voz (calentamiento de Piper), tasa y salida", loc.voz is piper.voz and loc.tasa
                and loc.salida is piper.salida)
    n += not ok("crear_locutor: Piper por defecto", tq.crear_locutor(piper, {}, {"modelo_activo": "qwen9b"}) is piper)
    n += not ok("crear_locutor: 'piper' explícito", tq.crear_locutor(piper, {"tts_motor": "piper"}, {}) is piper)
    q = tq.crear_locutor(piper, {"tts_motor": "qwen3"}, {"modelo_activo": "qwen9b"})
    n += not ok("crear_locutor: 'qwen3' → LocutorQwen sin iniciar (habla Piper)",
                isinstance(q, tq.LocutorQwen) and q.estado == "piper" and q.perfil == "qwen9b")
    return n


def pruebas_normal():
    n = 0
    loc, piper = locutor()
    n += not ok("antes de cargar habla Piper", (decir(loc, "Hola."), piper.dicho == ["Hola."])[1])
    loc.iniciar()
    loc.esperar_carga(15)
    n += not ok("carga: hashes, guardia, perfil y VRAM → activo", loc.estado == "activo", loc.motivo)
    n += not ok("salida a la tasa del TTS", loc.salida.tasa == TASA and loc.tasa == TASA)
    inicio = {}
    loc.hablar("Buenos días. Son las 10:30.", al_empezar=lambda t: inicio.setdefault("t", t))
    n += not ok("hablando() mientras suena", loc.hablando())
    esperar(lambda: not loc.hablando())
    n += not ok("habla Qwen: audio escrito, Piper callado", sum(loc.salida.escrito) > 0 and piper.dicho == ["Hola."])
    n += not ok("al_empezar se llama una vez", "t" in inicio)
    n += not ok("ultimo_motor = qwen3", loc.ultimo_motor == "qwen3")
    esperado = sum(int(TASA * 0.002 * len(NORMALIZAR(t))) for t in tq.partir("Buenos días. Son las 10:30."))
    n += not ok("todos los trozos suenan, normalizados", sum(loc.salida.escrito) == esperado,
                f"{sum(loc.salida.escrito)} de {esperado}")
    n += not ok("hablando() falso al terminar", not loc.hablando())
    # callar a mitad
    loc.salida.escrito.clear()
    loc.hablar("Esta es una respuesta bastante larga. " * 6)
    time.sleep(0.05)
    t = time.perf_counter()
    loc.callar()
    n += not ok("callar corta enseguida", time.perf_counter() - t < 1.0 and not loc.hablando())
    largo = sum(int(TASA * 0.002 * len(tq.normalizar_texto(x))) for x in tq.partir("Esta es una respuesta bastante larga. " * 6))
    n += not ok("callar: no suena todo", sum(loc.salida.escrito) < largo)
    # cortar (atajo de emergencia)
    loc.salida.escrito.clear()
    cortado = {"si": False}
    threading.Timer(0.05, lambda: cortado.update(si=True)).start()
    decir(loc, "Otra respuesta muy larga para cortar. " * 6, cortar=lambda: cortado["si"])
    n += not ok("cortar() la para", sum(loc.salida.escrito) < largo)
    n += not ok("sin fallos anotados", not loc.eventos or all(e["evento"] == "activo" for e in loc.eventos))
    loc.cerrar()
    n += not ok("cerrar: el proceso termina", esperar(lambda: not loc.creados[0].vivo(), 5))
    return n


def respaldo(modo, texto="Primera oración. Segunda oración.", **kw):
    loc, piper = locutor(modo, **kw)
    loc.iniciar()
    loc.esperar_carga(15)
    activo = loc.estado == "activo"
    decir(loc, texto)
    return loc, piper, activo


def pruebas_respaldo():
    n = 0
    viejo = tq.tiempo_maximo
    tq.tiempo_maximo = lambda texto: 0.6
    try:
        loc, piper, activo = respaldo("cae_en:1")
        n += not ok("cae: lo dice Piper entero", activo and piper.dicho == ["Primera oración. Segunda oración."],
                    piper.dicho)
        n += not ok("cae: se anota el fallo", any(e["evento"] == "fallo" for e in loc.eventos))
        n += not ok("cae: rearranca solo", esperar(lambda: loc.estado == "activo") and loc.rearranques == 1)
        n += not ok("cae: ultimo_motor = piper", loc.ultimo_motor == "piper")
        loc.cerrar()

        loc, piper, activo = respaldo("cuelga_en:1")
        n += not ok("se cuelga: Piper tras el tiempo máximo", activo and piper.dicho, loc.eventos)
        n += not ok("se cuelga: el proceso se mata", not loc.creados[0].vivo())
        loc.cerrar()

        loc, piper, activo = respaldo("lento")
        n += not ok("va lento: Piper", activo and piper.dicho and "sin respuesta" in json.dumps(loc.eventos,
                                                                                               ensure_ascii=False))
        loc.cerrar()

        loc, piper, activo = respaldo("error_en:1")
        n += not ok("error del motor: Piper", activo and piper.dicho)
        loc.cerrar()

        loc, piper, activo = respaldo("cae_en:2")
        n += not ok("cae a mitad: el resto lo dice Piper", piper.dicho == ["Segunda oración."], piper.dicho)
        n += not ok("cae a mitad: la primera sonó con Qwen", sum(loc._salida.escrito) > 0)
        n += not ok("cae a mitad: ultimo_motor = qwen3+piper", loc.ultimo_motor == "qwen3+piper")
        loc.cerrar()

        loc, piper = locutor(modos=["cae_en:1"])
        loc.iniciar()
        loc.esperar_carga(15)
        for i in range(min(tq.MAX_REARRANQUES, 5) + 2):  # acotado: una mutación sin límite no cuelga la suite
            esperar(lambda: loc.estado in ("activo", "piper"))
            decir(loc, f"Frase {i}.")
        n += not ok("límite de rearranques: se queda en Piper", loc.estado == "piper"
                    and loc.rearranques == tq.MAX_REARRANQUES and "sin más rearranques" in loc.motivo, loc.motivo)
        n += not ok("límite de rearranques: no crea más procesos", len(loc.creados) == tq.MAX_REARRANQUES + 1,
                    len(loc.creados))
        n += not ok("límite de rearranques: todo se dijo", len(piper.dicho) == min(tq.MAX_REARRANQUES, 5) + 2, piper.dicho)
    finally:
        tq.tiempo_maximo = viejo

    loc, piper, activo = respaldo("no_arranca")
    n += not ok("no arranca: Piper", not activo and loc.estado == "piper" and piper.dicho)

    motor = Motor()
    (motor.dir / tq.MODELO).write_bytes(b"cambiado")
    loc, piper, activo = respaldo("normal", motor=motor)
    n += not ok("hash malo: Piper sin arrancar el proceso", not activo and "hash" in loc.motivo and not loc.creados,
                loc.motivo)
    motor = Motor()
    (motor.dir / tq.MMPROJ).unlink()
    loc, piper, activo = respaldo("normal", motor=motor)
    n += not ok("falta un archivo: Piper", not activo and "falta" in loc.motivo and not loc.creados, loc.motivo)

    loc, piper, activo = respaldo("normal", libre=tq.vram_necesaria("qwen9b") - 1)
    n += not ok("VRAM corta: Piper", not activo and "VRAM" in loc.motivo and not loc.creados, loc.motivo)
    loc, piper, activo = respaldo("normal", libre=tq.vram_necesaria("qwen9b"))
    n += not ok("VRAM justa: carga", activo)
    loc.cerrar()
    n += not ok("umbral medido: 3 330 + 1 255 + 500", tq.vram_necesaria("qwen9b") == 5085)

    loc, piper, activo = respaldo("normal", perfil="gemma", libre=16000)
    n += not ok("Gemma: Piper sin error", not activo and "gemma" in loc.motivo and not loc.creados and piper.dicho,
                loc.motivo)
    loc, piper, activo = respaldo("normal", juego="UnJuego")
    n += not ok("juego abierto: Piper, no se carga", not activo and "UnJuego" in loc.motivo and not loc.creados)
    return n


def pruebas_modo_juego():
    n = 0
    loc, piper = locutor()
    loc.iniciar()
    loc.esperar_carga(15)
    proceso = loc.proceso
    loc.descargar()
    n += not ok("descargar: proceso cerrado", not proceso.vivo() and loc.proceso is None)
    decir(loc, "Estoy en pausa.")
    n += not ok("en pausa habla Piper", piper.dicho == ["Estoy en pausa."] and loc.estado == "descargado")
    loc.cargar()
    loc.esperar_carga(15)
    n += not ok("cargar: vuelve tras comprobarlo", loc.estado == "activo" and len(loc.creados) == 2)
    loc.cerrar()
    loc, piper = locutor(juego="UnJuego")
    loc.cargar()
    loc.esperar_carga(15)
    n += not ok("cargar con un juego abierto: sigue Piper", loc.estado == "piper" and not loc.creados)
    # descargar mientras carga: el proceso que llega se cierra
    loc, piper = locutor()
    lento = loc._crear_proceso
    loc._crear_proceso = lambda: (time.sleep(0.3), lento())[1]
    loc.iniciar()
    time.sleep(0.05)
    loc.descargar()
    loc.esperar_carga(15)
    n += not ok("modo juego durante la carga: no queda proceso", loc.estado == "descargado"
                and esperar(lambda: all(not p.vivo() for p in loc.creados), 5))
    return n


def pruebas_voz():
    n = 0
    fuente = (BASE / "voz.py").read_text(encoding="utf-8")
    n += not ok("voz.py: tts_motor 'piper' por defecto", '"tts_motor": "piper"' in fuente)
    n += not ok("voz.py: crear_locutor sobre Piper", "locutor = tts_qwen.crear_locutor(locutor, CONFIG_VOZ, a.CONFIG)"
                in fuente)
    preparar = fuente[fuente.index("def preparar():"):fuente.index("class MedidorVRAM")]
    orden = [preparar.find(x) for x in ("a.cargar_modelo()", "transcriptor = crear_transcriptor()",
                                        "a.EXTRAS_MODO_JUEGO.append((transcriptor.descargar",
                                        "transcriptor.transcribir(a_wav", "locutor.iniciar()",
                                        "a.EXTRAS_MODO_JUEGO.append((locutor.descargar, locutor.cargar))")]
    n += not ok("voz.py: el TTS se carga tras el LLM, Whisper y el calentamiento; en el modo juego vuelve tras Whisper",
                -1 not in orden and orden == sorted(orden), orden)
    n += not ok("voz.py: cierra el TTS al salir", "locutor.cerrar()" in fuente[fuente.index("    finally:"):])
    n += not ok("voz.py: anota qué voz habló", '"voz": getattr(locutor, "ultimo_motor", "piper")' in fuente)
    n += not ok("tts_qwen: comando sin red ni puertos", "--offline" in tq.comando()
                and not any("port" in c or "host" in c for c in tq.comando()))
    servidor = (BASE / "tts_qwen_motor" / "servidor.cpp").read_text(encoding="utf-8")
    n += not ok("servidor.cpp: sin sockets", not any(x in servidor for x in ("socket", "httplib", "listen(", "curl")))
    hashes = json.loads((BASE / "tts_qwen_motor" / "hashes.json").read_text(encoding="utf-8"))
    n += not ok("hashes.json: el binario, los dos modelos y la voz",
                {"bin/tts_qwen_servidor.exe", tq.MODELO, tq.MMPROJ, tq.VOZ} <= set(hashes["archivos"])
                and hashes["llama_cpp"].startswith("81bc6b8"))
    return n


def mutaciones():
    global silencio
    silencio = True
    detectadas = {}
    guardados = {k: getattr(tq, k) for k in ("verificar_hashes", "vram_necesaria", "partir", "tiempo_maximo",
                                              "MAX_REARRANQUES", "normalizar_texto")}
    fallo_real = tq.LocutorQwen._fallo
    cargar_real = tq.LocutorQwen._cargar

    def probar(nombre, aplicar, prueba):
        try:
            aplicar()
            detectadas[nombre] = prueba() > 0
        except Exception:
            detectadas[nombre] = True
        finally:
            for k, v in guardados.items():
                setattr(tq, k, v)
            tq.LocutorQwen._fallo = fallo_real
            tq.LocutorQwen._cargar = cargar_real

    probar("sin comprobar hashes", lambda: setattr(tq, "verificar_hashes", lambda *a: None), pruebas_respaldo)
    probar("sin umbral de VRAM", lambda: setattr(tq, "vram_necesaria", lambda p: 0), pruebas_respaldo)
    probar("sin partir por comas", lambda: setattr(tq, "partir", lambda t: [o for o in __import__("re").split(
        r"(?<=[.!?])\s+", t.strip()) if o]), pruebas_texto)
    probar("sin tiempo máximo por trozo", lambda: setattr(tq, "tiempo_maximo", lambda t: 3600) or setattr(
        tq, "tiempo_maximo", lambda t: 3600), lambda: _con_limite(pruebas_cuelgue, 8))
    probar("sin límite de rearranques", lambda: setattr(tq, "MAX_REARRANQUES", 10**6), pruebas_respaldo)
    probar("sin normalizar números", lambda: setattr(tq, "normalizar_texto", lambda t: t), pruebas_normal)

    def sin_guardia():
        def cargar(self):
            self._juego = lambda: None
            return cargar_real(self)
        tq.LocutorQwen._cargar = cargar
    probar("sin guardia_juego", sin_guardia, pruebas_modo_juego)

    def sin_piper(self, motivo):
        fallo_real(self, motivo)
        self.piper._decir = lambda *a, **k: None
    probar("sin decirlo con Piper tras un fallo", lambda: setattr(tq.LocutorQwen, "_fallo", sin_piper),
           pruebas_respaldo)
    silencio = False
    for nombre, ok_ in detectadas.items():
        ok(f"mutación detectada: {nombre}", ok_ is True)


def pruebas_cuelgue():
    loc, piper, activo = respaldo("cuelga_en:1")
    n = 0 if (activo and piper.dicho) else 1
    loc.cerrar()
    return n


def _con_limite(prueba, segundos):
    """Una mutación que cuelga la prueba también cuenta como detectada."""
    r = {}
    h = threading.Thread(target=lambda: r.setdefault("n", prueba()), daemon=True)
    h.start()
    h.join(segundos)
    return r.get("n", 1)


if __name__ == "__main__":
    pruebas_texto()
    pruebas_interfaz()
    pruebas_normal()
    pruebas_respaldo()
    pruebas_modo_juego()
    pruebas_voz()
    mutaciones()
    fallos = [r for r in resultados if not r[1]]
    print(f"{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
