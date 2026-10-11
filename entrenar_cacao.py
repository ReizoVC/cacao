"""
Entrena y mide el detector de la palabra "Cacao" (palabra_activacion.py). Todo local y en la CPU.

1. Datos sintéticos con Piper (voces en español de D:/Cacao/entrenamiento/piper_cacao y modelos/piper):
   - positivos: "Cacao" con cada voz y hablante, a varias velocidades y variaciones, colocada al final de una ventana
     de 2 s sobre ruido, con reverberación y volumen al azar;
   - negativos: frases en español sin "cacao" (órdenes, charla, números) y palabras parecidas ("caso", "Macao",
     "cacahuate", "Caracas"...), ruido y música sintética, y las grabaciones reales de voz_registro/ (tu voz).
   - negativos reales: una parte (los primeros 1,2 GB, ~390 000 ventanas) de las características que publica
     openWakeWord de ~2000 h de audio real (ACAV100M: habla, música, ruido), en D:/Cacao/entrenamiento/cacao/acav_parcial.npy;
   - el ruido de fondo real de tu micrófono (los silencios de voz_registro/) se mezcla con los positivos.
2. Características de openWakeWord (16 tramas x 96) y un MLP pequeño (scikit-learn) encima, con una segunda ronda
   que añade los negativos reales que más se parecen a la palabra.
3. Medición con voces que NO se usaron al entrenar (es_AR-daniela-high y es_MX-claude-high) y frases nuevas:
   detección de "Cacao" (sola y dicha de corrido con la orden), activaciones falsas por hora en conversación, en
   frases que mencionan "cacao" de pasada y con audio de fondo, en tus grabaciones de voz_pruebas/ y en las
   ~11 h del conjunto de validación de openWakeWord (D:/Cacao/entrenamiento/cacao/validation_set_features.npy).
Sale modelos/cacao/cacao.npz y resultados_cacao.json.

Con --reales se añaden las grabaciones de Reizo de voz_pruebas/cacao_real (grabar_cacao.py): dos tercios de cada
categoría entrenan (la palabra sola, con REPETICIONES_REAL variaciones de ruido, eco, volumen y tono; las palabras
parecidas como negativos; "de corrido" no, porque no se sabe dónde acaba la palabra) y el tercio restante, que el
modelo no ve, se mide en 'reales_prueba'. --salida NOMBRE guarda en modelos/cacao/NOMBRE.npz (sin tocar cacao.npz).

Uso: .venv\\Scripts\\python entrenar_cacao.py [--palabra "oye cacao"] [--reales] [--salida cacao_v4]
"""
import json
import sys
import time
import wave
from pathlib import Path

import numpy as np
from piper import PiperVoice, SynthesisConfig
from scipy.signal import fftconvolve

import palabra_activacion as pa

BASE = Path(__file__).parent
# datos que solo usa el entrenamiento: en el disco D (D:\Cacao\manifiesto_movimientos.md)
ENTRENAMIENTO = Path(r"D:\Cacao\entrenamiento")
RNG = np.random.default_rng(7)
PRUEBA = {"es_AR-daniela-high", "es_MX-claude-high"}  # voces que no se usan al entrenar

PALABRA = "cacao"
if "--palabra" in sys.argv:
    PALABRA = sys.argv[sys.argv.index("--palabra") + 1].lower()
NOMBRE = PALABRA.replace(" ", "_")
REALES = "--reales" in sys.argv
SALIDA = sys.argv[sys.argv.index("--salida") + 1] if "--salida" in sys.argv else NOMBRE
CARPETA_REALES = BASE / "voz_pruebas" / "cacao_real"
REPETICIONES_REAL = 30


def dividir_reales():
    """(entrenamiento, prueba): listas de (archivo, categoría, audio). La prueba es una toma de cada tres de cada
    categoría (la 3.ª, 6.ª...), siempre las mismas; 'de corrido' va entera a la prueba."""
    indice = json.loads((CARPETA_REALES / "indice.json").read_text(encoding="utf-8"))
    entrenamiento, prueba = [], []
    por_cat = {}
    for x in indice:
        por_cat.setdefault(x["categoria"], []).append(x)
    for cat, tomas in por_cat.items():
        for i, x in enumerate(sorted(tomas, key=lambda t: t["archivo"]), 1):
            fila = (x["archivo"], cat, leer_wav(CARPETA_REALES / x["archivo"]))
            (prueba if cat == "de_corrido" or i % 3 == 0 else entrenamiento).append(fila)
    return entrenamiento, prueba
