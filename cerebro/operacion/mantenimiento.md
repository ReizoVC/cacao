---
estado: verificado
verificado_commit: a57d633
verificado_fecha: 2026-10-11
fuentes: [CLAUDE.md, cerebro/frescura.py, wiki.py, memoria.py, herramientas_grupo1.py, herramientas.json]
---
# Mantenimiento del cerebro

## Chequeo de frescura

```
python -I cerebro/frescura.py          # solo las páginas por revisar
python -I cerebro/frescura.py --todo   # todas
```

Es de solo lectura: solo ejecuta `git log`, `git status`, `git ls-files` y `git rev-parse` y lee archivos. Avisa
cuando:
- una fuente en Git tiene commits posteriores a `verificado_commit`, o cambios sin commit;
- una fuente fuera de Git (ignorada) se modificó después de la fecha del commit verificado;
- una fuente ya no existe;
- faltan campos del frontmatter o el estado no es válido;
- hay un enlace `[[...]]` roto;
- una página pasa de unos 1.500 tokens. Es una estimación (caracteres / 3,2), no el tokenizador real.

Sale con 1 si hay algo por revisar.

## Qué hacer con un aviso

1. Lee el diff de la fuente (`git log -p <commit>..HEAD -- <fuente>`).
2. Si la página sigue siendo correcta, solo actualiza `verificado_commit` y `verificado_fecha`.
3. Si no, corrígela. Si no puedes comprobarla, `estado: sin verificar`; si ya no aplica, `obsoleto`.
4. Añade una entrada a [[log]].

## Formato de página

```
---
estado: verificado | sin verificar | obsoleto
verificado_commit: <hash del código comprobado>
verificado_fecha: AAAA-MM-DD
fuentes: [ruta/relativa.py, otra.json]
---
```

- Menos de 1.500 tokens; si crece, divídela y actualiza [[index]].
- Enlaces por nombre de archivo: `[[suites]]`.
- Nada de datos personales, rutas con el nombre de usuario, tokens ni credenciales.

## Seguridad: Cacao no lee el cerebro

Comprobado en el código el 2026-10-10:
- `consultar_memoria` y la wiki solo recorren `memoria.db` y `memoria/`;
- las herramientas de archivos solo trabajan en las carpetas del perfil.

La única vía teórica es `ejecutar_powershell`, que exige confirmación física, o ver una página abierta en pantalla
([[riesgos]]). Si algún día se amplían `carpetas_permitidas` o el vault de la wiki, vuelve a comprobarlo.

## Revisión de privacidad

Antes de un commit del cerebro:

```
git grep -n -i -E "users[\\/]|@[a-z0-9-]+\.(com|net)|password|contraseña|token" -- cerebro CLAUDE.md
```

Revisa cada coincidencia: puede ser legítima (por ejemplo, «token de la isla» como concepto).
