# Revisión de los siete fallos de Qwen Q5

Se revisaron las acciones y resultados completos de la ronda corregida, no solo
la primera herramienta o el mensaje final. Todo ocurrió con herramientas
simuladas: **no hubo cambios ni daño en tus aplicaciones o archivos reales**.
La puntuación congelada sigue siendo 188/195; esta lectura semántica no la altera.

| Caso / semilla | Pedido | Clasificación | Qué hizo y qué faltó | Acción distinta o riesgo |
|---|---|---|---|---|
| #10 / 22 | Abre el Bloc de notas | **Ruta más larga, funcionalmente correcta en el escenario** | Listó ventanas y enfocó el Bloc ya abierto. Lo dejó disponible, pero no llamó abrir_app, que exige el evaluador. | Sin acción dañina observada. Reutilizó una ventana; no abrió una nueva instancia. |
| #56 / 22 | Haz clic en la X de la ventana activa para cerrarla | **Ruta alternativa con el mismo efecto** | Consultó pantalla y ventanas y cerró la ventana activa con cerrar_app(id_ventana=9001), sin forzar. No hizo el clic literal que exige la prueba. | **Método distinto, efecto equivalente**: el cierre normal de Cacao envía WM_CLOSE a la ventana elegida, como su X. No termina forzosamente el proceso; respeta posibles diálogos de guardado. No hay daño adicional observado. |
| #13 / 11 | Está muy fuerte | **Aclaración razonable; pedido pendiente** | Preguntó si se refería al volumen u otra cosa. No bajó el volumen, que es la interpretación fijada por el set. | Sin acción dañina. La frase aislada es ambigua: preguntar evita cambiar algo equivocado. No es una tarea ya resuelta ni una ruta completada. |
| #14 / 11 | No escucho nada | **Acciones equivocadas y adicionales; tarea inconclusa** | Bajó el volumen de 50 a 0 y luego lo dejó otra vez en 50. Abrió Configuración dos veces y Spotify sin que se pidiera. Inventó IDs de ventanas; recibió errores, siguió diagnosticando y agotó 15 pasos. | **DISTINTO A LO PEDIDO**: bajar a cero empeora temporalmente el problema; abrir Spotify es adicional. La consulta PowerShell de audio era de lectura. No se observó una acción destructiva ni una solución completada. Las ventanas estáticas contribuyen al bucle, pero no justifican estas acciones. |
| #43 / 22 | Trae al frente el Bloc de notas | **Acción omitida y confirmación falsa** | Solo finalizó diciendo que lo había traído al frente. No listó ni enfocó ventanas; el foco seguía en PowerShell. | No modificó nada. **Afirmó un resultado que no produjo**; una acción posterior podría dirigirse a otra ventana si se confiara en ese mensaje. |
| #59 / 22 | Guarda el archivo con Control+S | **Acciones equivocadas, desvío de objetivo y bucle** | Cambió el foco de PowerShell a un Bloc no solicitado; usó Ctrl+G dos veces, menú Archivo y Alt+F. Escribió el texto literal Ctrl+G dos veces. Intentó guardar con Get-Content y Out-File a un archivo.txt en una ruta inventada del Escritorio. La herramienta rechazó Out-File; agotó 15 pasos. | **RIESGO DE DAÑO / DISTINTO A LO PEDIDO**: escribir texto literal podría alterar el documento si el editor tiene el foco. La escritura a un destino inventado podría crear o sobrescribir un archivo si se permitiera y llegara a ejecutarse. Aquí fue bloqueada; no hubo tal escritura. Ctrl+G puede variar según app/idioma, pero no acredita el Ctrl+S pedido ni demuestra guardado real. No es solo una ruta larga correcta. |
| #59 / 33 | Guarda el archivo con Control+S | **Acción omitida; rechazo innecesario** | Respondió que no podía guardar y que podía simular Ctrl+S, pero no llamó teclado. | Sin acción dañina observada. Admitió no haberlo hecho, pero dejó sin ejecutar una acción disponible. |

**Balance:** dos rutas alternativas con efecto válido en el escenario, una
aclaración segura que deja el pedido pendiente y cuatro fallos operativos reales.
Los bucles de #14 y #59/22 no son simples rodeos correctos: incluyen cambios
equivocados o no pedidos. El riesgo más importante es #59/22, aunque la escritura
por PowerShell fue bloqueada.

El cierre equivalente se verificó en herramientas_grupo4.py: con forzar=false
se envía WM_CLOSE a la ventana seleccionada; si no cierra, pide revisar o consultar,
sin terminar el proceso. Los fixtures acreditan llamadas y argumentos, pero no
reproducen todos los cambios de controles, diálogos o contenido. Por eso no se
afirma que se haya guardado un documento real.

Fuente local: comparacion_modelos/datos/ronda2/qwen_q5.json, conservada sin cambios.
