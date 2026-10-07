"""
Pruebas sin micrófono de la palabra de activación "Cacao" (palabra_activacion.py), con el modelo entrenado y audio
sintético de una voz que no se usó al entrenar (es_MX-claude-high, la voz de Cacao):
  1. "Cacao, sube el volumen" dicho de corrido: se detecta y la grabación conserva la orden (búfer previo);
  2. sin "Cacao" no se activa; con la escucha apagada tampoco; mientras Cacao habla (Piper) se ignora;
  3. graba hasta un silencio, o hasta 30 s si no para de hablar; si tras la palabra no dice nada, corta;
  4. la palabra sola nunca confirma; "Cacao, confirmo la instrucción" sí (pasa los frenos de la frase);
  5. quitar_palabra deja solo la orden.
Uso: .venv\\Scripts\\python probar_palabra_activacion.py
"""
import re
import sys
import threading
import time

import numpy as np
from piper import PiperVoice, SynthesisConfig

import confirmacion_voz as cv
import palabra_activacion as pa

# el contador diario de las pruebas va a un archivo temporal, no al real (contador_cacao.json)
import tempfile as _tempfile
from pathlib import Path as _Path
pa.RUTA_CONTADOR = _Path(_tempfile.mkdtemp()) / "contador_prueba.json"

resultados = []


def ok(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion), detalle))
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


VOZ = PiperVoice.load(str(pa.BASE / "modelos" / "piper" / "es_MX-claude-high.onnx"))
RNG = np.random.default_rng(3)


def decir(texto, largo=1.0):
    audio = np.concatenate([np.frombuffer(t.audio_int16_bytes, dtype=np.int16)
                            for t in VOZ.synthesize(texto, syn_config=SynthesisConfig(length_scale=largo))])
    return pa.a_16k(audio, VOZ.config.sample_rate)


def silencio(s):
    return RNG.normal(0, 20, int(s * pa.TASA)).astype(np.int16)


def pasar(escucha, audio, bloque=800, al_bloque=None):
    """Como el callback del micrófono: bloques de 50 ms. Espera a que el hilo procese todo."""
    for i in range(0, len(audio), bloque):
        if al_bloque:
            al_bloque(i / pa.TASA)
        escucha.recibir(audio[i:i + bloque].reshape(-1, 1))
        time.sleep(0.002)
    limite = time.monotonic() + 20
    while not escucha._entrada.empty() and time.monotonic() < limite:
        time.sleep(0.05)
    time.sleep(0.3)


def nueva(**k):
    return pa.Escucha(pa.TASA, activa=k.pop("activa", lambda: True), umbral_voz=400, anotar=lambda *_: None, **k)


def pruebas_deteccion():
    e = nueva()
    orden = decir("Cacao, sube el volumen.")
    pasar(e, np.concatenate([silencio(1.5), orden, silencio(2.5)]))
    try:
        d = e.cola.get(timeout=1)
    except Exception:
        d = None
    ok("«Cacao, sube el volumen» de corrido: detectada", d is not None and d[0] == "activacion", e.detecciones)
    if d is not None:
        from faster_whisper import WhisperModel  # Whisper pequeño en la CPU: solo para comprobar qué quedó grabado
        modelo = WhisperModel("base", device="cpu", compute_type="int8")
        texto = " ".join(s.text for s in modelo.transcribe(d[1].astype(np.float32) / 32768, language="es")[0])
        ok("la grabación conserva la orden (búfer previo)", re.search(r"volumen", texto, re.I), texto.strip())
        ok("la grabación termina tras el silencio (no a los 30 s)", len(d[1]) / pa.TASA < 8, f"{len(d[1]) / pa.TASA:.1f} s")
    e.cerrar()

    e = nueva()
    pasar(e, np.concatenate([silencio(1), decir("Hoy hace un día muy bonito para salir a caminar."),
                             decir("Abre la calculadora y sube el volumen."), silencio(1)]))
    ok("conversación sin «Cacao»: no se activa", e.detecciones == 0 and e.cola.empty(), e.detecciones)
    e.cerrar()

    e = nueva(activa=lambda: False)
    pasar(e, np.concatenate([silencio(1), orden, silencio(2)]))
    ok("escucha apagada: no se activa", e.detecciones == 0, e.detecciones)
    e.cerrar()

    hablando = {"si": True}
    e = nueva(ignorar=lambda: hablando["si"])
    pasar(e, np.concatenate([silencio(1), orden, silencio(2)]))
    ok("mientras Cacao habla (Piper) se ignora", e.detecciones == 0, e.detecciones)
    e.cerrar()


