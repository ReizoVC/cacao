"""
Prueba presencial de la isla (con Reizo frente al PC), guiada en voz alta con Piper. Abre la isla real con un
servidor de PRUEBA (no el agente): los interruptores solo se anotan (el modo sin confirmación no se activa en
Cacao) y los pedidos escritos no se ejecutan.

  1. interruptores con su clic: "Modo sin confirmación" y "Escuchar «Cacao»" en Ajustes de la isla, y "Modo sin
     confirmación" en la bandeja -> deben llegar como físicos; indicador ámbar a la vista;
  2. campo de texto, con el Bloc de notas al frente (lo abre él):
     a) clic en el campo, "hola" y Enter -> llega el pedido y el foco vuelve al Bloc de notas;
     b) clic en el campo, algo y Esc -> no llega nada y el foco vuelve al Bloc de notas;
     c) clic en el campo y clic en otra ventana -> el foco se queda en esa ventana;
     d) clic en el campo y clic en la casita de la isla -> el foco vuelve al Bloc de notas;
     e) con el Bloc de notas al frente, clic en un botón de la isla -> el Bloc de notas no pierde el foco.
Registra cada cambio de la ventana al frente (proceso, cada 50 ms) y lo que llega a la isla.
Resultados: resultados_isla_presencial.json. Uso: .venv\\Scripts\\python prueba_presencial_isla.py
"""
import json
import subprocess
import threading
import time
from pathlib import Path

import psutil
import win32gui
import win32process

import ui_isla
from grabar_cacao import Guia

BASE = Path(__file__).parent
SOLO_BANDEJA = "--solo-bandeja" in __import__("sys").argv
EXE = Path(r"C:\asistente-ui\windows\target\release\asistente-ui.exe")
resultados, frente_log = [], []


def ok(nombre, condicion, detalle=""):
    resultados.append({"prueba": nombre, "ok": bool(condicion), "detalle": str(detalle)})
    print(f"{'OK   ' if condicion else 'FALLO'} {nombre}{f'  ({detalle})' if detalle else ''}", flush=True)


def proceso_al_frente():
    try:
        pid = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[1]
        return psutil.Process(pid).name().lower()
    except Exception:
        return ""


def vigilar_frente(fin):
    previo = None
    while not fin.is_set():
        p = proceso_al_frente()
        if p != previo:
            frente_log.append((time.strftime("%H:%M:%S"), p))
            previo = p
        time.sleep(0.05)


def esperar(cond, segundos):
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if cond():
            return True
        time.sleep(0.1)
    return False


