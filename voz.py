"""
Modo voz del asistente: pulsar para hablar y respuesta hablada. El modo texto (agente_minimo.py) no cambia.

- Mantén el atajo (config.json -> voz.atajo_hablar, por defecto ctrl+espacio) mientras hablas; al soltarlo, el audio
  se transcribe con faster-whisper (transcripcion.py) y la transcripción se muestra en la consola.
- Frenos antes de llegar al agente: una pulsación casi sin voz se descarta sin transcribir; una transcripción con
  más palabras de las que caben en los segundos con voz, o con una frase típica de alucinación de Whisper, también.
- Las herramientas de solo lectura van directas. Las que cambian algo (abrir, volumen, mover, cerrar, teclado...)
  piden confirmación: Enter = sí, Esc = no, los botones de la isla, o la frase "confirmo la instrucción" en una
  grabación aparte tras la pregunta (confirmacion_voz.py; "sí" solo no vale). Sin respuesta en 30 s = no.
- La respuesta final (lo que devuelve atender) se lee con Piper, o con Qwen3-TTS si config.json -> voz.tts_motor es
  "qwen3" (tts_qwen.py; Piper queda de respaldo). El pensamiento, los pasos y las confirmaciones
  NUNCA se leen: solo se muestran en la consola. En modo voz el prompt pide 1 o 2 frases (agente_minimo.MODO_VOZ).
- Cada comando queda en voz_registro/: el WAV y una línea en registro.jsonl (transcripción, frenos, confirmaciones,
  respuesta y latencias). La carpeta no va a git.
- ctrl+alt+shift+q detiene la tarea y lo que se esté diciendo; di "reanudar" para seguir. Di "salir" para terminar.
- Palabra de activación "Cacao" (palabra_activacion.py, en la CPU; se enciende y apaga con un clic físico en la
  bandeja o en la isla): al oírla, la isla muestra "escuchando", se graba con un búfer previo hasta un silencio o
  30 s y pasa por los mismos frenos y por Whisper. Mientras Cacao habla se ignora. Sigue activa en modo juego.
- Escucha de seguimiento (seguimiento.py; modo «seguimiento», con un clic físico en Ajustes de la isla): al terminar
  de hablar, Cacao sigue oyendo 8 s sin la palabra, con un indicador en la isla. Si hablas, es un pedido normal (mismos
  frenos y confirmaciones); si no, termina. No se abre con otra app sonando ni con la escucha de «Cacao» apagada.

Uso: .venv\\Scripts\\python voz.py              (modo normal)
     .venv\\Scripts\\python voz.py --medir 5    (mide la latencia de 5 comandos -> resultados_latencia_voz.json)
"""
import json
import queue
import re
import subprocess
import sys
import threading
import time
import unicodedata
import winsound
from pathlib import Path

import numpy as np
import sounddevice as sd
from piper import PiperVoice, SynthesisConfig

import agente_minimo as a
import confirmacion_voz
import palabra_activacion
import seguimiento
import tts_qwen
from microfono import TASA, UMBRAL_VOZ, AtajoHablar, Microfono, analizar_audio
from transcripcion import TranscriptorNativo, TranscriptorWhisper, a_wav, contar_palabras, transcripcion_plausible

BASE = Path(__file__).parent
REGISTRO = BASE / "voz_registro"
POR_DEFECTO = {"atajo_hablar": "ctrl+espacio", "motor_transcripcion": "whisper", "whisper_modelo": "large-v3-turbo",
               "whisper_tipo": "int8_float16", "piper_voz": "modelos/piper/es_MX-claude-high.onnx", "velocidad": 1.0,
               "microfono": None, "min_voz_s": 0.15, "max_grabacion_s": 30, "confirmar_timeout_s": 30,
               "ctx_transcripcion": 1024, "lote_transcripcion": 256, "tts_motor": "piper"}
CONFIG_VOZ = {**POR_DEFECTO, **a.CONFIG.get("voz", {})}
# herramientas que solo leen: van directas. Cualquier otra (también las futuras) se confirma con Enter/Esc.
SOLO_LECTURA = {"listar_apps", "listar_ventanas", "listar_carpeta", "leer_archivo", "consultar_memoria",
                "ver_pantalla", "listar_controles", "finalizar"}


