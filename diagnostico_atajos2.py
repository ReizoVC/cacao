"""
Diagnóstico de atajos, segunda ronda (la primera: ninguna variante de Ctrl+S abrió "Guardar como").
  1. Reizo pulsa Ctrl+S él mismo (guiado por voz): se anotan las ventanas nuevas que aparecen (proceso, clase,
     título) y él las cierra con Esc. Así se sabe qué buscar.
  2. Ctrl+N inyectado: ¿funciona algún atajo con Ctrl? (cambia el título a "Sin título").
  3. Ctrl+S inyectado con VK_LCONTROL y con la tecla mantenida 100 y 200 ms, buscando ventanas nuevas de cualquier
     proceso y el cambio de ventana al frente.
Solo envía teclas con el Bloc de notas al frente. No guarda nada.
"""
import json
import time

import psutil
import win32gui
import win32process

import herramientas_grupo1 as g1
from diagnostico_atajos import KEYUP, VK_ESCAPE, enviar, scan_de
from grabar_cacao import Guia

VK_CONTROL, VK_LCONTROL, VK_S, VK_N = 0x11, 0xA2, 0x53, 0x4E


def ventanas():
    v = {}

    def cb(h, _):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h):
            try:
                proc = psutil.Process(win32process.GetWindowThreadProcessId(h)[1]).name()
            except psutil.Error:
                proc = "?"
            v[h] = (proc, win32gui.GetClassName(h), win32gui.GetWindowText(h)[:60])
        return True

    win32gui.EnumWindows(cb, None)
    return v


def frente():
    h = win32gui.GetForegroundWindow()
    try:
        proc = psutil.Process(win32process.GetWindowThreadProcessId(h)[1]).name()
    except psutil.Error:
        proc = "?"
    return h, proc, win32gui.GetClassName(h), win32gui.GetWindowText(h)[:60]


def combo(mod, tecla, hold=0.0, pausa=0.03, scan=True):
    enviar(mod, scan_de(mod) if scan else 0)
    time.sleep(pausa)
    enviar(tecla, scan_de(tecla) if scan else 0)
    time.sleep(hold)
    enviar(tecla, scan_de(tecla) if scan else 0, KEYUP)
    time.sleep(pausa)
    enviar(mod, scan_de(mod) if scan else 0, KEYUP)


def observar(segundos=2.5):
    antes, f0 = ventanas(), frente()
    time.sleep(segundos)
    despues, f1 = ventanas(), frente()
    nuevas = [despues[h] for h in despues if h not in antes]
    return {"nuevas": nuevas, "frente_antes": f0[1:], "frente_despues": f1[1:]}


def main():
    guia = Guia()
    r = {}
    bloc = next((h for h, (p, c, t) in ventanas().items() if p.lower() == "notepad.exe"), None)
    if not bloc:
        guia.decir("No encuentro el Bloc de notas.")
        return
    g1.enfocar_ventana(bloc)
    guia.decir("Primero tú: con el Bloc de notas al frente, pulsa Control S. Cuando veas la ventana de guardar, "
               "espera dos segundos y ciérrala con Escape. Tienes veinte segundos.")
    antes = ventanas()
    vistas = {}
    limite = time.monotonic() + 20
    while time.monotonic() < limite:
        for h, info in ventanas().items():
            if h not in antes:
                vistas[h] = info
        f = frente()
        if f[0] not in antes:
            vistas[f[0]] = f[1:]
        time.sleep(0.1)
    r["fisico_ctrl_s"] = list(vistas.values())
    print("Ctrl+S físico, ventanas nuevas:", r["fisico_ctrl_s"], flush=True)
    guia.decir("Gracias. Ahora no toques nada durante medio minuto.")
    time.sleep(1)

    pruebas = [("ctrl+N (vk genérico, scan)", lambda: combo(VK_CONTROL, VK_N)),
               ("ctrl+S VK_LCONTROL", lambda: combo(VK_LCONTROL, VK_S)),
               ("ctrl+S mantener 100 ms", lambda: combo(VK_CONTROL, VK_S, hold=0.1, pausa=0.05)),
               ("ctrl+S VK_LCONTROL mantener 200 ms", lambda: combo(VK_LCONTROL, VK_S, hold=0.2, pausa=0.1))]
    for nombre, accion in pruebas:
        g1.enfocar_ventana(bloc)
        time.sleep(0.5)
        if frente()[0] != bloc:
            r[nombre] = "omitido: el Bloc de notas no estaba al frente"
            continue
        accion()
        obs = observar()
        r[nombre] = obs
        print(nombre, json.dumps(obs, ensure_ascii=False), flush=True)
        if obs["nuevas"] or obs["frente_despues"] != obs["frente_antes"]:
            enviar(VK_ESCAPE)
            enviar(VK_ESCAPE, flags=KEYUP)
            time.sleep(1)
    guia.decir("Listo, terminé.")
    with open("resultados_diagnostico_atajos2.json", "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
