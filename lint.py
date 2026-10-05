"""
Fase 6: revisión semanal de la wiki (el 'lint' del patrón LLM Wiki), cada lint_dias días, con las mismas
condiciones de inactividad que la reflexión.

El CÓDIGO arregla solo lo mecánico (páginas del esquema que faltan, índice, enlaces rotos en secciones del asistente)
y anota en revision.md:
  - secciones sin marcadores, secciones del código congeladas por una edición tuya, tamaño excedido;
  - datos viejos: secciones del modelo sin actualizar en > 30 días y sugerencias que ya no se ven;
  - páginas sueltas fuera de mis_notas/ y fuentes/ (propone moverlas);
  - patrones sensibles en cualquier página del vault (propone borrar, no borra; no copia el texto);
  - si tu texto ya no cabe entero en el prompt.
El MODELO lista posibles contradicciones entre las frases del asistente, o con alias y preferencias de memoria.db, y
rutinas que ya no se ven en los datos. Solo se numeran frases del asistente: tu texto es la referencia, nunca el
acusado. Si dos cosas tuyas chocan, gana la más reciente y se te avisa. Nada se resuelve solo a favor del modelo.
"""
import re
from datetime import datetime, timedelta

import memoria
import sugerencias
import wiki
from reflexion import Reflexion, ReflexionDetenida, preparar_datos
from wiki import LIMITES, PAGINAS

DIAS_VIEJO = 30
SISTEMA = ("Revisas la wiki personal de Reizo. Lo que escribió Reizo es verdad y es la referencia: nunca es el "
           "error. Señala solo problemas reales en las frases numeradas del asistente. Responde SOLO con el JSON "
           "pedido; lista vacía si no hay problemas.")


