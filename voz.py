"""
Modo voz del asistente: pulsar para hablar y respuesta hablada. El modo texto (agente_minimo.py) no cambia.

- Mantén el atajo (config.json -> voz.atajo_hablar, por defecto ctrl+espacio) mientras hablas; al soltarlo, el audio
  se transcribe con faster-whisper (transcripcion.py) y la transcripción se muestra en la consola.
- Frenos antes de llegar al agente: una pulsación casi sin voz se descarta sin transcribir; una transcripción con
  más palabras de las que caben en los segundos con voz, o con una frase típica de alucinación de Whisper, también.
- Las herramientas de solo lectura van directas. Las que cambian algo (abrir, volumen, mover, cerrar, teclado...)
  piden confirmación con el TECLADO: Enter = sí, Esc = no (nunca diciendo "sí"); sin respuesta en 30 s = no.
- La respuesta final (lo que devuelve atender) se lee con Piper. El pensamiento, los pasos y las confirmaciones
  NUNCA se leen: solo se muestran en la consola. En modo voz el prompt pide 1 o 2 frases (agente_minimo.MODO_VOZ).
- Cada comando queda en voz_registro/: el WAV y una línea en registro.jsonl (transcripción, frenos, confirmaciones,
  respuesta y latencias). La carpeta no va a git.
- ctrl+alt+shift+q detiene la tarea y lo que se esté diciendo; di "reanudar" para seguir. Di "salir" para terminar.

Uso: .venv\\Scripts\\python voz.py              (modo normal)
     .venv\\Scripts\\python voz.py --medir 5    (mide la latencia de 5 comandos -> resultados_latencia_voz.json)
"""
import json
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
from microfono import TASA, AtajoHablar, Microfono, analizar_audio, confirmar_teclado
from transcripcion import TranscriptorNativo, TranscriptorWhisper, a_wav, contar_palabras, transcripcion_plausible

BASE = Path(__file__).parent
REGISTRO = BASE / "voz_registro"
POR_DEFECTO = {"atajo_hablar": "ctrl+espacio", "motor_transcripcion": "whisper", "whisper_modelo": "large-v3-turbo",
               "whisper_tipo": "int8_float16", "piper_voz": "modelos/piper/es_MX-claude-high.onnx", "velocidad": 1.0,
               "microfono": None, "min_voz_s": 0.15, "max_grabacion_s": 30, "confirmar_timeout_s": 30,
               "ctx_transcripcion": 1024, "lote_transcripcion": 256}
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


def pedir_confirmacion(descripcion):
    print(f"  ¿{descripcion}?  [Enter = sí · Esc = no]", flush=True)
    winsound.MessageBeep(winsound.MB_ICONQUESTION)  # aviso sonoro corto: la pregunta no se lee en voz alta
    respuesta = confirmar_teclado(CONFIG_VOZ["confirmar_timeout_s"], cancelar=a.emergencia.detenido)
    print(f"  -> {'sí' if respuesta else 'no' if respuesta is False else 'sin respuesta: no'}", flush=True)
    comando_actual.setdefault("confirmaciones", []).append({"accion": descripcion, "respuesta": respuesta})
    a.emergencia.comprobar()  # el atajo de emergencia pudo pulsarse mientras se esperaba
    return bool(respuesta)


_ejecutar = a.ejecutar


def ejecutar_voz(nombre, args):
    """Solo lectura: directo. Permiso 'confirmar': lo pregunta ejecutar() con input (= teclado). El resto, aquí."""
    if nombre not in SOLO_LECTURA and a.HERRAMIENTAS[nombre]["permiso"] != "confirmar":
        if not pedir_confirmacion(f"Ejecutar {nombre} {json.dumps(args, ensure_ascii=False)}"):
            return {"ok": False, "error": "Reizo no lo autorizó (Esc o sin respuesta)."}
    return _ejecutar(nombre, args)


def activar_confirmaciones():
    a.ejecutar = ejecutar_voz
    a.input = lambda pregunta="": "s" if pedir_confirmacion(pregunta.strip().rstrip("(s/n)").strip()) else "n"


# ---------- registro ----------

