---
estado: verificado
verificado_commit: d95855d
verificado_fecha: 2026-10-11
fuentes: [registro_habitos.py, habitos.py, agente_minimo.py, config.json, diseno_fase6.md]
---
# Registro de hábitos

## Proceso (`registro_habitos.py`)

- Proceso aparte, sin modelo, de una sola instancia (mutex con nombre).
- Cada `memoria_wiki.muestreo_s` = 30 s guarda en `habitos.db`:
  - la app al frente (ejecutable o AppID);
  - su categoría;
  - el estado: `activo`, `inactivo` (sin entrada física durante `inactivo_min` = 5 min; ver [[entrada-fisica]]) o
    `bloqueado`.
- Se arranca con `.venv\Scripts\pythonw registro_habitos.py`. Los errores van a `registro_habitos.log`.

## Privacidad (`habitos.py`)

- **Títulos:** nunca se guardan. El título solo se lee en memoria para detectar el modo incógnito, y se descarta.
- **Apps sin fila** (el hueco queda igual que con el registrador apagado):
  - privadas: `procesos_privados` y `appids_privados`, y la lista de apps de banco de los datos locales;
  - ventanas de incógnito.
- **Muestras:** inmutables. Se borran a los `conservar_dias` = 30 días, después de resumirlas en `resumen_diario`.
- `periodos_dudosos`: tramos con muestras poco fiables.

## Pausa

- La herramienta `registro_habitos` (permiso libre) crea o borra el archivo `PAUSA_HABITOS`. Mientras existe, no se
  muestrea.
- En una tarea contaminada, pide confirmación ([[permisos-y-bloqueos]]).

## Consumidores

- La reflexión y las sugerencias ([[memoria-y-wiki]]).
- `simular_habitos.py` genera días simulados en `habitos_prueba.db` para probar sin datos reales.

## No hacer

No abras `habitos.db`: son datos personales ([[mapa-datos]]). Para probar, usa `simular_habitos.py` y las bases
`*_prueba*`.
