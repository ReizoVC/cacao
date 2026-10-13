"""
Voz Qwen3-TTS 0.6B (llama.cpp, clonando A1_equilibrada) con Piper de respaldo.

voz.py lo usa solo si config.json -> voz.tts_motor es "qwen3" (por defecto, "piper"). LocutorQwen tiene la misma
interfaz que voz.Locutor (hablar, callar, hablando, salida, voz, tasa): fin_habla, la escucha de seguimiento,
confirmacion_voz.otro_audio_sonando y la isla no cambian, porque el audio se reproduce en este proceso.

- Motor: modelos/qwen3-tts/ (fuera de Git). bin/tts_qwen_servidor.exe (tts_qwen_motor/servidor.cpp, llama.cpp
  81bc6b8) es un proceso hijo por tubería: texto por stdin, PCM por stdout. Sin red ni puertos.
- Al arrancar (en un hilo, tras el LLM y Whisper): SHA-256 de todos los archivos contra tts_qwen_motor/hashes.json,
  guardia_juego (con un juego abierto no se carga), perfil medido y VRAM libre suficiente para el TTS más el pico
  de la visión. Si algo falla, habla Piper.
- Supervisado: si el proceso cae, se cuelga o va lento (tiempo máximo por trozo), el resto de esa respuesta lo dice
  Piper, se anota y se rearranca en segundo plano, con un límite de rearranques.
- Voz por trozos: oraciones; la primera, si es larga, también se parte por comas (baja el primer audio). Cada trozo
  se sintetiza mientras suena el anterior. Números y símbolos se pasan a palabras (Piper lo hace con espeak).
- Modo juego: descargar() para el proceso (Piper en la CPU durante la pausa) y cargar() lo vuelve a comprobar todo.
"""
import hashlib
import json
import queue
import re
import subprocess
import threading
import time
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent
CARPETA = BASE / "modelos" / "qwen3-tts"
HASHES = BASE / "tts_qwen_motor" / "hashes.json"
MODELO = "Qwen3-TTS-12Hz-0.6B-Base-Q8_0.gguf"
MMPROJ = "mmproj-Qwen3-TTS-12Hz-0.6B-Base-Q8_0.gguf"
VOZ = "voz/A1_equilibrada.wav"
# VRAM medida (fase B, comparacion_modelos/resumen_qwen3_tts_llama_cpp.json): el TTS residente ocupa 3 326 MiB y la
# visión de cada perfil sube el pico por encima de eso. Perfil sin medir = no cabe (Gemma): habla Piper.
VRAM_TTS_MIB = 3330
EXTRA_VISION_MIB = {"qwen9b": 1255}
MARGEN_MIB = 500
MAX_REARRANQUES = 3
ESPERA_ARRANQUE_S = 120
PRIMER_TROZO_MAX = 60  # caracteres: la primera oración más larga se parte también por comas
TROZO_MIN = 20


# ---------- texto ----------

_UNIDADES = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce",
             "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte",
             "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete",
             "veintiocho", "veintinueve"]
_DECENAS = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta", 9: "noventa"}
_CENTENAS = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos", 6: "seiscientos",
             7: "setecientos", 8: "ochocientos", 9: "novecientos"}


def _apocope(texto):
    """«veintiuno mil» → «veintiún mil», «treinta y uno mil» → «treinta y un mil»."""
    return re.sub(r"veintiuno$", "veintiún", re.sub(r"(?<![a-z])uno$", "un", texto))


