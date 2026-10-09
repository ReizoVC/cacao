"""Pruebas puras: no abre apps ni envía mouse o teclado."""
import sys

import herramientas_grupo4 as g4
from protecciones_ejecucion import (afirmaciones_sin_evidencia, nueva_proteccion, parece_atajo,
                                    registrar_resultado, resultado_verificado, validar_finalizacion)

fallos=[]
ejecutadas=[]
def ok(nombre, condicion, detalle=""):
    ejecutadas.append(nombre)
    print(("OK " if condicion else "MAL ")+nombre+(f": {detalle}" if detalle else ""))
    if not condicion:fallos.append(nombre)

ok("detecta Ctrl+G",parece_atajo("Ctrl+G"))
ok("detecta Alt+F4",parece_atajo(" Alt + F4 "))
ok("detecta combinación de tres teclas",parece_atajo("Ctrl Shift S"))
ok("no bloquea una frase que menciona atajo",not parece_atajo("Presiona Ctrl+G para guardar"))
ok("no bloquea texto normal",not parece_atajo("Hola mundo"))
_,error=g4.planificar_teclado("escribir",texto="Ctrl+G")
ok("teclado rechaza escribir atajo",bool(error) and not error.get("bloqueado") and "accion 'atajo'" in error["error"],error)
plan,error=g4.planificar_teclado("atajo",teclas=["ctrl","g"])
ok("teclado permite el atajo estructurado",not error and plan["accion"]=="atajo",plan)

estado=nueva_proteccion()
ok("volumen devuelve evidencia",resultado_verificado("volumen",{},
   {"ok":True,"volumen_actual":40,"silenciado":False}))
registrar_resultado(estado,"volumen",{"accion":"fijar","cantidad":40},
                    {"ok":True,"volumen_actual":40,"silenciado":False})
valida,_=validar_finalizacion(estado,"Ya ajusté el volumen al 40%.",True)
ok("permite confirmar efecto verificado",valida,estado)

estado=nueva_proteccion()
valida,correccion=validar_finalizacion(estado,"Ya he traído el Bloc de notas al frente.",True)
ok("corrige confirmación falsa",not valida and "no verificó" in correccion.lower(),correccion)
valida,_=validar_finalizacion(estado,"No pude comprobar el foco de la ventana.",False)
ok("permite informar un fallo sin afirmar éxito",valida)
ok("detecta dos efectos en afirmación compuesta",
   afirmaciones_sin_evidencia("Abrí Spotify y ajusté el volumen.",{"abrir_app"})==["volumen"])
ok("mencionar volumen sin afirmar cambio no activa protección",
   not afirmaciones_sin_evidencia("No realicé ningún cambio en el volumen.",set()))
ok("dar una instrucción de clic no afirma haberlo hecho",
   not afirmaciones_sin_evidencia("Haz clic en Guardar para continuar.",set()))
ok("información guardada no afirma una acción de teclado",
   not afirmaciones_sin_evidencia("No tengo información guardada sobre tus rutinas.",set()))
ok("archivo guardado sí afirma una acción de teclado",
   afirmaciones_sin_evidencia("El archivo quedó guardado correctamente.",set()) == ["teclado"])
ok("preguntar por un documento abierto no afirma abrir una app",
   not afirmaciones_sin_evidencia("¿Qué documento tienes abierto?",set()))
ok("afirmar que se abrió una app sí exige evidencia",
   afirmaciones_sin_evidencia("La aplicación se abrió correctamente.",set()) == ["abrir_app"])
ok("nombre de app seguido de abierta exige evidencia",
   afirmaciones_sin_evidencia("Calculadora abierta.",set()) == ["abrir_app"])
ok("volumen numérico exige evidencia",
   afirmaciones_sin_evidencia("Volumen al 20%.",set()) == ["volumen"])
ok("confirmación compuesta sin acciones detecta ambos efectos",
   afirmaciones_sin_evidencia("Calculadora abierta. Volumen al 20%.",set()) == ["abrir_app", "volumen"])
ok("un fallo explícito no se interpreta como confirmación",
   not afirmaciones_sin_evidencia("No pude cambiar la ventana enfocada: seguía siendo PowerShell.",set()))

estado=nueva_proteccion()
primero=registrar_resultado(estado,"teclado",{"accion":"atajo","teclas":["ctrl","g"]},
                            {"ok":True,"efecto_visible":False})
repetido=registrar_resultado(estado,"teclado",{"accion":"atajo","teclas":["ctrl","g"]},
                             {"ok":True,"efecto_visible":False})
segundo=registrar_resultado(estado,"ejecutar_powershell",{"comando":"fallo"},{"ok":False,"error":"no"})
ok("un mismo camino repetido cuenta una vez",not primero and not repetido)
ok("dos alternativas diferentes detienen",segundo,estado)

estado=nueva_proteccion()
registrar_resultado(estado,"listar_carpeta",{"ruta":"x"},{"ok":False,"error":"no"})
ok("una lectura fallida no consume alternativa",not estado["fallos"],estado)

print(f"{len(ejecutadas)-len(fallos)}/{len(ejecutadas)} OK")
sys.exit(1 if fallos else 0)
