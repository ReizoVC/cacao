"""Chequeo de frescura del cerebro de Claude Code. SOLO LECTURA: no escribe archivos ni cambia Git.

Para cada página .md de cerebro/ con frontmatter, mira sus `fuentes` y avisa si alguna cambió después de
`verificado_commit`:
  - archivo en Git: commits posteriores que lo tocan, o cambios sin commit en el árbol de trabajo;
  - archivo fuera de Git (ignorado): fecha de modificación posterior a la del commit verificado;
  - archivo que ya no existe.
Además revisa campos obligatorios, enlaces [[...]] rotos y el tamaño estimado (≈ caracteres / 3,2 tokens; es una
estimación, no el tokenizador real).

Uso:  python -I cerebro/frescura.py [--todo]   (--todo muestra también las páginas al día)
Sale con 1 si hay páginas por revisar, 0 si no.
"""
import re
import subprocess
import sys
from pathlib import Path

CEREBRO = Path(__file__).resolve().parent
RAIZ = CEREBRO.parent
LIMITE_TOKENS = 1500
CARACTERES_POR_TOKEN = 3.2
OBLIGATORIOS = ("estado", "verificado_commit", "verificado_fecha", "fuentes")
ESTADOS = {"verificado", "sin verificar", "obsoleto"}


def git(*args):
    r = subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout.strip()


def frontmatter(texto):
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    if not m:
        return None
    datos = {}
    for linea in m.group(1).splitlines():
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            valor = valor.strip()
            if valor.startswith("[") and valor.endswith("]"):
                valor = [v.strip() for v in valor[1:-1].split(",") if v.strip()]
            datos[clave.strip()] = valor
    return datos


def revisar_fuente(ruta, commit, fecha_commit):
    p = RAIZ / ruta
    if not p.exists():
        return "ya no existe"
    en_git = git("ls-files", "--error-unmatch", ruta)[0] == 0
    if en_git:
        _, posteriores = git("log", "--format=%h", f"{commit}..HEAD", "--", ruta)
        _, sucio = git("status", "--porcelain", "--", ruta)
        avisos = []
        if posteriores:
            avisos.append("cambió en " + ", ".join(posteriores.split()[:5]))
        if sucio:
            avisos.append("cambios sin commit")
        return "; ".join(avisos) or None
    if fecha_commit and p.stat().st_mtime > fecha_commit:
        return "modificado después (fuera de Git, por fecha)"
    return None


def main():
    todo = "--todo" in sys.argv
    sys.stdout.reconfigure(encoding="utf-8")
    paginas = sorted(p for p in CEREBRO.rglob("*.md") if ".obsidian" not in p.parts)
    nombres = {p.stem for p in paginas}
    por_revisar = 0
    for p in paginas:
        rel = p.relative_to(CEREBRO).as_posix()
        texto = p.read_text(encoding="utf-8")
        avisos = []
        sin_codigo = re.sub(r"```.*?```|`[^`\n]*`", "", texto, flags=re.S)  # los ejemplos en código no son enlaces
        rotos = sorted({e.split("|")[0] for e in re.findall(r"\[\[([^\]]+)\]\]", sin_codigo)} - nombres)
        if rotos:
            avisos.append("enlaces rotos: " + ", ".join(rotos))
        tokens = round(len(texto) / CARACTERES_POR_TOKEN)
        if tokens > LIMITE_TOKENS:
            avisos.append(f"≈{tokens} tokens (> {LIMITE_TOKENS}): dividir")
        fm = frontmatter(texto)
        if fm is None:
            if rel not in ("index.md", "log.md"):
                avisos.append("sin frontmatter")
        else:
            faltan = [c for c in OBLIGATORIOS if c not in fm]
            if faltan:
                avisos.append("faltan campos: " + ", ".join(faltan))
            if fm.get("estado") not in ESTADOS:
                avisos.append(f"estado no válido: {fm.get('estado')!r}")
            commit = fm.get("verificado_commit", "")
            ok, completo = git("rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
            if ok != 0:
                avisos.append(f"commit verificado desconocido: {commit!r}")
            else:
                fecha = float(git("show", "-s", "--format=%ct", completo)[1] or 0)
                fuentes = fm.get("fuentes") or []
                if isinstance(fuentes, str):
                    fuentes = [fuentes]
                for f in fuentes:
                    aviso = revisar_fuente(f, completo, fecha)
                    if aviso:
                        avisos.append(f"{f}: {aviso}")
        if avisos:
            por_revisar += 1
            print(f"REVISAR {rel} [{(fm or {}).get('estado', '-')}, ≈{tokens} tokens]")
            for a in avisos:
                print(f"    - {a}")
        elif todo:
            print(f"ok      {rel} [≈{tokens} tokens]")
    print(f"\n{len(paginas)} páginas; {por_revisar} por revisar.")
    return 1 if por_revisar else 0


if __name__ == "__main__":
    sys.exit(main())