def pruebas_grabacion():
    g = pa.Grabacion(np.zeros(0, np.int16), umbral_voz=400)
    voz = (5000 * np.sin(np.arange(pa.TASA) / pa.TASA * 2 * np.pi * 200)).astype(np.int16)
    for _ in range(40):  # 40 s hablando sin parar
        if g.agregar(voz):
            break
    ok("sin silencio: corta a los 30 s", g.terminada and abs(g.t - 30) < 1.1, f"{g.t:.1f} s")
    g = pa.Grabacion(np.zeros(0, np.int16), umbral_voz=400)
    for _ in range(200):  # bloques de 50 ms, como el micrófono
        if g.agregar(np.zeros(800, np.int16)):
            break
    ok("tras la palabra no dice nada: corta a los 4 s", g.terminada and g.t <= 4.1, f"{g.t:.1f} s")


def pruebas_confirmacion():
    m = cv.evaluar("Cacao.", 0.6, por_activacion=True)
    ok("la palabra sola no confirma", m is not None, m)
    m = cv.evaluar("Cacao, confirmo la instrucción.", 1.5, por_activacion=True)
    ok("«Cacao, confirmo la instrucción» confirma", m is None, m)
    m = cv.evaluar("Cacao, confirmo la instrucción.", 1.5, otro_audio=True, por_activacion=True)
    ok("con otro audio sonando, no", m is not None, m)


def pruebas_texto():
    for entrada, salida in (("Cacao, sube el volumen.", "sube el volumen."), ("cacao abre Spotify", "abre Spotify"),
                            ("Oye, Cacao, pon música.", "pon música."), ("Cacao.", ""),
                            ("Kakao, ¿qué hora es?", "¿qué hora es?")):
        ok(f"quitar_palabra: «{entrada}» -> «{salida}»", pa.quitar_palabra(entrada) == salida, pa.quitar_palabra(entrada))
    for texto, esperado in (("Cacao, sube el volumen.", True), ("Oye, Cacao, pon música.", True),
                            ("Kakao abre Spotify", True), ("Me gusta el chocolate con mucho cacao.", False),
                            ("Entonces el cacao se produce muy bien en Colombia.", False), ("¡Caca!", False),
                            ("Hola, Cacao, pon música.", True), ("Del cacao sale el chocolate.", False),
                            ("El caso es que no tengo tiempo.", False), ("Caracas es bonita.", False),
                            ("Gracias por ver el video.", False), ("", False)):
        ok(f"segunda etapa: «{texto}» {'empieza' if esperado else 'no empieza'} con la palabra",
           pa.empieza_con_la_palabra(texto) == esperado)


def cargar_voz_sin_modelo(transcripcion_pausa, transcripcion, en_pausa):
    """escuchar/filtrar/esperar_disparo de voz.py, extraídas con ast (importar voz cargaría Gemma y Whisper)."""
    import ast
    import queue
    import types
    import unicodedata
    import transcripcion as tr
    arbol = ast.parse((pa.BASE / "voz.py").read_text(encoding="utf-8"))
    nombres = {"escuchar", "filtrar", "esperar_disparo"}
    nodos = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name in nombres]
    notificaciones = []

    class Modo:
        def en_pausa(self):
            return "Roblox" if en_pausa else None

    def normalizar(texto):
        t = unicodedata.normalize("NFKD", texto)
        return "".join(c for c in t if not unicodedata.combining(c)).lower()

    agente = types.SimpleNamespace(_modo_juego=Modo(), normalizar=normalizar, FRASES_TERMINE=["ya termine"],
                                   FRASES_JUGANDO=["estoy jugando"], notificar=lambda e, d="": notificaciones.append(e),
                                   cola_pedidos=__import__("pedidos").ColaPedidos())

    class Transcriptor:
        def transcribir(self, _wav):
            return transcripcion

    escucha = types.SimpleNamespace(cola=queue.Queue())
    ns = {"a": agente, "time": time, "queue": queue, "np": np, "analizar_audio": __import__("microfono").analizar_audio,
          "a_wav": tr.a_wav, "transcripcion_plausible": tr.transcripcion_plausible, "contar_palabras": tr.contar_palabras,
          "transcribir_en_pausa": lambda _audio: transcripcion_pausa, "CONFIG_VOZ": {"min_voz_s": 0.15, "max_grabacion_s": 30},
          "_piezas": {"escucha": escucha}, "palabra_activacion": pa, "print": lambda *x, **k: None}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "voz.py", "exec"), ns)
    return ns, escucha, Transcriptor(), notificaciones