def main():
    guia = Guia()
    modos, pedidos = [], []
    s = ui_isla.ServidorIsla()
    s.al_cambiar_modo = lambda modo, fisico, origen: modos.append((modo, fisico, origen))
    s.al_pedido = pedidos.append
    s.al_conectar = lambda: s.enviar({"tipo": "modos", "sin_confirmacion": False, "escucha": False})
    s.iniciar()
    isla = subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
    fin = threading.Event()
    threading.Thread(target=vigilar_frente, args=(fin,), daemon=True).start()
    try:
        ok("la isla se conecta al servidor de prueba", esperar(lambda: s.conectada, 30))
        guia.decir("Empezamos la prueba de la isla. Esta isla está conectada a un servidor de prueba: nada de lo "
                   "que hagas se ejecuta de verdad.")

        if SOLO_BANDEJA:
            guia.decir("Repetimos solo la bandeja. Busca el icono de Cacao en la barra de tareas; si no lo ves, "
                       "ábrelo con la flechita de iconos ocultos. Clic derecho en él, y Modo sin confirmación. "
                       "Tienes un minuto y medio.")
            n = len(modos)
            llego = esperar(lambda: len(modos) > n, 90)
            ok("bandeja 'Modo sin confirmación': llega como físico",
               llego and modos[-1] == ("sin_confirmacion", True, "bandeja"), modos[n:])
            guia.decir("Listo." if llego else "No llegó nada desde la bandeja.")
            return
        # 1. interruptores
        guia.decir("Primero, los interruptores. Abre la isla pasando el mouse por arriba, entra en Ajustes con la "
                   "rueda dentada y haz clic en el interruptor Modo sin confirmación. Tienes un minuto.")
        n = len(modos)
        llego = esperar(lambda: len(modos) > n, 60)
        ok("interruptor 'Modo sin confirmación' en la isla: llega como físico",
           llego and modos[-1] == ("sin_confirmacion", True, "isla"), modos[n:])
        if llego:
            s.enviar({"tipo": "modos", "sin_confirmacion": True, "escucha": False})  # solo para ver el indicador
            guia.decir("Ahora deberías ver el indicador ámbar en la isla. Es solo una prueba: Cacao no está en marcha.")
            time.sleep(4)
            s.enviar({"tipo": "modos", "sin_confirmacion": False, "escucha": False})
        guia.decir("Ahora haz clic en el interruptor Escuchar Cacao.")
        n = len(modos)
        llego = esperar(lambda: len(modos) > n, 60)
        ok("interruptor 'Escuchar «Cacao»' en la isla: llega como físico",
           llego and modos[-1] == ("escucha", True, "isla"), modos[n:])
        if llego:
            s.enviar({"tipo": "modos", "sin_confirmacion": False, "escucha": True})
            guia.decir("Deberías ver el indicador de escucha.")
            time.sleep(3)
            s.enviar({"tipo": "modos", "sin_confirmacion": False, "escucha": False})
        guia.decir("Ahora en la bandeja: clic derecho en el icono de Cacao, y Modo sin confirmación.")
        n = len(modos)
        llego = esperar(lambda: len(modos) > n, 60)
        ok("bandeja 'Modo sin confirmación': llega como físico",
           llego and modos[-1] == ("sin_confirmacion", True, "bandeja"), modos[n:])

        # 2. campo de texto
        guia.decir("Ahora el campo de texto. Abre el Bloc de notas y haz clic dentro de él. Tienes treinta segundos.")
        ok("Bloc de notas al frente", esperar(lambda: proceso_al_frente() == "notepad.exe", 30), proceso_al_frente())

        guia.decir("Primera: abre la isla, haz clic en el campo Escribe a Cacao, escribe hola y pulsa Enter.")
        n = len(pedidos)
        llego = esperar(lambda: len(pedidos) > n, 60)
        time.sleep(0.8)
        ok("Enter: llega el pedido", llego and pedidos[-1].lower().startswith("hola"), pedidos[n:])
        ok("Enter: el foco vuelve al Bloc de notas", proceso_al_frente() == "notepad.exe", proceso_al_frente())

        guia.decir("Segunda: haz clic en el campo, escribe cualquier cosa y pulsa Escape.")
        n = len(pedidos)
        tomo = esperar(lambda: proceso_al_frente() == "asistente-ui.exe", 60)
        volvio = esperar(lambda: proceso_al_frente() == "notepad.exe", 60)
        time.sleep(0.5)
        ok("Esc: la isla tomó el foco al hacer clic en el campo", tomo)
        ok("Esc: no llega ningún pedido y el foco vuelve al Bloc de notas", volvio and len(pedidos) == n,
           f"frente={proceso_al_frente()} pedidos={pedidos[n:]}")

        guia.decir("Tercera: haz clic en el campo, y luego haz clic en otra ventana, por ejemplo el Explorador de "
                   "archivos o esta consola.")
        tomo = esperar(lambda: proceso_al_frente() == "asistente-ui.exe", 60)
        salio = esperar(lambda: proceso_al_frente() not in ("asistente-ui.exe", ""), 60)
        time.sleep(1.0)
        final = proceso_al_frente()
        ok("clic fuera: la isla tomó el foco", tomo)
        ok("clic fuera: el foco se queda en la ventana del clic (no vuelve al Bloc de notas)",
           salio and final not in ("notepad.exe", "asistente-ui.exe"), final)

        guia.decir("Cuarta: vuelve a hacer clic en el Bloc de notas. Luego haz clic en el campo de la isla, y "
                   "después en la casita de la isla, arriba a la izquierda.")
        esperar(lambda: proceso_al_frente() == "notepad.exe", 60)
        tomo = esperar(lambda: proceso_al_frente() == "asistente-ui.exe", 60)
        volvio = esperar(lambda: proceso_al_frente() == "notepad.exe", 60)
        ok("clic en la isla fuera del campo: el foco vuelve al Bloc de notas", tomo and volvio, proceso_al_frente())

        guia.decir("Última: con el Bloc de notas al frente, haz clic en la rueda dentada o en la casita de la isla, "
                   "sin tocar el campo. Tienes veinte segundos.")
        robado = esperar(lambda: proceso_al_frente() == "asistente-ui.exe", 20)
        ok("botones de la isla: el Bloc de notas no pierde el foco", not robado, proceso_al_frente())
        guia.decir("Terminamos. Fíjate si el campo se veía bien, y dímelo en el chat.")
    finally:
        fin.set()
        isla.terminate()
        isla.wait(10)
        s.cerrar()
        (BASE / ("resultados_isla_bandeja.json" if SOLO_BANDEJA else "resultados_isla_presencial.json")).write_text(json.dumps(
            {"resultados": resultados, "ventana_al_frente": frente_log, "modos": modos, "pedidos": pedidos},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n{sum(r['ok'] for r in resultados)}/{len(resultados)} OK", flush=True)


if __name__ == "__main__":
    main()