TEXTOS_POSITIVOS = {"cacao": ["Cacao", "Cacao.", "¡Cacao!", "Cacao,", "¿Cacao?"],
                    "oye cacao": ["Oye, Cacao", "Oye Cacao.", "¡Oye, Cacao!", "Oye Cacao,"]}[PALABRA]
PARECIDAS = ["caso", "acaso", "Macao", "cacahuate", "caca", "Caracas", "cacatúa", "Callao", "cazo", "ocaso",
             "Picasso", "Cancún", "cacería", "cacique", "chao", "caos", "cacho", "caucho", "cajón", "casado",
             "taco", "Tacna", "macaco", "kayak", "cacerola", "Lucas", "cálido", "cacarear", "cómo", "oye",
             "vacas", "acá", "ciao", "Cascos", "cacto", "Cora", "tacaño", "cacharro", "Calcuta", "Bacalao"]

ORDENES = ["sube el volumen", "baja el volumen", "abre Spotify", "abre la calculadora", "cierra el bloc de notas",
           "qué hora es", "pon música", "busca el clima de mañana", "qué ventanas tengo abiertas",
           "mueve el archivo a descargas", "silencia el audio", "abre el navegador", "pausa la música",
           "ya terminé", "estoy jugando", "escribe hola en el bloc de notas", "confirmo la instrucción"]
FRASES_ENTRENAMIENTO = [
    "Hoy hace un día muy bonito para salir a caminar.", "Mañana tengo clase a las ocho de la mañana.",
    "¿Me pasas la sal, por favor?", "El partido terminó dos a uno.", "Voy a preparar el almuerzo.",
    "No encuentro las llaves de la casa.", "Mi hermana llega el fin de semana.", "El tráfico estaba horrible.",
    "Tengo que entregar el informe el viernes.", "¿Viste la película que te recomendé?",
    "La reunión empieza en diez minutos.", "Compré pan, leche y huevos.", "Está lloviendo otra vez.",
    "El caso es que no tengo tiempo.", "Acaso no lo sabías.", "Viajamos a Caracas el año pasado.",
    "En Macao hay muchos casinos.", "Me encanta el cacahuate salado.", "El Callao queda cerca de Lima.",
    "Puse el cazo al fuego.", "El ocaso se veía naranja.", "Picasso pintó el Guernica.", "Fuimos a Cancún de vacaciones.",
    "El cacique habló con la comunidad.", "Esto es un caos total.", "Las vacas están en el campo.",
    "Ven acá un momento.", "Chao, nos vemos mañana.", "Oye, ¿me ayudas con esto?", "Oye, qué buena canción.",
    "Uno, dos, tres, cuatro, cinco, seis, siete, ocho.", "El número es nueve siete tres dos.",
    "Necesito comprar un cargador para el celular.", "La computadora está muy lenta hoy.",
    "¿Cuánto cuesta el pasaje a Arequipa?", "Me duele un poco la cabeza.", "El gato se subió al techo.",
    "Estamos jugando en línea con mis amigos.", "Ya casi termino la tarea.", "Llámame cuando llegues.",
    "El taco de pastor estaba delicioso.", "Tacna está al sur del Perú.", "Ese kayak es muy caro.",
    "La cacerola está en el armario.", "Lucas no vino a la reunión.", "El agua está tibia.",
    "Coca y café para el desayuno.", "Esa cacatúa habla mucho.", "El macaco saltó del árbol.",
    "Qué calor hace en verano.", "Hay que cargar la batería del auto.", "Cuidado con el escalón.",
    "La clase de cálculo fue difícil.", "Mi casa es tu casa.", "Cada quien con lo suyo.", "Quedamos a las cuatro.",
] + [f"{a} {o}." for a in ("Oye,", "Por favor,", "Ahora", "Luego") for o in ORDENES]
FRASES_PRUEBA = [
    "El colegio cierra temprano los viernes.", "Necesito revisar el correo antes de salir.",
    "Ayer fuimos al cine con mis primos.", "La pizza llegó fría otra vez.", "Hay que lavar los platos.",
    "Ese caso fue muy famoso en las noticias.", "Macao y Hong Kong están cerca.", "El cacao no.",
    "Me compré una casaca nueva.", "Cada cosa a su tiempo.", "El concierto fue increíble.",
    "¿Qué vamos a cenar hoy?", "La batería del celular está al diez por ciento.", "Mi perro se llama Toby.",
    "El examen es la próxima semana.", "Oye, pásame el control remoto.", "Oye, ¿ya comiste?",
    "Vamos a jugar una partida más.", "Tengo sueño, me voy a dormir.", "La tienda abre a las nueve.",
    "Pon la música más fuerte.", "Abre la ventana, hace calor.", "Cierra la puerta al salir.",
    "Dos más dos son cuatro.", "El tren llega a las tres y cuarto.", "Qué caos hay en la avenida.",
    "El cacique de la tribu.", "Compramos cacahuates para la fiesta.", "Caracas es la capital de Venezuela.",
    "El ocaso en la playa es precioso.",
]
FRASES_MENCION = ["Me encanta el chocolate con mucho cacao.", "El cacao peruano es de los mejores del mundo.",
                  "Compré manteca de cacao para los labios.", "Esta barra tiene setenta por ciento de cacao.",
                  "Mi abuelo cultivaba cacao en la selva.", "¿Le pusiste cacao al pastel?",
                  "El precio del cacao subió este año.", "Una taza de cacao caliente, por favor.",
                  "Vimos un documental sobre el cacao.", "Los granos de cacao se fermentan primero."]