def normalizar(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    return re.sub(r"[^a-z0-9 ]", "", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()


def limpiar_para_voz(texto):
    """Quita lo que no se debe pronunciar: markdown, viñetas, URLs y rutas."""
    texto = re.sub(r"https?://\S+", "el enlace", texto)
    texto = re.sub(r"[A-Za-z]:\\\S+", "esa ruta", texto)
    texto = re.sub(r"^\s*([-*•]|\d+\.)\s+", "", texto, flags=re.M)
    texto = re.sub(r"[*_`#>|]", "", texto)
    texto = re.sub(r"\s*\n+\s*", ". ", texto)
    return re.sub(r"\.\s*\.", ".", re.sub(r"\s{2,}", " ", texto)).strip()


class Locutor:
    """Piper en un hilo: empieza a sonar con la primera frase sintetizada y se puede cortar en cualquier momento."""

    TROZO_S = 0.1  # se escribe al altavoz en trozos cortos para poder callar enseguida

    def __init__(self, ruta_voz, velocidad=1.0):
        self.voz = PiperVoice.load(str(ruta_voz))
        self.config = SynthesisConfig(length_scale=1.0 / velocidad)
        self.tasa = self.voz.config.sample_rate
        self.salida = sd.OutputStream(samplerate=self.tasa, channels=1, dtype="int16")
        self.salida.start()
        self._callar = threading.Event()
        self._hilo = None

    def hablar(self, texto, al_empezar=None, cortar=lambda: False):
        self.callar()
        self._callar.clear()
        self._hilo = threading.Thread(target=self._decir, args=(texto, al_empezar, cortar), daemon=True)
        self._hilo.start()

    def _decir(self, texto, al_empezar, cortar):
        n = int(self.tasa * self.TROZO_S)
        for trozo in self.voz.synthesize(texto, syn_config=self.config):
            audio = np.frombuffer(trozo.audio_int16_bytes, dtype=np.int16)
            for i in range(0, len(audio), n):
                if self._callar.is_set() or cortar():
                    return
                if al_empezar:
                    al_empezar(time.perf_counter())
                    al_empezar = None
                self.salida.write(audio[i:i + n])

    def callar(self):
        self._callar.set()
        if self._hilo is not None:
            self._hilo.join(2)

    def hablando(self):
        return self._hilo is not None and self._hilo.is_alive()


# ---------- confirmación con teclado ----------

comando_actual = {}  # registro del comando en curso: aquí se anotan las confirmaciones


def pedir_confirmacion(descripcion, herramienta="accion", motivo=None, comando=None):
    """Enter/Esc o botones de la isla, solo con entrada física (agente_minimo.confirmar)."""
    winsound.MessageBeep(winsound.MB_ICONQUESTION)  # aviso sonoro corto: la pregunta no se lee en voz alta
    respuesta = _confirmar_base(herramienta, descripcion, motivo, comando)
    ultima = getattr(a._confirmacion, "ultima", None) or {}
    comando_actual.setdefault("confirmaciones", []).append(
        {"accion": descripcion, "respuesta": respuesta, "via": ultima.get("via")})
    a.emergencia.comprobar()  # el atajo de emergencia pudo pulsarse mientras se esperaba
    return respuesta


_confirmar_base = a.confirmar


_ejecutar = a.ejecutar


def ejecutar_voz(nombre, args):
    """Solo lectura: directo. Permiso 'confirmar': lo pregunta ejecutar() con input (= teclado). El resto, aquí."""
    if nombre not in SOLO_LECTURA and a.HERRAMIENTAS[nombre]["permiso"] != "confirmar" \
            and not a.decision_modo(nombre, args)[0]:
        if not pedir_confirmacion(f"Ejecutar {nombre} {json.dumps(args, ensure_ascii=False)}", nombre):
            return {"ok": False, "rechazado": True, "error": "Reizo no lo autorizó (Esc o sin respuesta)."}
    return _ejecutar(nombre, args)


def activar_confirmaciones():
    a.ejecutar = ejecutar_voz
    a.confirmar = lambda herramienta, resumen, motivo=None, comando=None: pedir_confirmacion(
        resumen, herramienta, motivo, comando)
    a._confirmar_extra = escuchar_confirmacion


# ---------- confirmación por voz ("confirmo la instrucción") ----------

_piezas = {}  # atajo, micrófono, transcriptor y locutor: los pone preparar()


def escuchar_confirmacion(aceptar, hecho, entrada):
    """Corre en un hilo mientras se espera una confirmación (confirmacion_voz.Oyente)."""
    if not _piezas:
        return
    atajo = _piezas["atajo"]
    confirmacion_voz.Oyente(atajo, _piezas["microfono"], _piezas["transcriptor"], min_voz_s=CONFIG_VOZ["min_voz_s"],
                            disparos=lambda s: esperar_disparo(atajo, s)).escuchar(aceptar, hecho, entrada)


def crear_escucha(microfono, locutor):
    """La palabra de activación, si hay modelo entrenado (entrenar_cacao.py) y no está apagada en config.json."""
    cfg = {"activa": True, "activa_al_iniciar": True, **CONFIG_VOZ.get("palabra_activacion", {})}
    if not cfg["activa"]:
        return None
    if not palabra_activacion.RUTA_MODELO.exists():
        print("Aviso: no hay modelo de la palabra «Cacao» (corre entrenar_cacao.py); solo Ctrl+Espacio.")
        return None
    a._modos["escucha"] = bool(cfg["activa_al_iniciar"])
    escucha = palabra_activacion.Escucha(
        microfono.tasa, activa=lambda: a._modos.get("escucha", False),
        ignorar=lambda: locutor.hablando() or microfono.grabando or (
            _piezas.get("seguimiento") is not None and _piezas["seguimiento"].abierta),
        al_detectar=lambda: (locutor.callar(), a.notificar("escuchando")),
        umbral_voz=UMBRAL_VOZ, mirar_audio=confirmacion_voz.otro_audio_sonando)
    microfono.oyentes.append(escucha.recibir)
    return escucha


def crear_seguimiento(microfono):
    """La escucha de seguimiento tras cada respuesta (modo «seguimiento»; empieza según config.json)."""
    cfg = {"activa_al_iniciar": True, "segundos": 8, **CONFIG_VOZ.get("seguimiento", {})}
    a._modos["seguimiento"] = bool(cfg["activa_al_iniciar"])
    s = seguimiento.Seguimiento(microfono.tasa, UMBRAL_VOZ, mirar_audio=confirmacion_voz.otro_audio_sonando,
                                al_empezar=lambda: (a_la_isla({"tipo": "seguimiento", "activo": False}),
                                                    a.notificar("escuchando")))
    s.segundos = cfg["segundos"]
    microfono.oyentes.append(s.recibir)
    return s


def a_la_isla(mensaje):
    if a._isla is not None:
        a._isla.enviar(mensaje)


class DespuesDeResponder:
    """Lo que pasa tras cada respuesta hablada (el bucle lo revisa mientras espera el siguiente pedido): avisa a la
    isla cuando Cacao termina de hablar (fin_habla: la isla empieza a contar para esconderse) y abre la escucha de
    seguimiento si se puede."""

    def __init__(self, locutor, oido):
        self.locutor, self.oido, self.fase = locutor, oido, None

    def empezar(self):
        self.fase = "hablando"

    def puede_seguir(self):
        return bool(self.oido is not None and a._modos.get("seguimiento") and a._modos.get("escucha")
                    and not (a._modo_juego is not None and a._modo_juego.en_pausa()) and not a.emergencia.detenido())

    def revisar(self):
        if self.fase == "hablando" and not self.locutor.hablando():
            a_la_isla({"tipo": "fin_habla"})
            self.fase = None
            if self.puede_seguir():
                if self.oido.abrir(self.oido.segundos):
                    self.fase = "siguiendo"
                    a_la_isla({"tipo": "seguimiento", "activo": True, "segundos": self.oido.segundos})
                    print(f"  (te sigo oyendo {self.oido.segundos} s sin «Cacao»)", flush=True)
                else:
                    print("  (otra app está sonando: sin escucha de seguimiento; di «Cacao»)", flush=True)
        elif self.fase == "siguiendo" and not self.oido.abierta:
            self.fase = None
            a_la_isla({"tipo": "seguimiento", "activo": False})

    def cancelar(self):
        """Llegó otro disparo (Ctrl+Espacio, un pedido escrito): la respuesta se calla y la escucha se cierra."""
        if self.fase == "hablando":
            a_la_isla({"tipo": "fin_habla"})
        elif self.fase == "siguiendo":
            self.oido.cerrar()
            a_la_isla({"tipo": "seguimiento", "activo": False})
        self.fase = None


# ---------- registro ----------

def registrar(n, audio, datos):
    REGISTRO.mkdir(exist_ok=True)
    nombre = time.strftime("%Y%m%d_%H%M%S") + f"_{n}"
    if audio is not None:  # un pedido escrito en la isla no tiene audio
        (REGISTRO / f"{nombre}.wav").write_bytes(a_wav(audio))
    with open(REGISTRO / "registro.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"wav": f"{nombre}.wav" if audio is not None else None, **datos}, ensure_ascii=False)
                + "\n")


# ---------- bucle ----------

def crear_transcriptor():
    if CONFIG_VOZ["motor_transcripcion"] == "gemma":  # audio nativo: descartado en la validación (resultados_voz.md)
        if a.vision is None:
            sys.exit("motor_transcripcion=gemma necesita el mmproj (config.json -> mmproj).")
        return TranscriptorNativo(a.llm, a.vision, CONFIG_VOZ["ctx_transcripcion"], CONFIG_VOZ["lote_transcripcion"])
    return TranscriptorWhisper(CONFIG_VOZ["whisper_modelo"], tipo=CONFIG_VOZ["whisper_tipo"], esperar_juego=True)


def preparar():
    a.cargar_modelo()  # antes que Whisper y Piper, como cuando se cargaba al importar agente_minimo
    if a.emergencia.iniciar():
        print(f"Atajo de emergencia activo: {a.emergencia.atajo}")
    atajo = AtajoHablar(CONFIG_VOZ["atajo_hablar"])
    if not atajo.iniciar():
        sys.exit(f"No pude registrar {CONFIG_VOZ['atajo_hablar']}: otro programa lo usa. Cambia voz.atajo_hablar "
                 "en config.json (por ejemplo ctrl+shift+espacio).")
    microfono = Microfono(CONFIG_VOZ["microfono"])
    transcriptor = crear_transcriptor()
    ruta_voz = Path(CONFIG_VOZ["piper_voz"])
    locutor = Locutor(ruta_voz if ruta_voz.is_absolute() else BASE / ruta_voz, CONFIG_VOZ["velocidad"])
    locutor = tts_qwen.crear_locutor(locutor, CONFIG_VOZ, a.CONFIG)  # Piper, salvo voz.tts_motor = "qwen3"
    _piezas.update(atajo=atajo, microfono=microfono, transcriptor=transcriptor, locutor=locutor)
    _piezas["escucha"] = crear_escucha(microfono, locutor)
    # sin la escucha de "Cacao" (apagada en config.json) tampoco hay escucha de seguimiento
    _piezas["seguimiento"] = crear_seguimiento(microfono) if _piezas["escucha"] is not None else None
    _piezas["despues"] = DespuesDeResponder(locutor, _piezas["seguimiento"])
    a.iniciar_isla()
    planificador, aviso = a.iniciar_memoria_wiki()
    if hasattr(transcriptor, "descargar"):  # el modo juego también libera Whisper
        a.EXTRAS_MODO_JUEGO.append((transcriptor.descargar, transcriptor.cargar))
    if aviso:
        print(f"Cacao: {aviso}")
    historial = [{"role": "system", "content": a.prompt_sistema(voz=True)}]
    activar_confirmaciones()
    # calentamiento: el prompt de sistema queda en la caché KV y los kernels de CUDA de Whisper cargados
    a.llm.create_chat_completion(messages=historial + [{"role": "user", "content": "hola"}], max_tokens=1)
    transcriptor.transcribir(a_wav(np.zeros(TASA // 2, dtype=np.int16)))
    list(locutor.voz.synthesize("hola"))
    if isinstance(locutor, tts_qwen.LocutorQwen):
        locutor.iniciar()  # después del LLM y de Whisper; en un hilo, y mientras tanto habla Piper
        a.EXTRAS_MODO_JUEGO.append((locutor.descargar, locutor.cargar))  # tras Whisper: vuelve con la VRAM libre
    print(f"Micrófono: {microfono.nombre}. Transcripción: {CONFIG_VOZ['motor_transcripcion']}. "
          f"Voz: {'Qwen3-TTS (Piper de respaldo, ' if isinstance(locutor, tts_qwen.LocutorQwen) else ''}"
          f"{ruta_voz.stem}{')' if isinstance(locutor, tts_qwen.LocutorQwen) else ''}.")
    return atajo, microfono, transcriptor, locutor, historial, planificador


class MedidorVRAM:
    """Muestrea la VRAM usada (toda la GPU, con nvidia-smi) cada 0,5 s en un hilo y guarda el pico."""

    def __init__(self):
        self.pico, self.total, self._parar = 0, 0, threading.Event()
        threading.Thread(target=self._muestrear, daemon=True).start()

    def _muestrear(self):
        while not self._parar.is_set():
            try:
                usado, total = map(int, subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout.split(","))
                self.pico, self.total = max(self.pico, usado), total
            except (ValueError, OSError):
                pass
            self._parar.wait(0.5)

    def parar(self):
        self._parar.set()


def esperar_disparo(atajo, segundos=None, isla=False):
    """'atajo' (Ctrl+Espacio), ('activacion', audio, otro_audio) tras la palabra "Cacao", ('isla', texto) con un
    pedido escrito en la isla (solo con isla=True, que usa el bucle y no la confirmación por voz) o None si pasó el
    tiempo. Lo usan el bucle y, durante una confirmación, el oyente de la frase."""
    limite = None if segundos is None else time.monotonic() + segundos
    escucha = _piezas.get("escucha")
    oido, despues = _piezas.get("seguimiento"), _piezas.get("despues")
    while True:
        if isla and despues is not None:  # solo el bucle principal, no la confirmación por voz
            despues.revisar()
            llegado = None
            if oido is not None:
                try:
                    llegado = oido.cola.get_nowait()
                except queue.Empty:
                    pass
            if llegado and llegado[0] == "seguimiento":
                return llegado
            if llegado:
                print("  (fin de la escucha de seguimiento: "
                      f"{'otra app sonando' if llegado[1] == 'otro_audio' else 'nadie habló'})", flush=True)
        if atajo.pulsado.is_set():
            atajo.pulsado.clear()
            return "atajo"
        if isla and (texto := a.cola_pedidos.pedido_isla()):
            return ("isla", texto)
        if escucha is not None:
            try:
                return escucha.cola.get(timeout=0.05)
            except queue.Empty:
                pass
        else:
            time.sleep(0.05)
        if limite is not None and time.monotonic() >= limite:
            return None


def escuchar(atajo, microfono, transcriptor, al_pulsar=lambda: None):
    """Espera Ctrl+Espacio o la palabra "Cacao", graba y aplica los frenos. Devuelve (audio, datos del registro,
    texto o None si se descartó, momento de soltar)."""
    disparo = esperar_disparo(atajo, isla=True)
    if disparo[0] != "seguimiento" and _piezas.get("despues") is not None:
        _piezas["despues"].cancelar()
    al_pulsar()
    if disparo[0] == "seguimiento":
        # dicho en la escucha de seguimiento, sin "Cacao": mismos frenos; con otra app sonando, no vale
        audio, otro_audio, soltado = disparo[1], disparo[2], time.perf_counter()
        datos, texto = filtrar(audio, soltado, transcriptor)
        datos["disparo"] = "seguimiento"
        if texto is not None and otro_audio:
            datos["freno"], texto = "otro_audio", None
            print("  (descartado: otra app sonaba mientras hablabas)", flush=True)
        if texto is not None and palabra_activacion.empieza_con_la_palabra(texto):
            texto = palabra_activacion.quitar_palabra(texto) or None  # "Cacao, ..." también vale aquí
        if texto is None:
            a.notificar_reposo()
        else:
            palabra_activacion.contar("seguimiento")
        return audio, datos, texto, soltado
    if disparo[0] == "isla":
        # escrito en la isla: sin audio ni frenos de voz; los permisos y las confirmaciones son los de siempre
        print(f"\nTú (isla): {disparo[1]}", flush=True)
        return None, {"hora": time.strftime("%Y-%m-%d %H:%M:%S"), "disparo": "isla", "duracion_s": 0.0,
                      "transcribir_s": 0.0}, disparo[1], time.perf_counter()
    if disparo == "atajo":
        limite = time.perf_counter() + CONFIG_VOZ["max_grabacion_s"]
        audio, pulsada, soltado = microfono.grabar_hasta(lambda: atajo.sigue_pulsado() and time.perf_counter() < limite)
        datos, texto = filtrar(audio, soltado, transcriptor)
        datos["tecla_s"] = round(pulsada, 2)
        return audio, datos, texto, soltado
    audio, soltado = disparo[1], time.perf_counter()
    datos, texto = filtrar(audio, soltado, transcriptor)
    datos["disparo"] = "cacao"
    dicho = texto if texto is not None else datos.get("transcripcion") or datos.get("transcripcion_pausa") or ""
    if not palabra_activacion.empieza_con_la_palabra(dicho):
        # segunda etapa: Whisper no oyó "Cacao" al principio: activación falsa. No se guarda nada.
        datos["freno"] = "sin_la_palabra"
        print("  (activación falsa: la transcripción no empieza con «Cacao»; descartada sin guardar)", flush=True)
        a.notificar_reposo()
        return audio, datos, None, soltado
    palabra_activacion.contar("segunda_etapa")
    if texto is not None:
        orden = palabra_activacion.quitar_palabra(texto)
        if not orden:
            datos["freno"] = "solo_la_palabra"
            print("  (solo dijiste «Cacao»: no hay orden)", flush=True)
            a.notificar_reposo()
            return audio, datos, None, soltado
        texto = orden
        palabra_activacion.contar("pedido")
    else:
        a.notificar_reposo()
    return audio, datos, texto, soltado


_transcriptor_pausa = None


def transcribir_en_pausa(audio):
    global _transcriptor_pausa
    if _transcriptor_pausa is None:  # se carga la primera vez (y se descarga el modelo la primera vez que se usa)
        _transcriptor_pausa = TranscriptorWhisper(CONFIG_VOZ.get("whisper_pausa", "base"), dispositivo="cpu",
                                                  tipo="int8")
    return _transcriptor_pausa.transcribir(a_wav(audio))


def filtrar(audio, soltado, transcriptor):
    """Frenos: silencio (sin transcribir), transcripción vacía y demasiadas palabras para la voz que hubo.
    Devuelve (datos para el registro, texto o None si se descartó)."""
    analisis = analizar_audio(audio)
    datos = {"hora": time.strftime("%Y-%m-%d %H:%M:%S"), **analisis}
    if a._modo_juego is not None and a._modo_juego.en_pausa():
        # Whisper de la GPU está descargado: un modelo pequeño en la CPU solo para entender "ya terminé"
        texto = transcribir_en_pausa(audio) if analisis["voz_s"] >= CONFIG_VOZ["min_voz_s"] else ""
        datos.update(transcripcion_pausa=texto, transcribir_s=round(time.perf_counter() - soltado, 2))
        # solo «ya terminé», «estoy jugando» y el volumen del camino rápido (sin el modelo ni la GPU)
        volumen = a.CAMINO_RAPIDO and a.camino_rapido.reconocer(texto, solo={"volumen"})
        if not volumen and not any(f in a.normalizar(texto) for f in a.FRASES_TERMINE + a.FRASES_JUGANDO):
            datos["freno"] = "modo_juego"
            return datos, None
        print(f"\nTú (voz, en pausa): {texto}", flush=True)
        return datos, texto
    if analisis["voz_s"] < CONFIG_VOZ["min_voz_s"]:
        datos["freno"] = "silencio"
        print(f"  (descartado sin transcribir: {analisis['voz_s']} s de voz)", flush=True)
        return datos, None
    texto = transcriptor.transcribir(a_wav(audio))
    datos.update(transcripcion=texto, transcribir_s=round(time.perf_counter() - soltado, 2))
    if not texto.strip():
        datos["freno"] = "transcripcion_vacia"
    elif not transcripcion_plausible(texto, analisis["voz_s"]):
        datos["freno"] = "palabras"
        print(f"  (descartado: {contar_palabras(texto)} palabras en {analisis['voz_s']} s de voz: «{texto}»)",
              flush=True)
    if datos.get("freno"):
        return datos, None
    print(f"\nTú (voz, {analisis['duracion_s']} s): {texto}", flush=True)
    return datos, texto


def bucle(medir=0):
    vram = MedidorVRAM() if medir else None
    atajo, microfono, transcriptor, locutor, historial, planificador = preparar()
    mediciones, n = [], 0
    try:
        print(f"\nModo voz listo. Mantén {atajo.atajo} mientras hablas; di 'salir' o pulsa Ctrl+C para terminar.")
        while True:
            # hablarle encima corta la respuesta anterior (y no se graba la voz de Piper)
            # pulsar el atajo también detiene una reflexión en curso (libera la GPU antes de transcribir)
            audio, datos, texto, soltado = escuchar(atajo, microfono, transcriptor,
                                                    al_pulsar=lambda: (locutor.callar(), planificador.parar.set()))
            n += 1
            comando_actual.clear()
            if texto is None:
                # una activación falsa, o lo que se oyó en la escucha de seguimiento sin ser un pedido, no deja rastro
                if datos.get("freno") != "sin_la_palabra" and datos.get("disparo") != "seguimiento":
                    registrar(n, audio, datos)
                if datos.get("freno") == "modo_juego":
                    locutor.hablar(limpiar_para_voz(a._modo_juego.mensaje()))  # Piper va en la CPU
                continue
            t_transcrito = time.perf_counter()
            orden = normalizar(texto)
            if orden in ("salir", "salir del modo voz"):
                registrar(n, audio, {**datos, "respuesta": "(salir)"})
                locutor.hablar("Hasta luego.")
                time.sleep(1.5)
                break
            if orden in ("reanudar", "reanuda"):
                a.emergencia.reanudar()
                respuesta = "Listo, vuelvo a atender pedidos."
            else:
                respuesta = a.atender_con_memoria(texto, historial, planificador, voz=True)
                historial[:] = historial[:1] + historial[1:][-20:]  # memoria corta, como en el modo texto
            t_respuesta = time.perf_counter()
            print(f"Cacao: {respuesta}", flush=True)
            inicio = {}
            pulsaciones = a.emergencia.pulsaciones
            locutor.hablar(limpiar_para_voz(respuesta), al_empezar=lambda t: inicio.setdefault("t", t),
                           cortar=lambda: a.emergencia.pulsaciones != pulsaciones)  # el atajo también la calla
            _piezas["despues"].empezar()  # al terminar de hablar: fin_habla a la isla y escucha de seguimiento
            limite = time.perf_counter() + 15
            while "t" not in inicio and locutor.hablando() and time.perf_counter() < limite:
                time.sleep(0.005)
            empieza = inicio.get("t")
            latencias = {"transcribir_s": datos["transcribir_s"], "agente_s": round(t_respuesta - t_transcrito, 2),
                         "piper_s": round(empieza - t_respuesta, 2) if empieza else None,
                         "total_s": round(empieza - soltado, 2) if empieza else None,
                         "salida_altavoz_s": round(locutor.salida.latency, 3),
                         "voz": getattr(locutor, "ultimo_motor", "piper")}
            confirmaciones = list(comando_actual.get("confirmaciones", []))
            registrar(n, audio, {**datos, "respuesta": respuesta, "confirmaciones": confirmaciones, **latencias})
            if medir:
                mediciones.append({"transcripcion": texto, "respuesta": respuesta, "confirmaciones": confirmaciones,
                                   "audio_s": datos["duracion_s"], **latencias})
                print("  [latencia] " + json.dumps(latencias), flush=True)
                if len(mediciones) >= medir:
                    while locutor.hablando():
                        time.sleep(0.05)
                    vram.parar()
                    resumen = {"vram_pico_mb": vram.pico, "vram_total_mb": vram.total,
                               "vram_libre_en_el_pico_mb": vram.total - vram.pico, "comandos": mediciones}
                    (BASE / "resultados_latencia_voz.json").write_text(
                        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
                    print(f"\nMedidos {medir} comandos: resultados_latencia_voz.json. VRAM pico {vram.pico} de "
                          f"{vram.total} MB (libres {vram.total - vram.pico} MB).")
                    break
    except KeyboardInterrupt:
        print("\nHasta luego.")
    finally:
        if _piezas.get("seguimiento") is not None:
            _piezas["seguimiento"].apagar()
        atajo.cerrar()
        microfono.cerrar()
        a.cerrar_isla()
        transcriptor.cerrar()
        if hasattr(locutor, "cerrar"):
            locutor.cerrar()


if __name__ == "__main__":
    a.salida_utf8()
    bucle(int(sys.argv[sys.argv.index("--medir") + 1]) if "--medir" in sys.argv else 0)
