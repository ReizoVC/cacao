---
estado: sin verificar
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
fuentes: [comparacion_modelos/ronda3_protocolo.md, comparacion_modelos/resumir_ronda3.py, config.json]
---
# Criterio para cambiar de modelo y para volver a Gemma Q5

Producción es Gemma Q5 ([[configuracion-vigente]]). «Volver a Gemma» significa volver a Q5 en llama-cpp-python
0.3.36 si un candidato (Q4, otro motor u otro modelo) falla después de adoptarlo.

**Estado de esta página:** solo el criterio de la ronda 3 está en un archivo (`ronda3_protocolo.md`). El resto es
una propuesta derivada de las decisiones registradas y **el usuario no lo ha aprobado**.

## Criterio fijado y escrito (`ronda3_protocolo.md`)

Para que un candidato pase, con las 65 frases × 3 semillas y el mismo prompt y esquema:
- ≥ 192/195 tareas completas;
- 0 respuestas vacías;
- 0 confirmaciones falsas finales;
- 0 acciones distintas a lo pedido.

Además, Gemma Q5 no debe bajar de su resultado.

## Propuesta para adoptar un candidato en producción (pendiente de aprobación)

1. Pasar el criterio anterior **con el prompt y el esquema de producción**, no solo con el contrato de pruebas.
2. Tener la evaluación a ciegas de la conversación puntuada por el usuario.
3. Que las suites sin modelo sigan en verde ([[suites]]).
4. Margen de VRAM con voz y visión ≥ el actual, medido con picos simultáneos.
5. Una semana de uso real sin regresiones visibles ([[pendientes-presenciales]]).

## Propuesta para volver a Gemma Q5 (pendiente de aprobación)

Volver a la configuración anterior (`config.json` y el motor) si ocurre cualquiera de estas:
- una acción distinta a lo pedido o una confirmación falsa en uso real;
- un fallo de carga o una caída del endpoint sin recuperación;
- pérdida de margen de VRAM que haga fallar el modo juego o Whisper;
- el usuario prefiere la conversación de Q5 en la evaluación a ciegas.

Para que la vuelta sea inmediata:
- conservar el GGUF de Q5 en `modelos/`;
- no tocar `.venv` sin una copia;
- hacer el cambio con un solo commit de `config.json`.
