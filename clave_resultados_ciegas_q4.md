# Clave — abrir únicamente después de evaluar resultados_ciegas_q4.md

Correspondencia por pregunta; las letras no son constantes entre preguntas. Fuente: comparacion_modelos/datos/ronda3/gemma_q5_swa_false.json y gemma_q4_swa_false.json (llama-cpp-python 0.3.36, swa_full=False).

## Pregunta 1

- A: gemma_q5
- B: gemma_q4

## Pregunta 2

- A: gemma_q5
- B: gemma_q4

## Pregunta 3

- A: gemma_q4
- B: gemma_q5

## Pregunta 4

- A: gemma_q5
- B: gemma_q4

## Pregunta 5

- A: gemma_q5
- B: gemma_q4

## Pregunta 6

- A: gemma_q4
- B: gemma_q5

## Pregunta 7

- A: gemma_q4
- B: gemma_q5

## Pregunta 8

- A: gemma_q5
- B: gemma_q4

## Pregunta 9

- A: gemma_q5
- B: gemma_q4

## Pregunta 10

- A: gemma_q4
- B: gemma_q5

## Notas para después de evaluar

- Pregunta 6, gemma_q5: la primera respuesta (una explicación de la cuantización) fue rechazada por la protección de afirmaciones sin evidencia: la palabra «escrita» coincide con el patrón de teclado `escrit[oa]`. El modelo se desvió, llamó a listar_controles y listar_ventanas, y entregó la respuesta que aparece arriba. Es un falso positivo de la protección, no un fallo de generación inicial.
- Las respuestas de las rondas `_swa_false` y `_swa_false_nuevas30` son idénticas pregunta por pregunta para cada modelo; se usó la primera.