def numero_a_palabras(n):
    """Entero no negativo (< 10^12) en palabras, en español."""
    if n < 30:
        return _UNIDADES[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _DECENAS[d] + ("" if u == 0 else " y " + _UNIDADES[u])
    if n < 1000:
        c, r = divmod(n, 100)
        if n == 100:
            return "cien"
        return _CENTENAS[c] + ("" if r == 0 else " " + numero_a_palabras(r))
    if n < 1_000_000:
        m, r = divmod(n, 1000)
        miles = "mil" if m == 1 else _apocope(numero_a_palabras(m)) + " mil"
        return miles + ("" if r == 0 else " " + numero_a_palabras(r))
    if n < 10**12:
        m, r = divmod(n, 1_000_000)
        millones = "un millón" if m == 1 else _apocope(numero_a_palabras(m)) + " millones"
        return millones + ("" if r == 0 else " " + numero_a_palabras(r))
    return " ".join(_UNIDADES[int(c)] for c in str(n))


def _cifras(texto):
    return " ".join(_UNIDADES[int(c)] for c in texto)


def _numero(m):
    """1.234.567 (miles con punto), 3,5 y 3.5 (decimales) o un entero."""
    s = m.group(0)
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", s):
        entero, _, decimal = s.replace(".", "").partition(",")
    else:
        entero, _, decimal = s.replace(",", ".").partition(".")
    texto = _cifras(entero) if len(entero) > 12 else numero_a_palabras(int(entero))
    if decimal:
        texto += " coma " + (_cifras(decimal) if decimal.startswith("0") or len(decimal) > 3
                             else numero_a_palabras(int(decimal)))
    return texto


def normalizar_texto(texto):
    """Números y símbolos a palabras (lo que Piper resuelve con espeak). Lo demás no cambia."""
    t = texto
    t = re.sub(r"(\d{1,2}):(\d{2})\b", lambda m: f"{int(m.group(1))} {'en punto' if m.group(2) == '00' else m.group(2)}",
               t)
    t = re.sub(r"[$]\s?(\d[\d.,]*)", r"\1 dólares", t)
    t = re.sub(r"(\d[\d.,]*)\s?€", r"\1 euros", t)
    t = re.sub(r"(\d)\s?%", r"\1 por ciento", t)
    t = re.sub(r"(\d)\s?°\s?C\b", r"\1 grados", t)
    t = re.sub(r"(\d)\s?°", r"\1 grados", t)
    t = re.sub(r"(?<![\w.,])(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?![\w]|[.,]\d)", _numero, t)
    t = re.sub(r"(?<=\d)\.(?=\d)", " punto ", t)  # versiones e IP: 2.0.1
    t = re.sub(r"\d+", lambda m: _cifras(m.group(0)), t)
    t = t.replace("&", " y ").replace("+", " más ").replace("%", " por ciento").replace("#", " número ")
    return re.sub(r"\s{2,}", " ", t).strip()


def partir(texto):
    """Trozos para la voz: oraciones; la primera, si es larga, también por comas (sin trozos de menos de
    TROZO_MIN caracteres)."""
    oraciones = [o.strip() for o in re.split(r"(?<=[.!?…])\s+", texto.strip()) if o.strip()]
    if not oraciones:
        return []
    primera = oraciones[0]
    if len(primera) > PRIMER_TROZO_MAX:
        piezas = [p.strip() for p in re.split(r"(?<=[,;:])\s+", primera) if p.strip()]
        juntas = []
        for p in piezas:
            if juntas and (len(juntas[-1]) < TROZO_MIN or len(p) < TROZO_MIN):
                juntas[-1] += " " + p
            else:
                juntas.append(p)
        oraciones[:1] = juntas
    return oraciones


# ---------- comprobaciones ----------

def sha256(ruta, bloque=1 << 22):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        while datos := f.read(bloque):
            h.update(datos)
    return h.hexdigest()


def verificar_hashes(carpeta=CARPETA, manifiesto=HASHES):
    """None si todo coincide; si no, el motivo."""
    try:
        esperado = json.loads(Path(manifiesto).read_text(encoding="utf-8"))["archivos"]
    except (OSError, ValueError, KeyError) as e:
        return f"sin manifiesto de hashes ({type(e).__name__})"
    for relativo, sha in esperado.items():
        ruta = Path(carpeta) / relativo
        if not ruta.is_file():
            return f"falta {relativo}"
        if sha256(ruta) != sha:
            return f"hash distinto en {relativo}"
    return None


def vram_libre_mib():
    s = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
    total, usada = (int(v) for v in s.strip().splitlines()[0].split(","))
    return total - usada


def vram_necesaria(perfil):
    """MiB libres que hacen falta antes de cargar el TTS, o None si el perfil no está medido."""
    extra = EXTRA_VISION_MIB.get(perfil)
    return None if extra is None else VRAM_TTS_MIB + extra + MARGEN_MIB


def comando(carpeta=CARPETA):
    c = Path(carpeta)
    return [str(c / "bin" / "tts_qwen_servidor.exe"), "-m", str(c / MODELO), "--mmproj", str(c / MMPROJ),
            "--tts-speaker-file", str(c / VOZ), "--tts-lang", "es", "-ngl", "99", "-c", "4096", "-n", "600",
            "--seed", "42", "--temp", "0.9", "--top-k", "50", "--top-p", "1.0", "--offline"]


# ---------- proceso hijo ----------

class FalloTTS(Exception):
    pass


class ProcesoTTS:
    """El servidor por tubería. Un pedido a la vez; si no responde a tiempo, se mata."""

    def __init__(self, cmd, espera_arranque=ESPERA_ARRANQUE_S, popen=subprocess.Popen):
        self.proc = popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          cwd=str(Path(cmd[0]).parent), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._respuestas = queue.Queue()
        self._lock = threading.Lock()
        self._n = 0
        self.tasa = None
        threading.Thread(target=self._leer, daemon=True).start()
        try:
            tipo, valor = self._respuestas.get(timeout=espera_arranque)
        except queue.Empty:
            self.matar()
            raise FalloTTS("no arrancó a tiempo")
        if tipo != "listo":
            self.matar()
            raise FalloTTS("terminó al arrancar")
        self.tasa = valor

    def _leer(self):
        salida = self.proc.stdout
        try:
            while True:
                cabecera = salida.readline()
                if not cabecera:
                    break
                partes = cabecera.decode("ascii", "replace").split()
                if partes[:1] == ["LISTO"]:
                    self._respuestas.put(("listo", int(partes[1])))
                elif partes[:1] == ["A"] and len(partes) == 4:
                    n = int(partes[2])
                    datos = b""
                    while len(datos) < 2 * n:
                        trozo = salida.read(2 * n - len(datos))
                        if not trozo:
                            raise EOFError
                        datos += trozo
                    self._respuestas.put(("audio", (partes[1], np.frombuffer(datos, dtype=np.int16), int(partes[3]))))
                elif partes[:1] == ["E"]:
                    self._respuestas.put(("error", (partes[1] if len(partes) > 1 else "",
                                                    " ".join(partes[2:]))))
        except (OSError, ValueError, EOFError):
            pass
        self._respuestas.put(("fin", None))

    def sintetizar(self, texto, tiempo_max):
        """Audio int16 del texto; FalloTTS si cae, da error o tarda más de tiempo_max (entonces se mata)."""
        with self._lock:
            self._n += 1
            ident = str(self._n)
            linea = texto.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()
            try:
                self.proc.stdin.write(f"{ident}\t{linea}\n".encode("utf-8"))
                self.proc.stdin.flush()
            except OSError:
                self.matar()
                raise FalloTTS("cayó")
            limite = time.monotonic() + tiempo_max
            while True:
                try:
                    tipo, valor = self._respuestas.get(timeout=max(0.0, limite - time.monotonic()))
                except queue.Empty:
                    self.matar()
                    raise FalloTTS(f"sin respuesta en {tiempo_max:.1f} s")
                if tipo == "fin":
                    self.matar()
                    raise FalloTTS("cayó")
                if tipo == "error" and valor[0] == ident:
                    raise FalloTTS(f"error: {valor[1]}")
                if tipo == "audio" and valor[0] == ident:
                    return valor[1]

    def vivo(self):
        return self.proc.poll() is None

    def matar(self):
        try:
            self.proc.kill()
        except OSError:
            pass
        try:
            self.proc.wait(5)
        except Exception:
            pass

    def cerrar(self):
        try:
            self.proc.stdin.write(b"SALIR\n")
            self.proc.stdin.flush()
            self.proc.wait(5)
        except Exception:
            pass
        self.matar()


def tiempo_maximo(texto):
    """Más que esto por trozo = va lento (más despacio que el habla, ~0,065 s de audio por carácter)."""
    return 3.0 + 0.08 * len(texto)


# ---------- locutor ----------

class LocutorQwen:
    """La interfaz de voz.Locutor; Piper (el locutor que recibe) es el respaldo."""

    TROZO_S = 0.1

    def __init__(self, piper, perfil, carpeta=CARPETA, manifiesto=HASHES, crear_salida=None, crear_proceso=None,
                 libre=vram_libre_mib, juego=None, avisar=print):
        self.piper, self.perfil, self.carpeta, self.manifiesto = piper, perfil, Path(carpeta), manifiesto
        self.voz = piper.voz  # voz.preparar() calienta Piper con locutor.voz.synthesize
        self._crear_salida = crear_salida or self._salida_sd
        self._crear_proceso = crear_proceso or (lambda: ProcesoTTS(comando(self.carpeta)))
        self._libre, self._juego, self.avisar = libre, juego, avisar
        self.estado, self.motivo = "piper", "sin iniciar"
        self.proceso, self._salida, self.tasa = None, None, piper.tasa
        self.rearranques, self.eventos = 0, []
        self.ultimo_motor = "piper"  # quién dijo la última respuesta (voz.py lo anota en el registro)
        self._callar = threading.Event()
        self._hilo = None
        self._carga = None
        self._mutex = threading.Lock()

    @staticmethod
    def _salida_sd(tasa):
        import sounddevice as sd
        s = sd.OutputStream(samplerate=tasa, channels=1, dtype="int16")
        s.start()
        return s

    @property
    def salida(self):
        return self._salida if self.estado == "activo" and self._salida is not None else self.piper.salida

    def anotar(self, evento, detalle=""):
        self.eventos.append({"hora": time.strftime("%H:%M:%S"), "evento": evento, "detalle": detalle})
        self.avisar(f"  [voz qwen3] {evento}{': ' + detalle if detalle else ''}")

    # --- carga ---

    def iniciar(self):
        """Comprueba y carga en un hilo; mientras tanto (y si algo falla) habla Piper."""
        self.estado, self.motivo = "cargando", ""
        self._carga = threading.Thread(target=self._cargar, daemon=True)
        self._carga.start()

    def esperar_carga(self, segundos=None):
        if self._carga is not None:
            self._carga.join(segundos)

    def _a_piper(self, motivo):
        with self._mutex:
            self.estado, self.motivo = "piper", motivo
        self.anotar("Piper", motivo)

    def _cargar(self):
        fallo = verificar_hashes(self.carpeta, self.manifiesto)
        if fallo:
            return self._a_piper(fallo)
        juego = self._juego() if self._juego else self._juego_abierto()
        if juego:
            return self._a_piper(f"{juego} está abierto: no cargo el TTS en la GPU")
        necesaria = vram_necesaria(self.perfil)
        if necesaria is None:
            return self._a_piper(f"perfil {self.perfil} sin medir: el TTS no cabe junto a su visión")
        try:
            libre = self._libre()
        except Exception as e:
            return self._a_piper(f"no pude medir la VRAM ({type(e).__name__})")
        if libre < necesaria:
            return self._a_piper(f"VRAM libre {libre} MiB < {necesaria} MiB")
        self._arrancar()

    @staticmethod
    def _juego_abierto():
        from guardia_juego import juego_abierto
        return juego_abierto()

    def _arrancar(self):
        try:
            proceso = self._crear_proceso()
            if self._salida is None or self.tasa != proceso.tasa:
                self._salida = self._crear_salida(proceso.tasa)
            with self._mutex:
                if self.estado == "descargado":  # el modo juego llegó mientras cargaba
                    proceso.cerrar()
                    return
                self.proceso, self.tasa = proceso, proceso.tasa
                self.estado, self.motivo = "activo", ""
            self.anotar("activo")
        except Exception as e:
            self._a_piper(f"no arrancó ({e})")

    def _fallo(self, motivo):
        """Cayó, se colgó o fue lento: Piper ahora; rearranque en segundo plano hasta MAX_REARRANQUES."""
        with self._mutex:
            proceso, self.proceso = self.proceso, None
            if self.estado != "activo":
                return
            self.estado = "piper"
        if proceso is not None:
            proceso.matar()
        if self.rearranques >= MAX_REARRANQUES:
            self.motivo = f"{motivo}; sin más rearranques ({MAX_REARRANQUES})"
            self.anotar("fallo", self.motivo)
            return
        self.rearranques += 1
        self.motivo = motivo
        self.anotar("fallo", f"{motivo}; rearranque {self.rearranques}/{MAX_REARRANQUES}")
        self.estado = "cargando"
        self._carga = threading.Thread(target=self._cargar, daemon=True)  # con guardia_juego y VRAM otra vez
        self._carga.start()

    def descargar(self):
        """Modo juego: libera la GPU; la pausa sigue con Piper en la CPU."""
        self.callar()
        with self._mutex:
            proceso, self.proceso = self.proceso, None
            self.estado, self.motivo = "descargado", "modo juego"
        if proceso is not None:
            proceso.cerrar()

    def cargar(self):
        """Fin del modo juego (después del LLM y de Whisper): vuelve a comprobarlo todo."""
        self.iniciar()

    def cerrar(self):
        self.descargar()

    # --- habla ---

    def hablar(self, texto, al_empezar=None, cortar=lambda: False):
        self.callar()
        self._callar.clear()
        if self.estado != "activo":
            self.ultimo_motor = "piper"
            return self.piper.hablar(texto, al_empezar, cortar)
        self.ultimo_motor = "qwen3"
        self._hilo = threading.Thread(target=self._decir, args=(texto, al_empezar, cortar), daemon=True)
        self._hilo.start()

    def _decir(self, texto, al_empezar, cortar):
        trozos = partir(texto)
        listos = queue.Queue(maxsize=2)
        parar = lambda: self._callar.is_set() or cortar()
        proceso = self.proceso

        def sintetizar():
            for i, trozo in enumerate(trozos):
                if parar():
                    break
                try:
                    t = time.perf_counter()
                    audio = proceso.sintetizar(normalizar_texto(trozo), tiempo_maximo(trozo))
                    listos.put((i, audio, time.perf_counter() - t))
                except FalloTTS as e:
                    listos.put((i, e, None))
                    return
            listos.put(None)

        threading.Thread(target=sintetizar, daemon=True).start()
        estado = {"al_empezar": al_empezar}

        def empezar():
            if estado["al_empezar"]:
                estado["al_empezar"](time.perf_counter())
                estado["al_empezar"] = None

        while True:
            if parar():
                return
            item = listos.get()
            if item is None:
                return
            i, audio, _ = item
            if isinstance(audio, FalloTTS):
                self.ultimo_motor = "qwen3+piper" if i else "piper"
                self._fallo(str(audio))
                resto = " ".join(trozos[i:])
                if not parar():  # el resto de esta respuesta lo dice Piper
                    self.piper._callar.clear()
                    self.piper._decir(resto, estado["al_empezar"], parar)
                return
            n = int(self.tasa * self.TROZO_S)
            for j in range(0, len(audio), n):
                if parar():
                    return
                empezar()
                self._salida.write(audio[j:j + n])

    def callar(self):
        self._callar.set()
        if self._hilo is not None:
            self._hilo.join(2)
        self.piper.callar()

    def hablando(self):
        return (self._hilo is not None and self._hilo.is_alive()) or self.piper.hablando()


def crear_locutor(piper, config_voz, config):
    """Piper (por defecto) o LocutorQwen según config.json -> voz.tts_motor. Sin iniciar: lo inicia voz.preparar()."""
    if config_voz.get("tts_motor", "piper") != "qwen3":
        return piper
    return LocutorQwen(piper, config.get("modelo_activo"))
