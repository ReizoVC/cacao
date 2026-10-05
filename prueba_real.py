"""
Pruebas REALES del agente (Fase 5, con Reizo frente al PC). Carga agente_minimo.py tal cual y le pasa frases.
Las confirmaciones s/n del agente las responde una política por prueba: solo aprueba las acciones previstas, y
teclado/mouse solo si la ventana al frente (o el punto del clic) es del Bloc de notas, para no escribir nunca
en otra ventana. Todo queda en resultados_real_<prueba>.json.
Uso: .venv\\Scripts\\python prueba_real.py 1|2|3
"""
import json
import sys
import time
from pathlib import Path

import psutil
import win32gui
import win32process

import agente_minimo as a
import herramientas_grupo1 as g1
import herramientas_grupo4 as g4

BASE = Path(__file__).parent
CARPETA_ORIGEN = Path.home() / "Documents" / "prueba_agente_origen"
CARPETA_DESTINO = Path.home() / "Documents" / "prueba_agente_destino"
REANUDAR = BASE / "REANUDAR"  # prueba 3: lo crea Claude cuando Reizo pide reanudar
registro = []
actual = {}


def proceso_de(hwnd):
    try:
        return psutil.Process(win32process.GetWindowThreadProcessId(hwnd)[1]).name().lower()
    except psutil.Error:
        return ""


# Ventanas del Bloc de notas que la prueba puede tocar: solo las que aparecen durante la prueba como documento
# nuevo ("Sin título"). Las que ya estaban o las que abre la sesión restaurada (archivos de Reizo) nunca.
VENTANAS_PRUEBA, AJENAS = set(), set()


def actualizar_ventanas_prueba():
    for v in g1.listar_ventanas():
        h = v["id_ventana"]
        if v["proceso"].lower() != "notepad.exe" or h in VENTANAS_PRUEBA or h in AJENAS:
            continue
        nueva = any(t in v["titulo"].lower() for t in ("sin título", "untitled"))
        (VENTANAS_PRUEBA if nueva else AJENAS).add(h)


def de_la_prueba(hwnd):
    """La ventana (o el diálogo, por su ventana dueña) es una de las que abrió la prueba."""
    return (win32gui.GetAncestor(hwnd, 3) in VENTANAS_PRUEBA  # GA_ROOTOWNER: diálogos
            or win32gui.GetAncestor(hwnd, 2) in VENTANAS_PRUEBA)  # GA_ROOT


def politica_2(nombre, args):
    """Prueba 2: solo Bloc de notas, archivos de prueba y teclas previstas."""
    if nombre == "teclado":
        plan, error = g4.planificar_teclado(args.get("accion"), args.get("texto"), args.get("teclas"))
        teclas = set(plan["nombres"]) if plan and "nombres" in plan else set()
        previstas = teclas <= {"ctrl", "s", "enter", "esc", "tab"}
        frente = win32gui.GetForegroundWindow()
        return (de_la_prueba(frente) and (args.get("accion") == "escribir" or previstas),
                f"teclado: al frente {proceso_de(frente)} «{win32gui.GetWindowText(frente)}»")
    if nombre == "mouse":
        plan, error = g4.planificar_mouse(args.get("accion"), args.get("x"), args.get("y"), args.get("cantidad"),
                                          control=args.get("control"), id_ventana=args.get("id_ventana"))
        if error or not plan["pantalla"]:
            return error is None, f"mouse sin punto o con error: {error}"
        destino = win32gui.WindowFromPoint(plan["pantalla"])
        sobre = win32gui.GetWindowText(win32gui.GetAncestor(destino, 2))
        return de_la_prueba(destino), f"mouse en {plan['pantalla']}, sobre «{sobre}»"
    if nombre == "cerrar_app":
        plan, error = g4.planificar_cierre(args.get("proceso"), args.get("pid"), args.get("id_ventana"))
        ok = plan is not None and set(plan["ventanas"]) <= VENTANAS_PRUEBA and not args.get("forzar")
        return ok, f"cerrar: {plan['titulos'] if plan else error}"
    if nombre == "mover_archivo":
        plan, error = g4.planificar_movimiento(args.get("origen", ""), args.get("destino", ""))
        ok = plan is not None and plan[0].parent == CARPETA_ORIGEN and plan[1].parent == CARPETA_DESTINO
        return ok, f"mover: {plan if plan else error}"
    return False, "herramienta no prevista en esta prueba"


POLITICAS = {"1": lambda n, a_: (False, "la prueba 1 no usa herramientas con confirmación"),
             "2": politica_2,
             "2m": politica_2,
             "3": lambda n, a_: (False, "la prueba 3 no usa herramientas con confirmación")}


def confirmar(_texto):
    ok, motivo = POLITICAS[actual["prueba"]](actual["nombre"], actual["args"])
    actual["confirmacion"] = {"respuesta": "s" if ok else "n", "motivo": motivo}
    print(f"  [confirmación automática] {'SÍ' if ok else 'NO'}: {motivo}", flush=True)
    return "s" if ok else "n"


_ejecutar = a.ejecutar


def ejecutar_registrado(nombre, args):
    if actual["prueba"] in ("2", "2m"):
        actualizar_ventanas_prueba()
    actual.update(nombre=nombre, args=args, confirmacion=None)
    t = time.perf_counter()
    resultado = _ejecutar(nombre, args)
    visible = {k: v for k, v in resultado.items() if k != "_imagen"} if isinstance(resultado, dict) else resultado
    registro[-1]["pasos"].append({"herramienta": nombre, "argumentos": args, "resultado": visible,
                                  "confirmacion": actual["confirmacion"], "segundos": round(time.perf_counter() - t, 2)})
    print(f"  [{nombre}] -> {json.dumps(visible, ensure_ascii=False)[:300]}", flush=True)
    return resultado


