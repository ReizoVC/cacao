"""Pruebas puras: no abre apps ni envía mouse o teclado."""
import sys

import herramientas_grupo4 as g4
from protecciones_ejecucion import (MAX_ALTERNATIVAS, afirmaciones_sin_evidencia, cierre_no_pedido, nueva_proteccion, parece_atajo,
                                    pide_cerrar, pide_forzar,
                                    quitar_forzar_no_pedido, registrar_resultado, resultado_verificado,
                                    validar_finalizacion)

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

# falsos positivos de resultados_swa_y_recursos.md (#108, conversación 6, #123 y #124)
ok("«Grabadora de sonido está instalada» no afirma un cambio de volumen",
   not afirmaciones_sin_evidencia("Sí, la Grabadora de sonido está instalada.",set()))
estado=nueva_proteccion()
valida,_=validar_finalizacion(estado,"La Grabadora de sonido está instalada en tu equipo.",True)
ok("y la respuesta se acepta sin corrección",valida and estado["correcciones"]==0,estado)
ok("«tarjeta de sonido» tampoco",not afirmaciones_sin_evidencia("Tu tarjeta de sonido está activa.",set()))
ok("«escrita» como adjetivo no afirma escribir",
   not afirmaciones_sin_evidencia("La forma escrita correcta es «haber».",set()))
ok("«escrita» en una descripción tampoco",
   not afirmaciones_sin_evidencia("En la versión escrita del informe aparece tu nombre.",set()))
ok("«no he podido verificar» cuenta como negación",
   not afirmaciones_sin_evidencia("No he podido verificar que se haya cerrado.",set()))
ok("«no puedo verificar … se haya movido» cuenta como negación",
   not afirmaciones_sin_evidencia("No puedo verificar que el archivo se haya movido.",set()))
ok("«no he podido» sin verificar también",not afirmaciones_sin_evidencia("No he podido cerrar la ventana.",set()))
ok("afirmar y decir que no se puede verificar no es un hecho",
   not afirmaciones_sin_evidencia("Cerré la ventana, pero no puedo verificarlo.",set()))
ok("una pregunta no afirma",not afirmaciones_sin_evidencia("¿La calculadora está abierta?",set()))
ok("participio solo como adjetivo no afirma",
   not afirmaciones_sin_evidencia("El archivo guardado en Descargas es el más reciente.",set()))
# las afirmaciones reales se siguen detectando
ok("la negación no cruza «pero»",
   afirmaciones_sin_evidencia("No pude abrir Spotify, pero cerré la calculadora.",set())==["cerrar"])
ok("«he escrito» exige evidencia",
   afirmaciones_sin_evidencia("He escrito el texto en el Bloc de notas.",set())==["teclado"])
ok("«Texto escrito.» exige evidencia",afirmaciones_sin_evidencia("Texto escrito.",set())==["teclado"])
ok("«está cerrada» exige evidencia",afirmaciones_sin_evidencia("La ventana ya está cerrada.",set())==["cerrar"])
ok("«el sonido está silenciado» exige evidencia",
   afirmaciones_sin_evidencia("El sonido está silenciado.",set())==["volumen"])
ok("«subí el volumen del sonido» exige evidencia",
   afirmaciones_sin_evidencia("Subí el volumen del sonido.",set())==["volumen"])
ok("«grabadora de sonido» no oculta un volumen afirmado después",
   afirmaciones_sin_evidencia("Abrí la Grabadora de sonido y subí el volumen.",{"abrir_app"})==["volumen"])
ok("una negación anterior no oculta una afirmación tras «y»",
   afirmaciones_sin_evidencia("El volumen no cambió y ahora está al 40%.",set())==["volumen"])

estado=nueva_proteccion()
primero=registrar_resultado(estado,"teclado",{"accion":"atajo","teclas":["ctrl","g"]},
                            {"ok":True,"efecto_visible":False})
repetido=registrar_resultado(estado,"teclado",{"accion":"atajo","teclas":["ctrl","g"]},
                             {"ok":True,"efecto_visible":False})
segundo=registrar_resultado(estado,"ejecutar_powershell",{"comando":"fallo"},{"ok":False,"error":"no"})
ok("un mismo camino repetido cuenta una vez",not primero and not repetido)
ok("dos alternativas fallidas ya no detienen (el tope es 5)",not segundo and MAX_ALTERNATIVAS==5,estado)
siguientes=[registrar_resultado(estado,"mouse",{"accion":"clic","control":f"Botón {i}"},
                                {"ok":True,"efecto_visible":False}) for i in range(3)]
ok("la quinta alternativa diferente detiene",siguientes==[False,False,True],estado)

