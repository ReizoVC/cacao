"""
Simulación sin modelo del filtrado de herramientas (diseño en cerebro/decisiones/filtrado-herramientas.md).

Núcleo fijo de herramientas y grupos que se añaden por palabras clave del pedido; ante la duda, todos. Para las 65 + 30
frases: qué grupos salen, si cubren las herramientas esperadas ('esperado' y 'requiere') y cuántos tokens tendría el
prompt de sistema, con las cifras por herramienta de medir_prompt.py (--tokens, el JSON que guarda con --guardar).
No carga ningún modelo ni cambia producción.
Uso: .venv\\Scripts\\python comparacion_modelos\\simular_filtrado.py --tokens comparacion_modelos\\datos\\prompt_tokens_<fecha>.json
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUCLEO = ["finalizar", "volumen", "abrir_app", "listar_apps", "listar_ventanas", "enfocar_ventana", "consultar_memoria"]
GRUPOS = {
    "interfaz": (["mouse", "teclado", "ver_pantalla", "listar_controles", "cerrar_app"],
                 r"\b(?:clic|pulsa\w*|presiona\w*|boton|rueda|desplaz\w*|baja con|sube con|escrib\w*|teclea\w*|"
                 r"tecla\w*|atajo|control [a-z]\b|guarda\w*|pantalla|ves|mira|cierr\w*|cerr\w*|sal(?:ir)? de|"
                 r"termin\w*|mata\w*|quita\w*)"),
    "archivos": (["listar_carpeta", "leer_archivo", "mover_archivo", "deshacer_movimiento"],
                 r"\b(?:archivo\w*|carpeta\w*|descargas|documentos|escritorio|mueve|mover|traslad\w*|renombr\w*|"
                 r"nombre de|lee\b|leer|resume|contenido|\.\w{2,4}\b|deshac\w*)"),
    "memoria": (["recordar", "sugerencias", "registro_habitos"],
                r"\b(?:recuerd\w*|acuerdate|sugi?er\w*|recomend\w*|habito\w*|registr\w*|suelo|costumbre\w*)"),
    "web": (["buscar_web"], r"\b(?:busca\w* en (?:internet|la web)|internet|web|averigua\w*|clima|noticias?)\b"),
    "powershell": (["ejecutar_powershell"], r"\b(?:powershell|comando|terminal de comandos|script)\b"),
}


def normal(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def grupos_de(frase):
    t = normal(frase)
    return [g for g, (_, patron) in GRUPOS.items() if re.search(patron, t)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens", type=Path, required=True)
    args = parser.parse_args()
    perfiles = {f["perfil"]: f for f in json.loads(args.tokens.read_text(encoding="utf-8")) if "error" not in f}
    frases = []
    for archivo in (ROOT / "pruebas.json", ROOT / "comparacion_modelos" / "pruebas_nuevas_30.json"):
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        frases += datos["pruebas"] if isinstance(datos, dict) else datos
    resumen = {p: [] for p in perfiles}
    faltan, solo_nucleo, conteo = [], 0, {}
    for prueba in frases:
        grupos = grupos_de(prueba["frase"])
        herramientas = set(NUCLEO) | {h for g in grupos for h in GRUPOS[g][0]}
        esperado = prueba["esperado"] if isinstance(prueba["esperado"], list) else [prueba["esperado"]]
        necesarias = set(prueba.get("requiere", [])) | ({esperado[0]} if esperado else set())
        if necesarias - herramientas:
            faltan.append((prueba["id"], prueba["frase"], sorted(necesarias - herramientas)))
        solo_nucleo += not grupos
        for g in grupos:
            conteo[g] = conteo.get(g, 0) + 1
        for perfil, f in perfiles.items():
            fijo = f["total_prompt_sistema"] - f["herramientas_total"]
            resumen[perfil].append(fijo + sum(f["herramientas"].get(h, 0) for h in herramientas))
    print(f"{len(frases)} frases; solo núcleo: {solo_nucleo}; frases por grupo: {conteo}")
    print(f"Frases cuya herramienta necesaria queda fuera: {len(faltan)}")
    for x in faltan:
        print("  ", x)
    for perfil, tokens in resumen.items():
        f = perfiles[perfil]
        fijo = f["total_prompt_sistema"] - f["herramientas_total"]
        nucleo = fijo + sum(f["herramientas"].get(h, 0) for h in NUCLEO)
        grupos_tok = {g: sum(f["herramientas"].get(h, 0) for h in hs) for g, (hs, _) in GRUPOS.items()}
        print(f"\n{perfil}: hoy {f['total_prompt_sistema']} tokens; núcleo solo {nucleo}; grupos {grupos_tok}")
        print(f"  media con filtrado {sum(tokens) / len(tokens):.0f}; mínimo {min(tokens)}; máximo {max(tokens)}")


if __name__ == "__main__":
    main()