class Lint:
    def __init__(self, cada_dias=None):
        self.cada_dias = cada_dias or wiki.CONFIG["memoria_wiki"]["lint_dias"]

    def pendiente(self, ahora):
        if not wiki.estado("ultima_reflexion"):
            return False  # sin ninguna reflexión no hay nada que revisar
        ultimo = wiki.estado("ultimo_lint")
        return not ultimo or ahora - datetime.strptime(ultimo, "%Y-%m-%d %H:%M") >= timedelta(days=self.cada_dias)

    # ----- parte mecánica -----

    def mecanicos(self, ahora):
        avisos, arreglos = [], []
        recreadas = wiki.asegurar_vault(ahora)
        arreglos += [f"Página {p}.md recreada (faltaba)." for p in recreadas]
        wiki.detectar_ediciones(ahora)
        fijas = wiki.congeladas()
        validos = wiki._nombres_validos()
        for pid, esquema in PAGINAS.items():
            pagina = wiki.leer(pid)
            for s in esquema["secciones"]:
                if s["id"] not in pagina["secciones"]:
                    avisos.append(f"[[{pid}]]: falta la sección '{s['titulo']}' (¿se borraron sus marcadores?). "
                                  "No la toco; si la quieres de vuelta, borra la página y se recrea.")
                    continue
                datos = pagina["secciones"][s["id"]]
                texto, editada = datos["texto"], (pid, s["id"]) in fijas
                rotos = [m.group(1) for m in wiki.RE_ENLACE.finditer(texto) if wiki.normalizar(m.group(1)) not in validos]
                if rotos and s["autor"] != "reizo" and not editada:
                    try:
                        nuevo = wiki.RE_ENLACE.sub(lambda m: m.group(0) if wiki.normalizar(m.group(1)) in validos
                                                   else (m.group(3) or m.group(1)), texto)
                        wiki.escribir(pid, {s["id"]: nuevo}, ahora=ahora)
                        arreglos.append(f"[[{pid}]] '{s['titulo']}': {len(rotos)} enlace(s) roto(s) pasados a texto.")
                    except wiki.Pospuesto:
                        avisos.append(f"[[{pid}]] '{s['titulo']}': enlaces rotos; no pude arreglarlos (página abierta).")
                elif rotos:
                    avisos.append(f"[[{pid}]] '{s['titulo']}' (tuya): enlace(s) a páginas que no existen: "
                                  f"{', '.join(rotos[:3])}.")
                if editada and s["autor"] == "codigo":
                    avisos.append(f"[[{pid}]] '{s['titulo']}': la editaste y quedó congelada, así que sus datos ya no "
                                  "se actualizan. Vacíala para que el asistente la vuelva a llenar.")
                vinetas = sum(1 for l in texto.splitlines() if l.startswith("- "))
                if s["autor"] == "modelo" and vinetas > s.get("frases_max", LIMITES["frases_max"]):
                    avisos.append(f"[[{pid}]] '{s['titulo']}': tiene {vinetas} frases (máximo "
                                  f"{s.get('frases_max', LIMITES['frases_max'])}).")
                m = re.search(r"actualizado:(\d{4}-\d{2}-\d{2})", datos["meta"])
                if s["autor"] == "modelo" and not editada and m and \
                        ahora - datetime.strptime(m.group(1), "%Y-%m-%d") > timedelta(days=DIAS_VIEJO):
                    avisos.append(f"[[{pid}]] '{s['titulo']}': sin actualizar desde {m.group(1)}.")
        # sugerencias que estaban activas en la revisión anterior y ya no se ven en los datos
        antes = set(wiki.estado("lint_sugerencias_activas", []))
        ahora_activas = {s["clave"]: s for s in sugerencias.activas()}
        with sugerencias._db() as con:
            textos = dict(con.execute("SELECT clave, texto FROM sugerencias"))
        for clave in sorted(antes - set(ahora_activas)):
            avisos.append(f"Ya no se ve en los datos: «{textos.get(clave, clave)}». Dejé de sugerirla.")
        wiki.fijar_estado("lint_sugerencias_activas", sorted(ahora_activas))
        for rel in wiki.paginas_sueltas():
            avisos.append(f"Página suelta {rel}: si es tuya, muévela a mis_notas/; si es de fuera, a fuentes/. "
                          "Mientras tanto la ignoro.")
        for f in sorted(wiki.VAULT.rglob("*.md")):
            rel = f.relative_to(wiki.VAULT).as_posix()
            if rel.startswith((".obsidian/", ".git/")):
                continue
            motivo = wiki.motivo_sensible(f.read_text(encoding="utf-8", errors="replace"))
            if motivo:
                avisos.append(f"{rel}: contiene algo sensible ({motivo.split(' (')[0]}). Te propongo borrarlo; "
                              "no lo toco.")
        total = sum(Reflexion(None).contar(t["texto"]) for t in wiki.texto_reizo())
        if total > LIMITES["texto_reizo_tokens"]:
            avisos.append(f"Tu texto suma ~{total} tokens y al prompt de cada página entran {LIMITES['texto_reizo_tokens']}"
                          " (lo más relacionado y lo reciente). La comprobación sí revisa todo.")
        try:
            wiki.escribir_indice(ahora)
        except wiki.Pospuesto:
            pass
        return arreglos, avisos

    # ----- parte del modelo -----

    def contradicciones(self, r, ahora):
        fijas = wiki.congeladas()
        frases = []  # (pagina, seccion, frase)
        for pid in ("perfil", "habitos", "apps", "rutinas"):
            pagina = wiki.leer(pid)
            for s in PAGINAS[pid]["secciones"]:
                if s["autor"] == "modelo" and (pid, s["id"]) not in fijas:
                    texto = pagina["secciones"].get(s["id"], {}).get("texto", "")
                    frases += [(pid, s["titulo"], l[2:]) for l in texto.splitlines() if l.startswith("- ")]
        tuyos = [(m["fecha"], m["dato"]) for m in memoria.memorias_para_reflexion()]
        tuyos += [(datetime.fromtimestamp(t["mtime"]).strftime("%Y-%m-%d %H:%M"), f"{t['origen']}: {t['texto'][:300]}")
                  for t in wiki.texto_reizo()]
        if not frases and len(tuyos) < 2:
            return []
        datos = preparar_datos(ahora, r.clasificador)
        patrones = "\n".join(f"- {p}" for p in datos["patrones"]) or "(ninguno)"
        n, m = max(len(frases), 1), max(len(tuyos), 1)
        contenido = (
            "<<<FRASES DEL ASISTENTE>>>\n" + "\n".join(f"{i}. [{p}/{s}] {f}" for i, (p, s, f) in enumerate(frases, 1)) +
            "\n<<<FIN>>>\n\n<<<LO TUYO (Reizo; con fecha)>>>\n" +
            "\n".join(f"T{i}. ({fecha}) {t}" for i, (fecha, t) in enumerate(tuyos, 1)) +
            f"\n<<<FIN>>>\n\n<<<PATRONES MEDIDOS ESTA SEMANA>>>\n{patrones}\n<<<FIN>>>\n\n"
            "Busca: (a) 'contradiccion': frases del asistente que se contradicen entre sí o con lo tuyo; "
            "(b) 'ya_no_se_ve': rutinas o hábitos de las frases que no aparecen en los patrones medidos; "
            "(c) 'entre_lo_tuyo': dos cosas de Reizo (T) que chocan entre sí. En 'frases' van números de frases del "
            "asistente; en 'tuyos', números de T. 'explicacion': una frase corta.")
        esquema = {"type": "object", "properties": {"problemas": {"type": "array", "maxItems": 6, "items": {
            "type": "object", "properties": {
                "tipo": {"type": "string", "enum": ["contradiccion", "ya_no_se_ve", "entre_lo_tuyo"]},
                "frases": {"type": "array", "maxItems": 3, "items": {"type": "integer", "enum": list(range(1, n + 1))}},
                "tuyos": {"type": "array", "maxItems": 2, "items": {"type": "integer", "enum": list(range(1, m + 1))}},
                "explicacion": {"type": "string", "maxLength": 150}},
            "required": ["tipo", "frases", "tuyos", "explicacion"]}}}, "required": ["problemas"]}
        salida = r._completar([{"role": "system", "content": SISTEMA}, {"role": "user", "content": contenido}],
                              esquema, 700)
        lineas = []
        for p in salida.get("problemas", []):
            fs = [frases[i - 1] for i in p.get("frases", []) if 1 <= i <= len(frases)]
            ts = [tuyos[i - 1] for i in p.get("tuyos", []) if 1 <= i <= len(tuyos)]
            explicacion = wiki.limpiar_frase(p.get("explicacion", ""))
            if wiki.motivo_sensible(explicacion):
                explicacion = ""
            citas = "; ".join(f"«{f}» ([[{pg}]])" for pg, _, f in fs)
            if p.get("tipo") == "entre_lo_tuyo" and len(ts) == 2:
                reciente = max(ts)
                lineas.append(f"Dos cosas tuyas parecen chocar: «{ts[0][1][:120]}» ({ts[0][0][:10]}) y "
                              f"«{ts[1][1][:120]}» ({ts[1][0][:10]}). Uso la más reciente ({reciente[0][:10]}) "
                              "mientras no me digas otra cosa.")
            elif p.get("tipo") == "ya_no_se_ve" and fs:
                lineas.append(f"Ya no se ve en los datos: {citas}. {explicacion}".strip())
            elif fs:
                lineas.append(f"Posible contradicción: {citas}. {explicacion}".strip())
        return [l for l in lineas if not wiki.motivo_sensible(l)]

    # ----- todo -----

    def ejecutar(self, llm, parar=None, comprobar_emergencia=None, ahora=None, motivo=lambda: "actividad"):
        ahora = ahora or datetime.now()
        r = Reflexion(llm, parar=parar, comprobar_emergencia=comprobar_emergencia, motivo=motivo)
        wiki.asegurar_vault(ahora)
        wiki.guardar_ediciones_reizo()
        arreglos, avisos = self.mecanicos(ahora)
        try:
            contradicciones = self.contradicciones(r, ahora) if llm is not None else []
        except ReflexionDetenida as e:
            wiki.anotar("lint_detenido", str(e), ahora)
            wiki.commit(f"Lint {ahora:%Y-%m-%d} (parcial)")
            return {"terminada": False, "detenida": str(e)}
        mecanicos = arreglos + avisos
        secciones = {"mecanicos": wiki.viñetas(mecanicos) if mecanicos else "(Nada que revisar.)",
                     "contradicciones": wiki.viñetas(contradicciones) if contradicciones else "(Ninguna.)"}
        try:
            wiki.escribir("revision", secciones, {"actualizado": f"{ahora:%Y-%m-%d %H:%M}",
                                                  "resumen": f"Revisión del {ahora:%Y-%m-%d}: "
                                                             f"{len(avisos) + len(contradicciones)} cosas para revisar."},
                          ahora)
        except wiki.Pospuesto as e:
            wiki.anotar("pospuesto", str(e), ahora)
            return {"terminada": False, "pospuesto": str(e)}
        pendientes = len(avisos) + len(contradicciones)
        wiki.fijar_estado("ultimo_lint", f"{ahora:%Y-%m-%d %H:%M}")
        wiki.fijar_estado("revision_por_avisar", pendientes)
        wiki.anotar("lint", f"{len(arreglos)} arreglos, {len(avisos)} avisos, {len(contradicciones)} posibles "
                            "contradicciones (ver [[revision]])", ahora)
        wiki.commit(f"Lint {ahora:%Y-%m-%d}")
        return {"terminada": True, "arreglos": arreglos, "avisos": avisos, "contradicciones": contradicciones}


def aviso_de_revision():
    """Una línea para el inicio de sesión si el último lint dejó cosas para revisar (se avisa una sola vez)."""
    n = wiki.estado("revision_por_avisar", 0)
    if not n:
        return None
    wiki.fijar_estado("revision_por_avisar", 0)
    return f"Hay {n} {'cosa' if n == 1 else 'cosas'} para revisar en la wiki (revision.md)."
