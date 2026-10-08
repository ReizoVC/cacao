# Ronda 2: protocolo fijado antes de las tandas completas

## Aceptación

Qwen Q5 necesita **al menos 186 de 195 tareas completas (95 % redondeado hacia
arriba)**, **cero respuestas finales vacías en las 195 tareas y las 10 preguntas**,
y no empeorar en español según la evaluación humana a ciegas. La condición humana
queda pendiente hasta que el usuario entregue sus puntuaciones; no se declara
aprobación completa por un resultado automático favorable.

## Comparación

Gemma 4 12B Q5_K_M y Qwen 3.5 9B UD-Q5_K_XL, archivos ya descargados.
65 frases originales sin editar, semillas 11, 22 y 33, mismas diez preguntas de
conversación. Contexto 16.384, flash attention, K/V q8_0, temperatura 0,3,
top_k 64, top_p 0,95 y herramientas simuladas como en la primera ronda.
No se añaden acciones esperadas al prompt ni se reintenta selectivamente un fallo.

Cambios comunes: instrucciones explícitas para finalizar con argumentos.mensaje,
continuar todas las acciones pendientes y no tratar un consejo como autorización
para cambiar ajustes. La gramática exige mensaje no vacío y los parámetros de
finalizar, y excluye mensaje_final en TODAS las acciones. Desactiva el cierre
rápido y siempre requiere finalizar; no comprueba semánticamente que todo esté completo. Ambos
modelos reciben los mismos cambios. Codificación UTF-8 de stdout/stderr para que
los registros no aborten por caracteres fuera de CP1252.

Plantilla: nativa de cada GGUF; para Qwen se mantiene enable_thinking=false y se
comprueba el sufijo exacto de generación con bloque think ya cerrado. La primera
ronda ya lo desactivaba: no se atribuyen a pensamiento activado los fallos sin
evidencia. Diagnóstico factorial en 12 observaciones originales: base con registro
UTF-8, solo prompt, solo esquema, ambos. Es análisis exploratorio sobre el set
conocido; el resultado posterior no prueba generalización a tareas nuevas.
El primer piloto encontró omisiones persistentes con el cierre rápido. Una tanda
parcial de Gemma fue detenida y archivada, sin puntuarla. Antes de la tanda
definitiva se fijó desactivar ese atajo para ambos; se informa el coste temporal.
La primera tanda de Gemma con ese contrato acreditó 188/195 y fue rechazada como
ajuste común por empeorar su referencia de 190/195. Antes de la comparación final
se aclaró abrir_app directamente frente a enfocar para actuar dentro de una app,
y la descripción de la rueda (-10 a 10; negativo abajo, positivo arriba) conforme
a herramientas_grupo4.py. Ambas aclaraciones se aplican a los dos modelos.
La tanda descartada y sus diagnósticos quedan en datos/piloto_ronda2_v2.

El siguiente piloto completó Gemma con 195/195, pero Qwen generó un salto de línea
literal dentro de pensamiento (#14, semilla 22), con JSONDecodeError y respuesta
vacía. La regla char del convertidor JSON-schema de llama-cpp-python 0.3.36 era
`[^"\\]`: admitía controles JSON sin escapar. Antes de las nuevas tandas se
corrigió en memoria del ejecutor para excluir U+0000–U+001F (y DEL), igual para
ambos modelos. No se cambian archivos del motor ni se repara el texto generado:
json.loads sigue siendo estricto. El piloto V3 se conserva en datos/piloto_ronda2_v3
y no se acredita como resultado final. Se repiten ambos modelos con la regla
corregida y se congelan de nuevo las huellas antes de empezar.

Puntuación: mismos criterios de la ronda anterior salvo #44. Se corrige un falso
negativo: la terminal PowerShell ya enfocada (fixture 9001) acredita el pedido sin
necesidad de una llamada redundante para enfocarla. Se comprueba el efecto de la
lista de ventanas, no una palabra en el mensaje. Se recalculan AMBAS referencias
anteriores con este criterio para comparar en igualdad. No se atribuye ese fallo
del evaluador a capacidad del modelo.

Visión: mismas cinco tareas, capturas y rectángulos. Gemma recibe box_2d en orden
[y_min,x_min,y_max,x_max], escala 0–1000, según la documentación de Google.
Qwen recibe point_2d [x,y], escala 0–1000, siguiendo el cookbook de Qwen3-VL
(antecesor; no se encontró una especificación propia de Qwen3.5 para esta salida).
Se fija la conversión antes de medir: centro de la caja para Gemma y punto para
Qwen, en píxeles originales. Se mantienen presupuesto 1120, semilla 11 y temperatura
0,3. Son solo cinco tareas por modelo, sin ejecución de clics ni pantalla personal.

Fuentes consultadas:

- [Plantilla oficial Qwen3.5](https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/chat_template.jinja).
- [Visión Gemma y box_2d](https://ai.google.dev/gemma/docs/capabilities/vision/image).
- [Cookbook espacial Qwen3-VL](https://github.com/QwenLM/Qwen3-VL/blob/main/cookbooks/spatial_understanding.ipynb).

Los datos crudos nuevos quedan en datos/ronda2 (excluidos de Git). Se conserva la
primera ronda. Producción y .venv intactos; todo corre con .venv-pruebas.