DE_CORRIDO = ["Cacao, sube el volumen.", "Cacao sube el volumen.", "Cacao, abre Spotify.",
              "Cacao, ¿qué hora es?", "Cacao, ya terminé.", "Oye, Cacao, pon música."]


# ---------- audio ----------

def cargar_voces():
    voces = []
    for carpeta in (ENTRENAMIENTO / "piper_cacao", BASE / "modelos" / "piper"):
        for onnx in sorted(carpeta.glob("*.onnx")):
            voz = PiperVoice.load(str(onnx))
            voces.append((onnx.stem, voz, max(1, int(voz.config.num_speakers or 1))))
    return voces


def sintetizar(voz, texto, sid=0, largo=1.0, ruido=0.667, ruido_w=0.8):
    cfg = SynthesisConfig(speaker_id=sid if voz.config.num_speakers and voz.config.num_speakers > 1 else None,
                          length_scale=largo, noise_scale=ruido, noise_w_scale=ruido_w)
    audio = np.concatenate([np.frombuffer(t.audio_int16_bytes, dtype=np.int16) for t in voz.synthesize(texto, syn_config=cfg)])
    return pa.a_16k(audio, voz.config.sample_rate)


def recortar(x, umbral=400):
    idx = np.flatnonzero(np.abs(x) > umbral)
    return x[idx[0]:idx[-1] + 1] if len(idx) else x


def ruido(n, tipo=None):
    tipo = tipo or RNG.choice(["blanco", "rosa", "marron", "zumbido", "silencio"])
    if tipo == "silencio":
        return RNG.normal(0, 3, n)
    blanco = RNG.normal(0, 1, n)
    if tipo == "blanco":
        y = blanco
    elif tipo == "rosa":
        f = np.fft.rfft(blanco)
        f /= np.sqrt(np.maximum(np.arange(len(f)), 1))
        y = np.fft.irfft(f, n)
    elif tipo == "marron":
        y = np.cumsum(blanco)
        y -= np.convolve(y, np.ones(400) / 400, mode="same")
    else:
        t = np.arange(n) / pa.TASA
        y = np.sin(2 * np.pi * 50 * t) + 0.3 * np.sin(2 * np.pi * 150 * t) + 0.05 * blanco
    return y / (np.std(y) + 1e-9)