a.ejecutar = ejecutar_registrado
a.input = confirmar  # sustituye al input() de ejecutar y preparar_apertura


def correr(frases, historial=None):
    historial = historial or [{"role": "system", "content": a.prompt_sistema()}]
    for frase in frases:
        if frase is None:  # sesión nueva: el prompt se vuelve a armar con las memorias guardadas
            historial = [{"role": "system", "content": a.prompt_sistema()}]
            continue
        registro.append({"frase": frase, "pasos": []})
        print(f"\nTú: {frase}", flush=True)
        t = time.perf_counter()
        respuesta = a.atender(frase, historial)
        registro[-1].update(respuesta=respuesta, segundos=round(time.perf_counter() - t, 2))
        print(f"Asistente: {respuesta}  ({registro[-1]['segundos']} s)", flush=True)
        time.sleep(1.5)  # deja que la app abra o cierre antes del paso siguiente
    return historial


if __name__ == "__main__":
    actual["prueba"] = prueba = sys.argv[1]
    if prueba == "1":
        correr(["abre la calculadora",
                "cuando digo el editor me refiero a VS Code",
                None,
                "abre el editor",
                "pon el volumen al 30",
                "sube el volumen un poco",
                "trae al frente la calculadora",
                "busca en internet el clima de Lima para mañana"])
    elif prueba == "2":
        CARPETA_ORIGEN.mkdir(exist_ok=True)
        CARPETA_DESTINO.mkdir(exist_ok=True)
        actualizar_ventanas_prueba()  # lo que ya está abierto queda como ajeno
        AJENAS.update(VENTANAS_PRUEBA)
        VENTANAS_PRUEBA.clear()
        ruta = CARPETA_ORIGEN / "prueba_agente.txt"
        correr(["abre el bloc de notas",
                "escribe en el bloc de notas: Hola, esta es una prueba del asistente.",
                f"guarda el archivo con ctrl+s y, en la ventana de guardar, escribe la ruta {ruta} y pulsa enter",
                "mira la pantalla con presupuesto 1120 y cuadrícula, y haz clic en el menú Archivo del Bloc de notas",
                "cierra ese menú con la tecla escape",
                "cierra la ventana del bloc de notas donde escribiste",
                f"mueve {ruta} a la carpeta {CARPETA_DESTINO}"])
        registro.append({"comprobacion": {"guardado_en_origen": ruta.exists(),
                                          "movido_a_destino": (CARPETA_DESTINO / "prueba_agente.txt").exists(),
                                          "contenido": (CARPETA_DESTINO / "prueba_agente.txt").read_text(
                                              encoding="utf-8", errors="replace")
                                          if (CARPETA_DESTINO / "prueba_agente.txt").exists() else None}})
        print("\nComprobación:", registro[-1]["comprobacion"])
    elif prueba == "2m":  # solo la parte de mouse de la prueba 2: clic por nombre de control y verificación
        actualizar_ventanas_prueba()  # lo que ya está abierto queda como ajeno
        AJENAS.update(VENTANAS_PRUEBA)
        VENTANAS_PRUEBA.clear()
        correr(["abre el bloc de notas",
                "haz clic en el menú Archivo del Bloc de notas",
                "cierra ese menú con la tecla escape",
                "cierra la ventana del bloc de notas que abriste"])
    elif prueba == "3":
        listo = a.emergencia.iniciar()
        print(f"Atajo registrado: {listo}. Tareas de varios pasos en bucle hasta que pulses {a.emergencia.atajo} "
              "(máximo 3 minutos).", flush=True)
        tareas = ["revisa una por una mis apps de música, de juegos, de oficina y de desarrollo y dime cuántas hay "
                  "de cada categoría",
                  "lista las ventanas abiertas, luego los archivos de mis descargas y luego los de mi escritorio, "
                  "y resúmeme todo"]
        inicio = time.time()
        detenida = None
        while time.time() - inicio < 180 and detenida is None:
            for tarea in tareas:
                correr([tarea])
                if a.emergencia.detenido():  # cortó esta tarea o se pulsó justo después: no se descarta
                    detenida = registro[-1]
                    break
        if detenida:
            print("\n== Agente detenido; una tarea nueva debe rechazarse ==", flush=True)
            correr(["¿qué apps de música tengo?"])
            rechazada = registro[-1]["respuesta"] == a.MENSAJE_DETENIDO and not registro[-1]["pasos"]
            # Reizo decide cuándo reanudar: el script espera a que exista el archivo REANUDAR (máximo 10 min)
            print(f"\n== Esperando que Reizo pida reanudar (archivo {REANUDAR.name}) ==", flush=True)
            limite = time.time() + 600
            while not REANUDAR.exists() and time.time() < limite:
                time.sleep(0.5)
            reanudada = REANUDAR.exists()
            if reanudada:
                REANUDAR.unlink()
                a.emergencia.reanudar()
                print("\n== Reanudado; la siguiente tarea debe funcionar ==", flush=True)
                correr(["¿qué apps de música tengo?"])
            registro.append({"detenida": True, "pulsaciones": a.emergencia.pulsaciones,
                             "tarea_nueva_rechazada": rechazada, "reanudada": reanudada})
        else:
            registro.append({"detenida": False})
    Path(BASE / f"resultados_real_{prueba}.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
