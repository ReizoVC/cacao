"""
Diagnóstico: por qué el Ctrl+S que envía Cacao no abre "Guardar como" en el Bloc de notas (Fase 5: Ctrl+V sí
funcionaba). Abre un Bloc de notas, escribe un texto de prueba (sin guardar) y prueba variantes de SendInput:
  actual        lo que hace herramientas_grupo4.teclado (código virtual, sin pausas)
  vk+scan       código virtual y código de escaneo (MapVirtualKey), sin pausas
  vk+scan+pausa lo mismo con PAUSA_S entre cada evento
  scan+pausa    solo código de escaneo (KEYEVENTF_SCANCODE), con pausas
  vk+pausa      solo código virtual, con pausas
Éxito = aparece una ventana "Guardar como" del Bloc de notas; se cierra con Esc antes de la siguiente prueba. Solo
envía teclas si el Bloc de notas está al frente. No guarda nada: el texto queda en una pestaña sin guardar.
Uso: .venv\\Scripts\\python diagnostico_atajos.py [repeticiones=2]
"""
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes

import psutil
import win32con
import win32gui
import win32process

import herramientas_grupo1 as g1
import herramientas_grupo4 as g4

user32 = ctypes.windll.user32
PAUSA_S = 0.03
KEYEVENTF_SCANCODE, KEYEVENTF_EXTENDEDKEY, KEYUP = 0x0008, 0x0001, 0x0002
VK_CONTROL, VK_S, VK_ESCAPE = 0x11, 0x53, 0x1B


def enviar(vk=0, scan=0, flags=0):
    e = g4._INPUT(type=g4.INPUT_KEYBOARD, ki=g4._KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags))
    return user32.SendInput(1, ctypes.byref(e), ctypes.sizeof(g4._INPUT))


def scan_de(vk):
    return user32.MapVirtualKeyW(vk, 0)  # MAPVK_VK_TO_VSC


def combo(teclas, usar_vk=True, usar_scan=False, solo_scan=False, pausa=0.0):
    eventos = [(t, 0) for t in teclas] + [(t, KEYUP) for t in reversed(teclas)]
    for vk, arriba in eventos:
        if solo_scan:
            enviar(0, scan_de(vk), KEYEVENTF_SCANCODE | arriba)
        else:
            enviar(vk if usar_vk else 0, scan_de(vk) if usar_scan else 0, arriba)
        if pausa:
            time.sleep(pausa)


VARIANTES = {
    "actual": lambda: g4.teclado("atajo", teclas=["ctrl", "s"]),
    "vk+scan": lambda: combo([VK_CONTROL, VK_S], usar_scan=True),
    "vk+scan+pausa": lambda: combo([VK_CONTROL, VK_S], usar_scan=True, pausa=PAUSA_S),
    "scan+pausa": lambda: combo([VK_CONTROL, VK_S], solo_scan=True, pausa=PAUSA_S),
    "vk+pausa": lambda: combo([VK_CONTROL, VK_S], pausa=PAUSA_S),
}


def ventanas_de(pid):
    encontradas = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h) and win32process.GetWindowThreadProcessId(h)[1] == pid:
            encontradas.append((h, win32gui.GetClassName(h), win32gui.GetWindowText(h)))
        return True

    win32gui.EnumWindows(cb, None)
    return encontradas


def dialogo_guardar(pid):
    return next((v for v in ventanas_de(pid) if v[1] == "#32770" or "guardar" in v[2].lower()
                 or "save" in v[2].lower()), None)


def bloc_al_frente(hwnd):
    return win32gui.GetForegroundWindow() == hwnd


def main():
    repeticiones = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    antes = {p.pid for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == "notepad.exe"}
    subprocess.Popen(["notepad.exe"])
    hwnd = pid = None
    limite = time.monotonic() + 10
    while time.monotonic() < limite and not hwnd:
        time.sleep(0.3)
        h = win32gui.GetForegroundWindow()
        p = win32process.GetWindowThreadProcessId(h)[1]
        try:
            if psutil.Process(p).name().lower() == "notepad.exe":
                hwnd, pid = h, p
        except psutil.Error:
            pass
    if not hwnd:
        sys.exit("El Bloc de notas no quedó al frente; no envío nada.")
    time.sleep(1)
    g4._pegar("prueba de atajos de Cacao (no se guarda)")
    time.sleep(0.5)
    resultados = []
    for nombre, variante in VARIANTES.items():
        for i in range(repeticiones):
            g1.enfocar_ventana(hwnd)
            time.sleep(0.4)
            if not bloc_al_frente(hwnd) or dialogo_guardar(pid):
                resultados.append({"variante": nombre, "intento": i + 1, "resultado": "omitido (sin foco)"})
                continue
            variante()
            limite = time.monotonic() + 2.5
            dialogo = None
            while time.monotonic() < limite and not dialogo:
                time.sleep(0.1)
                dialogo = dialogo_guardar(pid)
            resultados.append({"variante": nombre, "intento": i + 1,
                               "resultado": "ABRE Guardar como" if dialogo else "no abre",
                               "ventana": dialogo[2] if dialogo else win32gui.GetWindowText(win32gui.GetForegroundWindow())[:40]})
            print(json.dumps(resultados[-1], ensure_ascii=False), flush=True)
            if dialogo:
                win32gui.SetForegroundWindow(dialogo[0]) if win32gui.GetForegroundWindow() != dialogo[0] else None
                time.sleep(0.2)
                enviar(VK_ESCAPE)
                enviar(VK_ESCAPE, flags=KEYUP)
                limite = time.monotonic() + 3
                while time.monotonic() < limite and dialogo_guardar(pid):
                    time.sleep(0.1)
            time.sleep(0.5)
    with open("resultados_diagnostico_atajos.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)
    print("\nResumen:", {n: sum(r["resultado"].startswith("ABRE") for r in resultados if r["variante"] == n)
                         for n in VARIANTES}, flush=True)
    print(f"Bloc de notas: pid {pid}, hwnd {hwnd} (nuevo={pid not in antes})", flush=True)


if __name__ == "__main__":
    main()