def musica(n):
    """Acordes y percusión sintéticos (no hay música real en el PC que se pueda usar)."""
    t = np.arange(n) / pa.TASA
    y = np.zeros(n)
    paso = int(0.5 * pa.TASA)
    for i in range(0, n, paso):
        base = 110 * 2 ** (RNG.integers(0, 12) / 12)
        for k in (1, 1.25, 1.5, 2):
            y[i:i + paso] += np.sin(2 * np.pi * base * k * t[i:i + paso]) * np.exp(-np.arange(min(paso, n - i)) / paso * 2)
        y[i:i + 200] += RNG.normal(0, 3, min(200, n - i))
    return y / (np.std(y) + 1e-9)


def otra_voz(x):
    """Hablante "nuevo": cambia tono y velocidad juntos (remuestreo), para no aprender solo 9 voces."""
    if RNG.random() < 0.4:
        return x
    from scipy.signal import resample
    f = RNG.uniform(0.86, 1.14)
    return resample(x.astype(np.float64), int(len(x) * f)).astype(np.float64)


def reverberar(x):
    if RNG.random() < 0.5:
        return x
    rt = RNG.uniform(0.15, 0.6)
    largo = int(rt * pa.TASA)
    ir = RNG.normal(0, 1, largo) * np.exp(-6.9 * np.arange(largo) / largo)
    ir[0] = 1.0
    y = fftconvolve(x.astype(np.float32), ir / np.sqrt((ir ** 2).sum()))[:len(x)]
    return y * (np.std(x) / (np.std(y) + 1e-9))


def mezclar(voz_audio, fondo, snr_db):
    v = voz_audio.astype(np.float64)
    potencia = np.sqrt(np.mean(v[np.abs(v) > 300] ** 2)) if np.any(np.abs(v) > 300) else 1000
    return v + fondo * potencia / (10 ** (snr_db / 20))


def a_int16(x, ganancia=1.0):
    return np.clip(x * ganancia, -32768, 32767).astype(np.int16)


RUIDO_REAL = None  # silencios de tus grabaciones (el ruido de fondo real del micrófono)


def ruido_real(n):
    if RUIDO_REAL is None or len(RUIDO_REAL) < n:
        return ruido(n)
    i = RNG.integers(0, len(RUIDO_REAL) - n)
    y = RUIDO_REAL[i:i + n].astype(np.float64)
    return y / (np.std(y) + 1e-9)


def ventana_con_palabra(palabra, total_s=2.0):
    """La palabra termina entre 1,72 y 1,96 s de una ventana de 2 s (donde la busca el clasificador)."""
    n = int(total_s * pa.TASA)
    fin = int(RNG.uniform(1.72, 1.96) * pa.TASA)
    palabra = reverberar(palabra)[: fin]
    x = np.zeros(n)
    x[fin - len(palabra):fin] = palabra
    eleccion = RNG.random()
    fondo = ruido_real(n) if eleccion < 0.45 else ruido(n) if eleccion < 0.85 else musica(n)
    return a_int16(mezclar(x, fondo, RNG.uniform(5, 30)), RNG.uniform(0.3, 1.6))


def silencios(audio, umbral=250):
    """Las tramas de 30 ms sin voz de un audio, unidas."""
    n = len(audio) // 480 * 480
    tramas = audio[:n].reshape(-1, 480)
    rms = np.sqrt((tramas.astype(np.float64) ** 2).mean(axis=1))
    return tramas[rms < umbral].reshape(-1)


