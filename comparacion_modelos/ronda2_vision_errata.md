# Corrección del rectángulo de visión, antes de la nueva tanda

Al revisar visualmente las dos capturas guardadas se detectó que el rectángulo
original del número 7 `[5,379,64,415]` correspondía a la tecla vecina `xʸ`.
El botón 7 está en la segunda columna: interior `[69,379,127,415]`.
Se corrige únicamente el rectángulo de evaluación, sin cambiar la captura,
el objetivo, los prompts de los modelos ni sus respuestas.

Las 40 localizaciones de referencia se vuelven a puntuar con este mismo
rectángulo para todos los candidatos. Se conserva la evidencia y puntuación
originales y se publica el recálculo por separado. La corrección se hizo antes
de ejecutar las 10 localizaciones nuevas con los formatos de cada familia.

Esta errata no modifica el protocolo de las 65 frases ni el umbral de aceptación.
Las huellas de visión quedan separadas en `ronda2_vision_congelada.json`.
