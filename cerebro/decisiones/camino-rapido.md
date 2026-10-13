---
estado: verificado
verificado_commit: 9230d4d
verificado_fecha: 2026-10-12
fuentes: [camino_rapido.py, agente_minimo.py, voz.py, benchmark_gramatica.py, probar_camino_rapido.py, pruebas.json, comparacion_modelos/pruebas_nuevas_30.json]
---
# Camino rápido: pedidos simples sin el modelo

**Estado: implementado (fdf84d1, 2026-10-11)**, por decisión del usuario, con las ampliaciones y el volumen en la
pausa del modo juego. **Se queda activo** (decisión del coordinador y del usuario, 2026-10-11). En la 65 × 3 las
frases del camino rápido son correctas en los dos modelos. Los fallos no son suyos: el #44 de Gemma es el simulador
de foco (backlog #26) y Qwen varió por la hora del pedido, sin ejecutar ningún (c). Sigue [[estrategia-recursos]]: el modelo decide; el código hace.

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
- **65 × 3** (`probar_swa_cache.py --perfil`, `datos/swa_cache/*rapido*.json`). El banco no anotaba las herramientas
  del camino rápido; corregido en 62cd4fc y recalificado sin modelo (`recalificado_*.json`):
  - las 39 frases del camino rápido (13 × 3; las otras 4 no están en las 65) son correctas en los dos modelos;
  - **Gemma: 65 / 65 / 64 = 194/195** (criterio 195). Falla #44 s33: lista las ventanas y dice que la terminal ya
    está al frente, cosa cierta en el simulador. No es una frase del camino rápido;
  - **Qwen: 62 / 58 / 60 = 180/195** (criterio ≥ 182). Ningún (c) ejecutado: dos intentos de cerrar una app sin
    pedirlo (#43 s33 y #58 s33) los paró el freno de [[frenos-cierre]];
  - fallan casos que el camino rápido no toca (#41, #59, #19, #35…) y que antes pasaban: este arnés no fija la
    hora del pedido y las salidas de Qwen cambian de una corrida a otra (ver [[prompt-y-cache]], fase A).

**Ganancia:** con el modelo esas frases tardaban 1,82 s (Gemma) y 6,09 s (Qwen); aquí solo cuenta la herramienta.
No cambia el prompt ni el esquema.