def leer_wav(ruta):
    with wave.open(str(ruta)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        return pa.a_16k(x, w.getframerate())


# ---------- características ----------

_F = None


def features():
    global _F
    if _F is None:
        from openwakeword.utils import AudioFeatures
        _F = AudioFeatures(inference_framework="onnx", ncpu=4)
    return _F


def embeddings_clips(clips):
    return features().embed_clips(np.stack(clips), batch_size=64, ncpu=4)[:, -pa.TRAMAS:, :]


def ventanas_largas(audio, paso=2):
    """Todas las ventanas de 16 tramas de un audio largo (trozos de 60 s para no gastar memoria)."""
    salida = []
    trozo = 60 * pa.TASA
    for i in range(0, len(audio), trozo):
        x = audio[i:i + trozo + 2 * pa.TASA]
        if len(x) < 2 * pa.TASA:
            break
        e = features()._get_embeddings(x)
        for j in range(pa.TRAMAS, len(e) + 1, paso):
            salida.append(e[j - pa.TRAMAS:j])
    return salida


def flujo(partes, pausa=(0.3, 1.2), fondo_snr=None):
    """Une audios con silencios al azar y, si se pide, ruido de fondo."""
    trozos = []
    for p in partes:
        trozos.append(p.astype(np.float64))
        trozos.append(np.zeros(int(RNG.uniform(*pausa) * pa.TASA)))
    x = np.concatenate(trozos)
    if fondo_snr is not None:
        x = mezclar(x, ruido(len(x)) if RNG.random() < 0.6 else musica(len(x)), fondo_snr)
    return a_int16(x)


# ---------- datos ----------

def datos(voces):
    global RUIDO_REAL
    pos, neg_clips, neg_largos = [], [], []
    registro = [leer_wav(w) for w in sorted((BASE / "voz_registro").glob("*.wav"))]
    if registro:
        RUIDO_REAL = np.concatenate([silencios(x) for x in registro])
        print(f"  ruido real del micrófono: {len(RUIDO_REAL) / pa.TASA:.1f} s", flush=True)
    entrenamiento = [(n, v, s) for n, v, s in voces if n not in PRUEBA]
    for nombre, voz, hablantes in entrenamiento:
        for sid in range(min(hablantes, 4)):
            for largo in (0.75, 0.85, 1.0, 1.15, 1.3):
                for r in (0.4, 0.667, 0.9):
                    for texto in TEXTOS_POSITIVOS:
                        palabra = recortar(sintetizar(voz, texto, sid, largo * RNG.uniform(0.95, 1.05), r,
                                                      RNG.uniform(0.6, 1.0)))
                        for _ in range(2):
                            pos.append(ventana_con_palabra(otra_voz(palabra)))
                # de corrido: "Cacao, sube el volumen" cortado donde acaba la palabra (su duración sola, igual config)
                if PALABRA == "cacao":
                    sola = len(recortar(sintetizar(voz, "Cacao", sid, largo, 0.667, 0.8)))
                    for orden in RNG.choice(ORDENES, size=4, replace=False):
                        frase = recortar(sintetizar(voz, f"Cacao{RNG.choice([',', ''])} {orden}.", sid, largo, 0.667, 0.8))
                        corte = int(sola + RNG.uniform(-0.04, 0.06) * pa.TASA)
                        for _ in range(2):
                            pos.append(ventana_con_palabra(otra_voz(frase[:corte])))
            for largo in (0.85, 1.0, 1.2):
                for texto in PARECIDAS:
                    neg_clips.append(ventana_con_palabra(otra_voz(recortar(sintetizar(voz, texto, sid, largo)))))
            for _ in range(2):  # dos pasadas: la segunda con otro tono
                frases = [otra_voz(sintetizar(voz, f, sid, RNG.uniform(0.85, 1.2))) for f in FRASES_ENTRENAMIENTO]
                neg_largos.append(flujo(frases, fondo_snr=RNG.uniform(10, 30)))
        print(f"  voz {nombre}: {len(pos)} positivos, {len(neg_clips)} negativos cortos", flush=True)
    if REALES:
        entrenamiento, _ = dividir_reales()
        for _, cat, audio in entrenamiento:
            palabra = recortar(audio, umbral=700)
            destino = neg_clips if cat == "parecida" else pos
            for _ in range(REPETICIONES_REAL if cat != "parecida" else REPETICIONES_REAL // 2):
                destino.append(ventana_con_palabra(otra_voz(palabra)))
        print(f"  tus grabaciones: {sum(c != 'parecida' for _, c, _ in entrenamiento)} positivas y "
              f"{sum(c == 'parecida' for _, c, _ in entrenamiento)} parecidas para entrenar", flush=True)
    if registro:
        neg_largos.append(flujo(registro))
    neg_largos.append(a_int16(ruido(5 * 60 * pa.TASA, "blanco") * 300))
    neg_largos.append(a_int16(musica(5 * 60 * pa.TASA) * 2000))
    return pos, neg_clips, neg_largos


# ---------- entrenamiento ----------

ACAV = ENTRENAMIENTO / "cacao" / "acav_parcial.npy"
VALIDACION = ENTRENAMIENTO / "cacao" / "validation_set_features.npy"


def acav():
    """Ventanas (N, 16, 96) reales de openWakeWord (descarga parcial: se leen solo las completas)."""
    if not ACAV.exists():
        return np.zeros((0, pa.TRAMAS, 96), np.float16)
    n = (ACAV.stat().st_size - 128) // (pa.TRAMAS * 96 * 2)
    return np.memmap(ACAV, dtype=np.float16, mode="r", offset=128, shape=(n, pa.TRAMAS, 96))


def validacion_fp(modelo, umbral, paciencia):
    """Activaciones falsas por hora en las ~11 h del conjunto de validación (tramas seguidas de 80 ms)."""
    if not VALIDACION.exists():
        return None
    v = np.load(VALIDACION, mmap_mode="r")
    probs = []
    for i in range(0, len(v) - pa.TRAMAS, 20000):
        trozo = np.asarray(v[i:i + 20000 + pa.TRAMAS - 1], dtype=np.float32)
        idx = np.arange(pa.TRAMAS)[None, :] + np.arange(len(trozo) - pa.TRAMAS + 1)[:, None]
        probs.append(modelo.probabilidad(trozo[idx]))
    p = np.concatenate(probs)
    activaciones, racha, pausa = 0, 0, 0
    for x in p >= umbral:
        if pausa:
            pausa -= 1
            continue
        racha = racha + 1 if x else 0
        if racha >= paciencia:
            activaciones, racha, pausa = activaciones + 1, 0, 25  # 2 s sin volver a activar
    horas = len(v) * 0.08 / 3600
    return {"horas": round(horas, 1), "activaciones": activaciones, "por_hora": round(activaciones / horas, 2)}


def entrenar(x_pos, x_neg):
    from sklearn.neural_network import MLPClassifier
    x = np.concatenate([x_pos, x_neg]).reshape(len(x_pos) + len(x_neg), -1)
    y = np.concatenate([np.ones(len(x_pos)), np.zeros(len(x_neg))])
    repetir = max(1, len(x_neg) // (3 * len(x_pos)))  # positivos repetidos para equilibrar
    x = np.concatenate([x] + [x[: len(x_pos)]] * (repetir - 1))
    y = np.concatenate([y] + [np.ones(len(x_pos))] * (repetir - 1))
    media, escala = x.mean(axis=0), x.std(axis=0) + 1e-6
    mlp = MLPClassifier(hidden_layer_sizes=(128, 64), alpha=1e-3, batch_size=512, learning_rate_init=1e-3,
                        max_iter=40, early_stopping=True, validation_fraction=0.1, random_state=0)
    mlp.fit((x - media) / escala, y)
    return mlp, media, escala


def guardar(mlp, media, escala, umbral, paciencia, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    capas = {}
    for i, (w, b) in enumerate(zip(mlp.coefs_, mlp.intercepts_), 1):
        capas[f"W{i}"], capas[f"b{i}"] = w.astype(np.float32), b.astype(np.float32)
    np.savez(ruta, media=media.astype(np.float32), escala=escala.astype(np.float32), umbral=umbral,
             paciencia=paciencia, **capas)


# ---------- medición (streaming, como en el PC) ----------

def detecciones(modelo, audio, umbral, paciencia):
    """Momentos (s) de las detecciones al pasar el audio en trozos de 80 ms, con 2 s de pausa tras cada una."""
    d = pa.Detector(modelo, umbral, paciencia)
    momentos, n = [], 0
    for i in range(0, len(audio) - pa.TROZO + 1, pa.TROZO):
        if d.procesar(audio[i:i + pa.TROZO]):
            momentos.append(i / pa.TASA)
            d.reiniciar()
            d._racha = -int(2 * pa.TASA / pa.TROZO)
    return momentos


def medir(modelo, umbral, paciencia, voces_prueba):
    global RNG
    RNG = np.random.default_rng(11)  # el mismo audio de prueba para todos los umbrales
    r = {"umbral": umbral, "paciencia": paciencia}
    # 1) "Cacao" sola y de corrido con la orden, voces de prueba, con y sin ruido de fondo
    aciertos, total = 0, 0
    de_corrido_ok, de_corrido_total = 0, 0
    for _, voz, hablantes in voces_prueba:
        for largo in (0.85, 1.0, 1.2):
            for snr in (None, 20, 10):
                for texto in TEXTOS_POSITIVOS[:3]:
                    a = flujo([np.zeros(pa.TASA, np.int16), sintetizar(voz, texto, 0, largo)], fondo_snr=snr)
                    aciertos += bool(detecciones(modelo, a, umbral, paciencia))
                    total += 1
                if PALABRA == "cacao":
                    for texto in DE_CORRIDO:
                        a = flujo([np.zeros(pa.TASA, np.int16), sintetizar(voz, texto, 0, largo)], fondo_snr=snr)
                        de_corrido_ok += bool(detecciones(modelo, a, umbral, paciencia))
                        de_corrido_total += 1
    r["deteccion_sola"] = {"aciertos": aciertos, "total": total}
    if de_corrido_total:
        r["deteccion_de_corrido"] = {"aciertos": de_corrido_ok, "total": de_corrido_total}
    # 2) conversación sin la palabra (frases nuevas, voces de prueba)
    conversacion = flujo([sintetizar(voz, f, 0, RNG.uniform(0.85, 1.2)) for _, voz, _ in voces_prueba
                          for _ in range(3) for f in FRASES_PRUEBA], fondo_snr=25)
    fp = detecciones(modelo, conversacion, umbral, paciencia)
    horas = len(conversacion) / pa.TASA / 3600
    r["conversacion_sin_cacao"] = {"minutos": round(horas * 60, 1), "activaciones": len(fp),
                                   "por_hora": round(len(fp) / horas, 2)}
    # 3) frases que mencionan "cacao" de pasada (no son órdenes)
    activadas, total = 0, 0
    for _, voz, _ in voces_prueba:
        for f in FRASES_MENCION:
            a = flujo([np.zeros(pa.TASA, np.int16), sintetizar(voz, f, 0, RNG.uniform(0.9, 1.1))])
            activadas += bool(detecciones(modelo, a, umbral, paciencia))
            total += 1
    r["menciones_de_cacao"] = {"activadas": activadas, "total": total}
    # 4) solo audio de fondo (ruido y música sintética)
    fondo = np.concatenate([a_int16(ruido(5 * 60 * pa.TASA) * RNG.uniform(200, 3000)), a_int16(musica(10 * 60 * pa.TASA) * 3000)])
    fp = detecciones(modelo, fondo, umbral, paciencia)
    r["audio_de_fondo"] = {"minutos": round(len(fondo) / pa.TASA / 60, 1), "activaciones": len(fp)}
    r["validacion_openwakeword"] = validacion_fp(modelo, umbral, paciencia)
    if REALES:  # tus grabaciones que el modelo no vio (1 s de silencio antes, como en la escucha real)
        _, prueba = dividir_reales()
        pos_ok = [bool(detecciones(modelo, np.concatenate([np.zeros(pa.TASA, np.int16), a, np.zeros(pa.TASA // 2, np.int16)]), umbral, paciencia))
                  for _, c, a in prueba if c != "parecida"]
        neg_ok = [bool(detecciones(modelo, np.concatenate([np.zeros(pa.TASA, np.int16), a, np.zeros(pa.TASA // 2, np.int16)]), umbral, paciencia))
                  for _, c, a in prueba if c == "parecida"]
        r["reales_prueba"] = {"detectadas": sum(pos_ok), "total": len(pos_ok),
                              "parecidas_activadas": sum(neg_ok), "parecidas": len(neg_ok)}
    # 5) tus grabaciones de voz_pruebas (no se usaron al entrenar)
    wavs = sorted((BASE / "voz_pruebas").glob("*.wav"))
    if wavs:
        tuyas = flujo([leer_wav(w) for w in wavs])
        fp = detecciones(modelo, tuyas, umbral, paciencia)
        r["tus_grabaciones"] = {"archivos": len(wavs), "minutos": round(len(tuyas) / pa.TASA / 60, 1),
                                "activaciones": len(fp)}
    return r


def main():
    t0 = time.time()
    print(f"Palabra: «{PALABRA}». Cargando voces de Piper (CPU)...", flush=True)
    voces = cargar_voces()
    print("Voces:", ", ".join(f"{n} ({s} hablantes)" for n, _, s in voces), flush=True)
    pos, neg_clips, neg_largos = datos(voces)
    print(f"Datos: {len(pos)} ventanas con la palabra, {len(neg_clips)} con palabras parecidas, "
          f"{sum(len(x) for x in neg_largos) / pa.TASA / 60:.1f} min de audio sin ella "
          f"({time.time() - t0:.0f} s)", flush=True)
    x_pos = embeddings_clips(pos)
    x_neg = np.concatenate([embeddings_clips(neg_clips), np.array([v for a in neg_largos for v in ventanas_largas(a)])])
    reales = acav()
    elegidas = RNG.choice(len(reales), size=min(200000, len(reales)), replace=False) if len(reales) else []
    x_real = np.asarray(reales[np.sort(elegidas)], dtype=np.float32) if len(reales) else np.zeros((0, 16, 96))
    print(f"Características: {len(x_pos)} positivas, {len(x_neg)} negativas sintéticas, {len(x_real)} negativas "
          f"reales ({time.time() - t0:.0f} s)", flush=True)
    mlp, media, escala = entrenar(x_pos, np.concatenate([x_neg, x_real]))
    # segunda ronda: los negativos reales que el modelo confunde con la palabra
    dificiles = np.zeros((0, pa.TRAMAS, 96), np.float32)
    for ronda in (2, 3):
        if not len(reales):
            break
        ruta_tmp = BASE / "modelos" / "cacao" / "_ronda.npz"
        guardar(mlp, media, escala, 0.5, 2, ruta_tmp)
        m1 = pa.ModeloCacao(ruta_tmp)
        nuevos = []
        for i in range(0, len(reales), 20000):
            trozo = np.asarray(reales[i:i + 20000], dtype=np.float32)
            nuevos.append(trozo[m1.probabilidad(trozo) > 0.1])
        dificiles = np.concatenate([dificiles] + nuevos)
        ruta_tmp.unlink(missing_ok=True)
        print(f"Ronda {ronda}: {len(dificiles)} negativos reales difíciles ({time.time() - t0:.0f} s)", flush=True)
        mlp, media, escala = entrenar(x_pos, np.concatenate([x_neg, x_real] + [dificiles] * 3))
    print(f"Entrenado ({time.time() - t0:.0f} s). Midiendo con voces que no vio...", flush=True)
    ruta = BASE / "modelos" / "cacao" / f"{SALIDA}.npz"
    voces_prueba = [v for v in voces if v[0] in PRUEBA]
    resultados = []
    for umbral in (0.3, 0.5, 0.7, 0.85, 0.9, 0.95):
        guardar(mlp, media, escala, umbral, 2, ruta)
        r = medir(pa.ModeloCacao(ruta), umbral, 2, voces_prueba)
        print(json.dumps(r, ensure_ascii=False), flush=True)
        resultados.append(r)
    # el umbral más bajo sin activaciones falsas en conversación ni fondo; si ninguno, el más alto
    def falsas(r):
        return (r["conversacion_sin_cacao"]["activaciones"] + r["audio_de_fondo"]["activaciones"]
                + r.get("tus_grabaciones", {}).get("activaciones", 0)
                + (r["validacion_openwakeword"] or {}).get("activaciones", 0))
    limpios = [r for r in resultados if falsas(r) == 0]
    elegido = min(limpios, key=lambda r: r["umbral"]) if limpios else min(resultados, key=falsas)
    guardar(mlp, media, escala, elegido["umbral"], 2, ruta)
    salida = {"palabra": PALABRA, "voces_entrenamiento": [n for n, _, _ in voces if n not in PRUEBA],
              "voces_prueba": sorted(PRUEBA), "positivos": len(x_pos), "negativos": len(x_neg),
              "segundos": round(time.time() - t0), "por_umbral": resultados, "elegido": elegido}
    (BASE / f"resultados_{SALIDA}.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nElegido: umbral {elegido['umbral']}. Modelo en {ruta}. Total {time.time() - t0:.0f} s.")


if __name__ == "__main__":
    main()
