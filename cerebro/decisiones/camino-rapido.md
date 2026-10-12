---
estado: verificado
verificado_commit: 76250a2
verificado_fecha: 2026-10-11
fuentes: [camino_rapido.py, agente_minimo.py, voz.py, benchmark_gramatica.py, probar_camino_rapido.py, pruebas.json, comparacion_modelos/pruebas_nuevas_30.json]
---
# Camino rápido: pedidos simples sin el modelo

**Estado: implementado (fdf84d1, 2026-10-11)**, por decisión del usuario, con las ampliaciones y el volumen en la
pausa del modo juego. **Falta la 65 × 3 de los dos modelos**: espera a que la GPU esté libre (el usuario está
jugando). Sigue [[estrategia-recursos]]: el modelo decide; el código hace.

## Qué pedidos entran (`camino_rapido.py`, lista blanca)

| Frase entera (sin tildes) | Herramienta y argumentos | Banco |
|---|---|---|
| «sube / baja el volumen [un poco]» | `volumen` subir / bajar 10 | #1, #2 |
| «pon / deja / ajusta el volumen al N» (cifras o palabras, 0–100), «… al máximo» | `volumen` fijar | #3, #7, #101 |
| «silencia [el sonido / el volumen / el equipo]» | `volumen` silenciar | #4 |
| «quita el silencio», «(vuelve a) activa el audio / el sonido» | `volumen` activar | #5, #103 |
| «¿a cuánto está el volumen?» | `volumen` consultar | #6 |
| «abre / inicia (la aplicación de) X» | `abrir_app` X, solo si `resolver_app_rapido` lo da | #8–12, #104 |
| «deja de registrar lo que hago», «reanuda el registro de mis hábitos» | `registro_habitos` | #65, #130 |

**17 de las 95 frases** ([[frases-simples]]).

`abrir_app` entra solo si el nombre no es genérico (`es_generico`) y si `elegir_app` lo resuelve sin error ni dudas.
Además, el nombre no puede tener «y», «en», «con», «no», «si», «otra vez», URLs ni extensiones.

Ante la duda, al modelo:
- negaciones y condiciones;
- pedidos compuestos o con varias apps;
- rutas, URLs y números fuera de rango;
- cualquier palabra de más.

Normaliza tildes, mayúsculas, «Cacao,», «por favor» y la puntuación final. Solo mira el pedido del usuario (isla o
voz), nunca texto externo.

## Mismo ejecutor

- `atender()`: tras `emergencia.detenido()` y antes del modelo, `paso_rapido()` ejecuta con el mismo `ejecutar()`:
  permisos, planificadores, modo sin confirmación, confirmación física, [[frenos-cierre]] y
  `emergencia.comprobar()`.
- Al historial va como si el modelo hubiera elegido la acción (acción, resultado y `finalizar`).
- Responde con un texto fijo que usa el resultado **verificado** («Listo, puse el volumen al 30%», «Listo, abrí
  Spotify»).
- Si el resultado no se verifica, sigue el modelo. Un rechazo o un bloqueo termina como hoy.
- **Interruptor:** `CAMINO_RAPIDO = CONFIG.get("camino_rapido", True)`. Hoy `config.json` no tiene la clave: está
  activo.
- **Registro:** `[camino rápido] <herramienta>`, sin el texto del pedido. `resumir_semana_qwen.py` lo cuenta.

## Modo juego (pausa)

- Solo el volumen: `atender_con_memoria` llama a `atender(..., en_pausa=True)`, que no reserva ni carga el modelo y
  no usa la GPU.
- `voz.filtrar` deja pasar solo esas frases a la transcripción de la CPU.
- Lo demás sigue con el aviso de pausa. Si el volumen falla, responde «No pude hacerlo durante la pausa del modo
  juego.», sin el modelo.
- `guardia_juego` no cambia.

## Pruebas

- `probar_camino_rapido.py` 456/456:
  - las 17 frases y sus variantes;
  - más de 50 frases que no deben entrar;
  - el agente (mismo ejecutor, historial, sin verificar → modelo, rechazo, bloqueo, atajo de emergencia,
    interruptor);
  - el modo juego;
  - 8 mutaciones detectadas (quitar cada freno hace fallar alguna prueba).
- **Pendiente:** 65 × 3 de `gemma` y de `qwen9b` (`probar_swa_cache.py --perfil`). Criterio del coordinador: Gemma
  195/195; Qwen no peor que 182/195 y sin casos (c) nuevos.

**Ganancia esperada:** con el modelo, esas frases tardaban de media 1,82 s con Gemma y 6,09 s con Qwen
(`datos/swa_cache/*cierre_C.json` y `*contrato_A.json`); por este camino solo cuenta el tiempo de la herramienta.
No cambia el prompt ni el esquema.
