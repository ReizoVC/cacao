"""
Diagnóstico de atajos, tercera ronda. Hallazgo de Reizo: en español, Guardar es Ctrl+G (Bloc de notas: Ctrl+S no
existe; Word: Ctrl+S es Subrayado). Comprueba que el envío actual de Cacao (herramientas_grupo4.teclado, sin
cambios) sí funciona con el atajo correcto: Ctrl+G en el Bloc de notas y en Word, mirando si aparece una ventana o
cambia la ventana al frente. Lo que se abra se cierra con Esc; no se guarda nada.
Uso: .venv\\Scripts\\python diagnostico_atajos3.py [notepad.exe] [winword.exe]
"""
import json
import sys
import time

import herramientas_grupo1 as g1
import herramientas_grupo4 as g4
from diagnostico_atajos import KEYUP, VK_ESCAPE, enviar
from diagnostico_atajos2 import frente, observar, ventanas


def probar(proceso, teclas):
    destino = next((h for h, (p, c, t) in ventanas().items() if p.lower() == proceso), None)
    if not destino:
        return {"proceso": proceso, "resultado": "no está abierto"}
    g1.enfocar_ventana(destino)
    time.sleep(0.6)
    if frente()[0] != destino:
        return {"proceso": proceso, "resultado": "omitido: no quedó al frente"}
    titulo = frente()[3]
    g4.teclado("atajo", teclas=teclas)
    obs = observar(3.0)
    hubo = bool(obs["nuevas"]) or obs["frente_despues"] != obs["frente_antes"]
    if hubo:
        enviar(VK_ESCAPE)
        enviar(VK_ESCAPE, flags=KEYUP)
        time.sleep(1)
    return {"proceso": proceso, "atajo": "+".join(teclas), "titulo": titulo,
            "resultado": "ABRE algo" if hubo else "sin efecto visible", **obs}


if __name__ == "__main__":
    procesos = [a.lower() for a in sys.argv[1:]] or ["notepad.exe", "winword.exe"]
    r = [probar(p, ["ctrl", "g"]) for p in procesos]
    for x in r:
        print(json.dumps(x, ensure_ascii=False), flush=True)
    with open("resultados_diagnostico_atajos3.json", "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
