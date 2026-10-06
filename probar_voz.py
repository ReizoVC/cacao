"""
Prueba de voz.py sin micrófono ni altavoz (el audio entra desde WAV y Piper escribe en un altavoz falso).
Comprueba, sin ejecutar acciones que cambien algo:
  1. frenos: las pulsaciones en silencio o con ruido se descartan; las órdenes habladas pasan;
  2. confirmación: una herramienta que cambia algo no se ejecuta con Esc ni sin respuesta, y sí con Enter
     (la ejecución real se sustituye por una falsa); las de solo lectura no preguntan;
  3. al altavoz solo llega la respuesta final (nunca el pensamiento) y en 1 o 2 frases.
Uso: .venv\\Scripts\\python probar_voz.py   (usa voz_pruebas/validacion_<n>.wav)
"""
import json
import time
import wave
from pathlib import Path

import numpy as np

import voz

CARPETA = Path(__file__).parent / "voz_pruebas"
HABLADAS_SOLO_LECTURA = {1: "¿Qué apps de música tengo?", 10: "¿Qué archivos hay en mis descargas?",
                         20: "¿Qué ventanas tengo abiertas? (con ruido de fondo)"}
SIN_VOZ = {17: "silencio", 18: "silencio", 19: "solo ruido"}
filas = []


def registrar(prueba, ok, **datos):
    filas.append({"prueba": prueba, "ok": ok, **datos})
    print(f"{'OK ' if ok else 'MAL'} {prueba}: {json.dumps(datos, ensure_ascii=False)[:300]}", flush=True)


def leer(n):
    with wave.open(str(CARPETA / f"validacion_{n}.wav")) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


class AltavozFalso:
    latency = 0.0

    def __init__(self, *_, **__):
        self.escrito = []

    def start(self):
        pass

    def write(self, audio):
        self.escrito.append((time.perf_counter(), len(audio)))


class MicrofonoFalso:
    nombre = "WAV de prueba"

    def __init__(self, *_):
        pass

    def cerrar(self):
        pass


voz.sd.OutputStream = AltavozFalso
voz.Microfono = MicrofonoFalso

if __name__ == "__main__":
    voz.a.CONFIG.setdefault("ui", {})["activa"] = False  # sin isla: aquí las confirmaciones son falsas
    voz.CONFIG_VOZ["palabra_activacion"] = {"activa": False}  # sin micrófono real: sin escucha de "Cacao"
    atajo, _, transcriptor, locutor, historial, _planificador = voz.preparar()
    atajo.cerrar()

    # 1) frenos
    for n, nota in SIN_VOZ.items():
        datos, texto = voz.filtrar(leer(n), time.perf_counter(), transcriptor)
        registrar(f"freno: {nota} (validacion_{n})", texto is None, freno=datos.get("freno"), voz_s=datos["voz_s"])
    inventada = "Abre la carpeta de Documentos y busca el archivo Presupuesto_2024.xlsx. Luego, abre Excel y ponlo en "\
                "pantalla completa."
    registrar("freno: orden inventada en 0,8 s de voz", not voz.transcripcion_plausible(inventada, 0.8),
              palabras=voz.contar_palabras(inventada))

    # 2) confirmación con teclado (ejecución real sustituida por una falsa)
    ejecutadas = []
    ejecutar_real, confirmar_real = voz._ejecutar, voz._confirmar_base
    voz._ejecutar = lambda nombre, args: ejecutadas.append(nombre) or {"ok": True, "simulado": True}
    for respuesta, esperado in ((False, False), (None, False), (True, True)):
        voz._confirmar_base = lambda *_a, **_k: bool(respuesta)
        ejecutadas.clear()
        r = voz.ejecutar_voz("volumen", {"accion": "fijar", "nivel": 50})
        registrar(f"confirmación volumen con {'Enter' if respuesta else 'Esc' if respuesta is False else 'sin respuesta'}",
                  bool(ejecutadas) == esperado, resultado=r)
    preguntas = []
    voz._confirmar_base = lambda *_a, **_k: preguntas.append(1) or False
    ejecutadas.clear()
    voz.ejecutar_voz("listar_ventanas", {})
    registrar("solo lectura no pregunta", not preguntas and ejecutadas == ["listar_ventanas"])
    voz._ejecutar, voz._confirmar_base = ejecutar_real, confirmar_real  # el paso 3 usa las reales (solo lectura)

    # 3) órdenes habladas de solo lectura, de punta a punta (agente real, altavoz falso)
    pensamientos = []
    _print = print

    def print_registrando(*args, **kw):  # los pasos del agente se imprimen como "  [herramienta] pensamiento"
        texto = " ".join(map(str, args))
        if texto.startswith("  [") and "] " in texto and "->" not in texto:
            pensamientos.append(texto.split("] ", 1)[1])
        _print(*args, **kw)

    voz.a.print = print_registrando
    for n, referencia in HABLADAS_SOLO_LECTURA.items():
        soltado = time.perf_counter()
        datos, texto = voz.filtrar(leer(n), soltado, transcriptor)
        if texto is None:
            registrar(f"orden hablada {n}", False, freno=datos.get("freno"))
            continue
        t1 = time.perf_counter()
        respuesta = voz.a.atender(texto, historial)
        t2 = time.perf_counter()
        dicho = voz.limpiar_para_voz(respuesta)
        locutor.salida.escrito.clear()
        locutor.hablar(dicho)
        while locutor.hablando():
            time.sleep(0.01)
        primero = locutor.salida.escrito[0][0] if locutor.salida.escrito else None
        frases = len([f for f in dicho.replace("?", ".").replace("!", ".").split(".") if f.strip()])
        registrar(f"orden hablada {n}: {referencia}",
                  frases <= 2 and not any(p and p in dicho for p in pensamientos) and primero is not None,
                  transcripcion=texto, dicho=dicho, frases=frases, transcribir_s=datos["transcribir_s"],
                  agente_s=round(t2 - t1, 2), piper_s=round(primero - t2, 2) if primero else None,
                  total_s=round(primero - soltado, 2) if primero else None)
    voz.a.cerrar_isla()
    transcriptor.cerrar()
    bien = sum(f["ok"] for f in filas)
    print(f"\n{bien}/{len(filas)} OK" + ("" if bien == len(filas) else " - HAY FALLOS"))
