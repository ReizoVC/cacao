# Cacao — guía para Claude Code

Cacao es un asistente de escritorio para Windows, local y en español. Un LLM local con llama-cpp-python 0.3.36 (el que
diga `modelo_activo` en `config.json`: la referencia es Gemma 4 12B Q5_K_M; desde el 2026-10-11 Qwen 3.5 9B Q5 está
a prueba de uso una semana, ver `cerebro/decisiones/qwen-como-cerebro.md`) elige herramientas en JSON con gramática; un ejecutor en Python aplica permisos,
protecciones y confirmaciones físicas. Tiene voz (Whisper + Piper), palabra de activación «Cacao», una isla de
interfaz (repositorio aparte, C:\asistente-ui), modo juego, memoria tipo wiki y registro de hábitos.

Este archivo y `cerebro/` son para Claude Code. Cacao no los lee ni los indexa.

## Protocolo de lectura

1. Este archivo.
2. `cerebro/index.md`: el catálogo, una línea por página.
3. Solo las páginas que la tarea necesita (normalmente 1–3). El código gana si contradice una página: corrige la
   página y anótalo en `cerebro/log.md`.
4. Una página con `estado: sin verificar` o `obsoleto` no es un hecho: compruébalo en el código antes de actuar.

## Reglas permanentes

**Seguridad**
- No cargues modelos ni uses la GPU si hay un juego abierto (`guardia_juego.juego_abierto`). Si una prueba sale
  con «[GPU] … está abierto», avisa; no reintentes ni lo esquives.
- No ejecutes herramientas reales (volumen, apps, mouse, teclado, mover o cerrar, PowerShell, micrófono) salvo
  que el usuario esté presente y lo pida para esa prueba.
- No leas ni copies `memoria.db`, `habitos.db`, `datos_locales.json`, `apps_categorias.json`, `memoria/` (wiki
  personal), `voz_registro/`, `voz_pruebas/`, `diagnostico/` ni `contador_cacao.json`.
- Nunca pongas datos personales, credenciales, tokens ni rutas con el nombre de usuario en `cerebro/`, en commits o
  en informes.
- No toques `config.json`, `.venv/` ni el modelo de producción sin permiso explícito. Los experimentos van en
  `.comparacion-runtime/` y `comparacion_modelos/`.
- No reduzcas Whisper ni el contexto para ganar VRAM sin pedido expreso (ver `cerebro/decisiones/`).

**Cuándo pedir permiso**
- Antes de: cambiar producción (`config.json`, modelo, motor, prompt o esquema de `agente_minimo.py`), instalar
  paquetes, descargar o borrar modelos, tocar el arranque de Windows, usar administrador, hacer push, o activar
  funciones apagadas (`autocompletar_login`).
- Desde el teléfono (sesión remota): solo simulación, nada real, sin micrófono ni arranque; respuestas de 5–8
  líneas.

**Cómo probar**
- Siempre con herramientas simuladas: `SIN_REALES=1` y `CONFIRMAR=s` en `evaluar_pruebas.py` y
  `benchmark_gramatica.py`. Sin `SIN_REALES`, `listar_carpeta`, `leer_archivo` y `ver_pantalla` son reales.
- Las suites `probar_*.py` sin modelo van primero. Las que cargan Gemma o Whisper, solo con la GPU libre.
- Mapa de suites, comandos y baselines: `cerebro/pruebas/suites.md`.
- Un cambio en el prompt, el esquema o las herramientas obliga a volver a pasar las 65 frases × 3 semillas
  (`cerebro/pruebas/evaluacion-65-frases.md`).

**Forma de trabajar**
- No mezcles cambios: un commit por tema, sin datos crudos (`.gitignore` ya excluye datos y resultados; los
  informes que sí van se añaden con `git add -f`).
- Documentos en Markdown y en español.
- Informa cifras solo con su archivo de origen; lo que no puedas medir, dilo.

## Protocolo de actualización (al terminar cada tarea)

1. Actualiza las páginas de `cerebro/` afectadas por el cambio. En su frontmatter: `estado`, `verificado_commit`
   (commit del código que comprobaste), `verificado_fecha` y `fuentes`.
2. Si moviste, creaste o renombraste archivos, actualiza `cerebro/operacion/mapa-archivos.md` (y
   `mapa-datos.md` si cambian datos o rutas de modelos).
3. Si añadiste o quitaste páginas, actualiza `cerebro/index.md` (una línea por página).
4. Añade una entrada a `cerebro/log.md`: fecha, qué cambió y commit.
5. Commit del código y del cerebro (pueden ir en commits separados, pero en la misma tarea).
6. De vez en cuando: `python -I cerebro/frescura.py` (solo lectura) lista las páginas cuyas fuentes cambiaron
   después de su verificación (`cerebro/operacion/mantenimiento.md`).

Límites de cada página: menos de 1.500 tokens (si crece, se divide), enlaces `[[así]]`, estados
`verificado` / `sin verificar` / `obsoleto`.