def registrar(n, audio, datos):
    REGISTRO.mkdir(exist_ok=True)
    nombre = time.strftime("%Y%m%d_%H%M%S") + f"_{n}"
    (REGISTRO / f"{nombre}.wav").write_bytes(a_wav(audio))
    with open(REGISTRO / "registro.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"wav": f"{nombre}.wav", **datos}, ensure_ascii=False) + "\n")


# ---------- bucle ----------

def crear_transcriptor():
    if CONFIG_VOZ["motor_transcripcion"] == "gemma":  # audio nativo: descartado en la validación (resultados_voz.md)
        if a.vision is None:
            sys.exit("motor_transcripcion=gemma necesita el mmproj (config.json -> mmproj).")
        return TranscriptorNativo(a.llm, a.vision, CONFIG_VOZ["ctx_transcripcion"], CONFIG_VOZ["lote_transcripcion"])
    return TranscriptorWhisper(CONFIG_VOZ["whisper_modelo"], tipo=CONFIG_VOZ["whisper_tipo"])


def preparar():
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
    planificador, aviso = a.iniciar_memoria_wiki()
    if hasattr(transcriptor, "descargar"):  # el modo juego también libera Whisper
        a.EXTRAS_MODO_JUEGO.append((transcriptor.descargar, transcriptor.cargar))
    if aviso:
        print(f"Asistente: {aviso}")
    historial = [{"role": "system", "content": a.prompt_sistema(voz=True)}]
    activar_confirmaciones()
    # calentamiento: el prompt de sistema queda en la caché KV y los kernels de CUDA de Whisper cargados
    a.llm.create_chat_completion(messages=historial + [{"role": "user", "content": "hola"}], max_tokens=1)
    transcriptor.transcribir(a_wav(np.zeros(TASA // 2, dtype=np.int16)))
    list(locutor.voz.synthesize("hola"))
    print(f"Micrófono: {microfono.nombre}. Transcripción: {CONFIG_VOZ['motor_transcripcion']}. "
          f"Voz: {ruta_voz.stem}.")
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


def escuchar(atajo, microfono, transcriptor, al_pulsar=lambda: None):
    """Graba una pulsación y aplica los frenos. Devuelve (audio, datos del registro, texto o None si se descartó,
    momento de soltar)."""
    atajo.esperar()
    al_pulsar()
    limite = time.perf_counter() + CONFIG_VOZ["max_grabacion_s"]
    audio, pulsada, soltado = microfono.grabar_hasta(lambda: atajo.sigue_pulsado() and time.perf_counter() < limite)
    datos, texto = filtrar(audio, soltado, transcriptor)
    datos["tecla_s"] = round(pulsada, 2)
    return audio, datos, texto, soltado


def filtrar(audio, soltado, transcriptor):
    """Frenos: silencio (sin transcribir), transcripción vacía y demasiadas palabras para la voz que hubo.
    Devuelve (datos para el registro, texto o None si se descartó)."""
    analisis = analizar_audio(audio)
    datos = {"hora": time.strftime("%Y-%m-%d %H:%M:%S"), **analisis}
    if a._modo_juego is not None and a._modo_juego.en_pausa():  # Whisper está descargado
        datos["freno"] = "modo_juego"
        return datos, None
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
    print(f"\nModo voz listo. Mantén {atajo.atajo} mientras hablas; di 'salir' para terminar.")
    while True:
        # hablarle encima corta la respuesta anterior (y no se graba la voz de Piper)
        # pulsar el atajo también detiene una reflexión en curso (libera la GPU antes de transcribir)
        audio, datos, texto, soltado = escuchar(atajo, microfono, transcriptor,
                                                al_pulsar=lambda: (locutor.callar(), planificador.parar.set()))
        n += 1
        comando_actual.clear()
        if texto is None:
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
        print(f"Asistente: {respuesta}", flush=True)
        inicio = {}
        pulsaciones = a.emergencia.pulsaciones
        locutor.hablar(limpiar_para_voz(respuesta), al_empezar=lambda t: inicio.setdefault("t", t),
                       cortar=lambda: a.emergencia.pulsaciones != pulsaciones)  # el atajo también la calla
        limite = time.perf_counter() + 15
        while "t" not in inicio and locutor.hablando() and time.perf_counter() < limite:
            time.sleep(0.005)
        empieza = inicio.get("t")
        latencias = {"transcribir_s": datos["transcribir_s"], "agente_s": round(t_respuesta - t_transcrito, 2),
                     "piper_s": round(empieza - t_respuesta, 2) if empieza else None,
                     "total_s": round(empieza - soltado, 2) if empieza else None,
                     "salida_altavoz_s": round(locutor.salida.latency, 3)}
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
    atajo.cerrar()
    microfono.cerrar()
    transcriptor.cerrar()


if __name__ == "__main__":
    bucle(int(sys.argv[sys.argv.index("--medir") + 1]) if "--medir" in sys.argv else 0)
