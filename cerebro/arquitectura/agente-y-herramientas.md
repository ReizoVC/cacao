---
estado: verificado
verificado_commit: 62cd4fc
verificado_fecha: 2026-10-11
fuentes: [agente_minimo.py, herramientas.json, herramientas_grupo1.py, herramientas_grupo4.py, herramientas_powershell.py, vision.py, memoria.py, benchmark_gramatica.py]
---
# Agente y herramientas

## Catálogo

`herramientas.json` define 23 herramientas (nombre, descripción, parámetros y `permiso`) y los `limites`.
`agente_minimo.py` activa las que están en `ACTIVAS`:
- `ver_pantalla` sale si no hay `mmproj`;
- `autocompletar_login` solo entra con `config.autocompletar_login.activa` (hoy `false`).

| Grupo | Herramientas | Implementación |
|---|---|---|
| Apps y sistema | listar_apps, abrir_app, volumen | `agente_minimo.py` |
| Ventanas, archivos, web | listar_ventanas, enfocar_ventana, listar_carpeta, leer_archivo, buscar_web | `herramientas_grupo1.py` |
| Visión | ver_pantalla | `vision.py` (Gemma4ChatHandler + mmproj) |
| Interfaz y archivos con efecto | cerrar_app, mover_archivo, deshacer_movimiento, mouse, teclado, listar_controles | `herramientas_grupo4.py` |
| PowerShell | ejecutar_powershell | `herramientas_powershell.py` |
| Memoria | recordar, consultar_memoria | `memoria.py` (+ `wiki.buscar`) |
| Fase 6 | sugerencias, registro_habitos | `sugerencias.py`, `agente_minimo.registro_habitos` |
| Diálogo | preguntar_usuario, finalizar | el propio bucle |

## Estructuras clave en `agente_minimo.py`

- `IMPLEMENTACIONES`: nombre → función.
- `PLANIFICADORES`: comprobaciones sin efecto antes de pedir confirmación (PowerShell, teclado,
  autocompletar_login).
- `ACCIONES_A_VERIFICAR` y `VERIFICADORAS`: clics y atajos que hay que comprobar con listar_controles,
  ver_pantalla o listar_ventanas.
- `TEXTO_EXTERNO`: herramientas cuyo resultado marca la tarea como «contaminada».
- `GUARDAN_SOBRE_REIZO`: recordar, sugerencias y registro_habitos, que piden confirmación si la tarea está
  contaminada.
- `atender()` prueba antes el [[camino-rapido]] (`paso_rapido`, `CAMINO_RAPIDO`).
- `ESQUEMA_ACCION`: `{pensamiento ≤120, herramienta (enum), argumentos, mensaje_final opcional}`. `mensaje_final`
  se valida como `finalizar` y `CIERRE_RAPIDO` (perfil de `config.json`) puede apagarlo ([[cierre-rapido-mensaje-final]]).
- Con `contrato_ronda2` (solo perfil qwen9b), `contrato_ronda2.aplicar(globals())` cambia `prompt_sistema`,
  `HERRAMIENTAS` y `ESQUEMA_ACCION` como el banco de la ronda 2 ([[configuracion-vigente]]).
- `prompt_sistema(voz)`: reglas, catálogo y memorias para el prompt. En modo voz añade `MODO_VOZ`.

## Añadir una herramienta nueva (lista de cambios)

1. `herramientas.json`: la entrada con su `permiso` (libre o confirmar). Si es peligrosa, mejor no
   añadirla (ver `acciones_prohibidas`).
2. La implementación en un módulo; si tiene efecto, sepárala en `planificar_*` + ejecución, como el grupo 4.
3. `agente_minimo.py`: añádela a `ACTIVAS` e `IMPLEMENTACIONES`; si corresponde, a `PLANIFICADORES`,
   `ACCIONES_A_VERIFICAR`, `TEXTO_EXTERNO` o `GUARDAN_SOBRE_REIZO`.
4. `voz.py`: si es de solo lectura, añádela a `SOLO_LECTURA`; si no, la voz pedirá confirmación.
5. `modo_directo.py`: decide si puede ir sin confirmación en ese modo (por defecto, no).
6. `protecciones_ejecucion.py`: si produce efectos que el modelo podría afirmar, añade su patrón a `_CLAIMS` y su
   comprobación a `resultado_verificado`.
7. Simulación: añádela a las herramientas simuladas de `benchmark_gramatica.py`, frases a `pruebas.json` y una
   suite `probar_*.py` sin modelo.
8. Vuelve a pasar las 65 frases × 3 semillas: cambiar el prompt cambia el comportamiento ([[evaluacion-65-frases]]).
9. Actualiza [[permisos-y-bloqueos]], esta página y [[mapa-archivos]].

Ver también [[vision-general]] y [[protecciones]].
