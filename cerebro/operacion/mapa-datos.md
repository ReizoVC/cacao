---
estado: verificado
verificado_commit: 8a78d51
verificado_fecha: 2026-10-10
fuentes: [.gitignore, config.json, memoria.py, wiki.py, habitos.py, voz.py, ui_isla.py, iniciar_cacao.py]
---
# Mapa de datos por rol

## Datos personales: no leer, no copiar, no commitear

| Rol | Dónde (relativo a la raíz o según config) | Lo escribe |
|---|---|---|
| Memorias, obstáculos, sugerencias | `memoria.db` | `memoria.py`, `obstaculos.py`, `sugerencias.py` |
| Hábitos (muestras y resúmenes) | `habitos.db` (`memoria_wiki.habitos_db`) | `registro_habitos.py` |
| Wiki personal (vault con su propio git) | `memoria/` (`memoria_wiki.vault`) | `reflexion.py`, `lint.py`, el usuario |
| Datos locales (apps de banco y otros) | `datos_locales.json` | el usuario |
| Catálogo de apps instaladas | `apps_categorias.json` | `agente_minimo.sincronizar_apps` |
| Grabaciones y registro de voz | `voz_registro/` | `voz.py` |
| Grabaciones de prueba | `voz_pruebas/` | `grabar_*.py` |
| Diagnósticos del PC | `diagnostico/` | scripts de diagnóstico |
| Contador de activaciones | `contador_cacao.json` | `palabra_activacion.py` |
| Registros de ejecución | `registro_cacao.log`, `registro_habitos.log` | el lanzador y el registrador |
| Historial de movimientos | `historial_movimientos.json` | `herramientas_grupo4.py` (mover_archivo) |
| Resultados de pruebas reales | `resultados_*.json` y `resultados_*.md` de la raíz | pruebas (pueden listar apps, ventanas y archivos) |
| Token de la isla | `%LOCALAPPDATA%\Asistente\ui.json` (se borra al salir) | `ui_isla.py` |

Todo lo que está dentro del repositorio figura en `.gitignore`. Los informes `resultados_*.md` que sí están en Git
se añadieron a mano con `-f` y están sanitizados.

## Datos de prueba: se pueden usar

- `memoria_prueba.db`, `habitos_prueba.db` y las carpetas `memoria_prueba*`. Las crean y borran las suites.
- `pruebas.json`, `comparacion_modelos/pruebas_nuevas_30.json` y `comparacion_modelos/capturas/` (aplicaciones de
  prueba).
- Los `metricas_*.json` y `resumen_*.json` de `comparacion_modelos/`: sanitizados, en Git.

## Modelos (pesados, fuera de Git)

| Rol | Dónde |
|---|---|
| LLM de producción y mmproj | `modelos/` (rutas en `config.json`) |
| Piper y detector «Cacao» | `modelos/piper/`, `modelos/cacao/` (`cacao.npz` es el de producción) |
| Datos para entrenar «Cacao» (`acav_parcial.npy`, `validation_set_features.npy`, voces de `piper_cacao/`) | Movidos a `D:\Cacao\entrenamiento\` el 2026-10-10. `entrenar_cacao.py` todavía los busca en `modelos/` ([[backlog]]) |
| Qwen 3.5 9B Q5 para la prueba | Copia en `modelos/comparacion_local/` (C:); `ejecutar.py` la usa |
| Candidatos de comparación | `modelos/comparacion/` es una **unión (junction) a `D:\Cacao\ModelosComparacion`**: los GGUF viven solo en D: (disco duro), no ocupan C: |
| Whisper | caché de Hugging Face del perfil del usuario |
| Pila WSL (TTS, motores) | disco D y `/opt` dentro de WSL ([[wsl-dominio-cuda]]) |

No muevas los modelos que producción espera en `modelos/` sin cambiar y validar `config.json`. D: es un disco duro:
solo copias y lo que no se usa. Registro de cada movimiento con SHA256: `D:\Cacao\manifiesto_movimientos.md`.