estado=nueva_proteccion()
registrar_resultado(estado,"listar_carpeta",{"ruta":"x"},{"ok":False,"error":"no"})
ok("una lectura fallida no consume alternativa",not estado["fallos"],estado)

# cerrar_app con forzar=true solo si el pedido lo pide (caso #56 s22 de Qwen: forzó el cierre de «la X»)
for pedido in ["el bloc de notas no responde, ciérralo a la fuerza", "fuerza el cierre de Chrome",
               "ciérralo forzado", "Spotify se colgó, ciérralo", "el juego está congelado, ciérralo",
               "forzar cierre del bloc", "FUÉRZALO", "Word no contesta", "se trabó Discord, ciérralo",
               "mata el proceso de chrome", "la app está bloqueada, ciérrala"]:
    ok(f"pide forzar: {pedido}",pide_forzar(pedido))
for pedido in ["haz clic en la X de la ventana activa para cerrarla", "cierra el bloc de notas",
               "cierra todo", "", None, "con esfuerzo, cierra la ventana", "cierra Spotify rápido"]:
    ok(f"no pide forzar: {pedido!r}",not pide_forzar(pedido))
args,nota=quitar_forzar_no_pedido("cerrar_app",{"id_ventana":3,"forzar":True},
                                  "haz clic en la X de la ventana activa para cerrarla")
ok("forzar no pedido: cierre normal y nota",args=={"id_ventana":3,"forzar":False} and bool(nota),(args,nota))
args,nota=quitar_forzar_no_pedido("cerrar_app",{"proceso":"notepad.exe","forzar":True},
                                  "el bloc de notas no responde, ciérralo a la fuerza")
ok("forzar pedido: se mantiene",args["forzar"] is True and nota is None,(args,nota))
args,nota=quitar_forzar_no_pedido("cerrar_app",{"proceso":"notepad.exe"},"cierra el bloc")
ok("sin forzar: no cambia",args=={"proceso":"notepad.exe"} and nota is None)
args,nota=quitar_forzar_no_pedido("mover_archivo",{"forzar":True},"mueve el archivo")
ok("solo afecta a cerrar_app",args=={"forzar":True} and nota is None)

# cerrar_app solo si el pedido expresa intención de cerrar (Qwen: #58 s22, #43 s22 y #19 s33 cerraron apps no pedidas)
for pedido in ["cierra el bloc de notas", "ciérrame Spotify", "cerrar Chrome", "sal de Discord", "salir de Word",
               "quítalo", "termina el bloc de notas", "mata el proceso de chrome", "apaga la app de música",
               "el bloc de notas no responde, ciérralo a la fuerza", "haz clic en la X de la ventana activa para cerrarla",
               "cierra únicamente la ventana del bloc de notas que está abierta",
               "termina a la fuerza el bloc de notas porque quedó congelado"]:
    ok(f"pide cerrar: {pedido}", pide_cerrar(pedido))
for pedido in ["escribe 'hola mundo' en el bloc de notas", "trae al frente el bloc de notas",
               "abre algo para escribir", "abre el bloc de notas", "cambia a la ventana de la terminal", "", None]:
    ok(f"no pide cerrar: {pedido!r}", not pide_cerrar(pedido))
r = cierre_no_pedido("cerrar_app", "escribe 'hola mundo' en el bloc de notas")
ok("#58: cerrar_app no pedido -> resultado para el modelo, sin ejecutar",
   r and r["ok"] is False and r["cierre_no_pedido"] and "no pidió cerrar" in r["error"] and "bloqueado" not in r, r)
ok("#43: trae al frente -> cerrar_app no pedido", cierre_no_pedido("cerrar_app", "trae al frente el bloc de notas"))
ok("cierra el bloc de notas -> pasa", cierre_no_pedido("cerrar_app", "cierra el bloc de notas") is None)
ok("solo afecta a cerrar_app", cierre_no_pedido("mover_archivo", "abre el bloc de notas") is None)

# toda frase de las 65 (y de las 30 nuevas, si están) cuya acción esperada incluye cerrar_app pasa el freno
import json
from pathlib import Path
for archivo in (Path("pruebas.json"), Path("comparacion_modelos/pruebas_nuevas_30.json")):
    if not archivo.exists():
        continue
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    for prueba in (datos["pruebas"] if isinstance(datos, dict) else datos):
        esperado = prueba["esperado"] if isinstance(prueba["esperado"], list) else [prueba["esperado"]]
        if "cerrar_app" in esperado + prueba.get("requiere", []):
            ok(f"{archivo.name} #{prueba['id']} pasa el freno de cerrar_app", pide_cerrar(prueba["frase"]), prueba["frase"])

print(f"{len(ejecutadas)-len(fallos)}/{len(ejecutadas)} OK")
sys.exit(1 if fallos else 0)