def pruebas_bucle():
    class Atajo:
        pulsado = threading.Event()

    audio = np.concatenate([silencio(0.3), (6000 * np.sin(np.arange(int(1.5 * pa.TASA)) / pa.TASA * 2 * np.pi * 180)).astype(np.int16)])
    ns, escucha, tr, notif = cargar_voz_sin_modelo("Cacao, ya terminé.", None, en_pausa=True)
    escucha.cola.put(("activacion", audio, False))
    _, datos, texto, _ = ns["escuchar"](Atajo(), None, tr)
    ok("modo juego: «Cacao, ya terminé» llega como «ya terminé» (Whisper de la CPU)", texto == "ya terminé.", (texto, datos.get("freno")))
    ns, escucha, tr, notif = cargar_voz_sin_modelo(None, "El caso es que no tengo tiempo.", en_pausa=False)
    escucha.cola.put(("activacion", audio, False))
    _, datos, texto, _ = ns["escuchar"](Atajo(), None, tr)
    ok("activación falsa (Whisper no oyó «Cacao»): se descarta sin guardar", texto is None
       and datos.get("freno") == "sin_la_palabra" and "reposo" in notif, datos.get("freno"))
    ns, escucha, tr, notif = cargar_voz_sin_modelo(None, "Cacao, sube el volumen.", en_pausa=False)
    escucha.cola.put(("activacion", audio, False))
    _, datos, texto, _ = ns["escuchar"](Atajo(), None, tr)
    ok("«Cacao, sube el volumen» -> la orden «sube el volumen.»", texto == "sube el volumen.", texto)


def pruebas_contador():
    import json
    pa.RUTA_CONTADOR.unlink(missing_ok=True)
    for etapa in ("primera_etapa", "primera_etapa", "primera_etapa", "segunda_etapa", "segunda_etapa", "pedido"):
        pa.contar(etapa, hoy="2026-10-06")
    pa.contar("primera_etapa", hoy="2026-10-07")
    d = json.loads(pa.RUTA_CONTADOR.read_text(encoding="utf-8"))
    ok("contador: suma por día y por etapa", d["2026-10-06"] == {"primera_etapa": 3, "segunda_etapa": 2, "pedido": 1}
       and d["2026-10-07"]["primera_etapa"] == 1, str(d))
    ok("contador: solo números (sin audio ni texto)", all(isinstance(v, int) for f in d.values() for v in f.values()))
    pa.RUTA_CONTADOR.unlink(missing_ok=True)
    ns, escucha, transcriptor, _ = cargar_voz_sin_modelo(None, "Cacao, sube el volumen.", None)
    escucha.cola.put(("activacion", np.concatenate([silencio(0.3), decir("Cacao, sube el volumen.")]), None))

    class Atajo:
        pulsado = threading.Event()

    ns["escuchar"](Atajo(), None, transcriptor)
    d = json.loads(pa.RUTA_CONTADOR.read_text(encoding="utf-8"))
    hoy = time.strftime("%Y-%m-%d")
    ok("contador: «Cacao, sube el volumen» suma segunda etapa y pedido", d[hoy]["segunda_etapa"] == 1
       and d[hoy]["pedido"] == 1, str(d))
    ns2, escucha2, transcriptor2, _ = cargar_voz_sin_modelo(None, "Me gusta el chocolate con cacao.", None)
    escucha2.cola.put(("activacion", np.concatenate([silencio(0.3), decir("Me gusta el chocolate con cacao.")]), None))
    ns2["escuchar"](Atajo(), None, transcriptor2)
    d = json.loads(pa.RUTA_CONTADOR.read_text(encoding="utf-8"))
    ok("contador: una activación falsa no suma segunda etapa ni pedido", d[hoy]["segunda_etapa"] == 1
       and d[hoy]["pedido"] == 1, str(d))


if __name__ == "__main__":
    if not pa.RUTA_MODELO.exists():
        sys.exit("Falta modelos/cacao/cacao.npz: corre entrenar_cacao.py")
    for parte in (pruebas_deteccion, pruebas_grabacion, pruebas_confirmacion, pruebas_texto, pruebas_bucle, pruebas_contador):
        print(f"\n== {parte.__name__} ==")
        parte()
    fallos = [r for r in resultados if not r[1]]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} OK")
    sys.exit(1 if fallos else 0)
