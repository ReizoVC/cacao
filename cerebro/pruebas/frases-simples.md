---
estado: verificado
verificado_commit: f83dd1a
verificado_fecha: 2026-10-13
fuentes: [pruebas.json, comparacion_modelos/pruebas_nuevas_30.json, agente_minimo.py]
---
# Frases simples de las 65 + 30 (para el camino rápido)

Clasificación hecha a mano leyendo `pruebas.json` y `pruebas_nuevas_30.json`. «Sí» significa que una regla de frase
entera da la herramienta y los argumentos sin interpretar. Implementado con las ampliaciones (fdf84d1): entran las
17, comprobadas en `probar_camino_rapido.py` ([[camino-rapido]]).

## Frases de una herramienta

| # | Frase | Herramienta → argumentos | ¿Sin modelo? |
|---|---|---|---|
| 1 | baja el volumen | volumen bajar 10 | sí |
| 2 | sube el volumen un poco | volumen subir 10 | sí |
| 3 | pon el volumen al 30 | volumen fijar 30 | sí |
| 4 | silencia el sonido | volumen silenciar | sí |
| 5 | quita el silencio | volumen activar | sí |
| 6 | ¿a cuánto está el volumen? | volumen consultar | sí |
| 7 | pon el volumen al máximo | volumen fijar 100 | sí |
| 8–12 | abre spotify / la calculadora / el bloc de notas / Google Chrome / discord | abrir_app nombre | sí (si `elegir_app` da una sola app; si no, al modelo) |
| 103 | vuelve a activar el audio del equipo | volumen activar | sí |
| 104 | inicia la aplicación de calculadora | abrir_app Calculadora | sí |
| 101 | déjame el sonido a cuarenta y cinco por ciento | volumen fijar 45 | sí (números en palabras) |
| 65 | deja de registrar lo que hago | registro_habitos pausar | sí (frase literal, reversible) |
| 130 | reanuda el registro de mis hábitos | registro_habitos reanudar | sí |
| 13–15, 102 | está muy fuerte / no escucho nada / ponlo más bajito / que se escuche menos fuerte | volumen | no: hay que interpretar |
| 105 | quiero usar Discord, ábrelo | abrir_app | no: forma libre (fase 1) |
| 21–28, 107, 108 | ¿qué apps de… tengo? | listar_apps | no: la respuesta interpreta la lista |
| 35–40, 111, 112 | conversación | finalizar | no: la respuesta es del modelo |
| 41, 42, 113 | ¿qué ventanas…? / ¿qué programa uso? | listar_ventanas | no: hay que resumir títulos |
| 45–47, 115, 116 | ¿qué hay en mis descargas…? | listar_carpeta | no: hay que resumir |
| 49, 118 | busca en internet… | buscar_web | no: texto externo y resumen |
| 60, 127 | presiona enter / envía escape | teclado | no: acción en una ventana sin comprobar |
| 61, 128 | ¿qué suelo hacer…? | consultar_memoria | no: resumen |
| 62–64, 129 | sugerencias | sugerencias | no: «eso» depende del contexto; listar pide resumen |

## Resto (siempre al modelo)

- **Varios pasos:** #29–34, #109, #110.
- **Nombres genéricos:** #16–20, #106.
- **Ventanas con acción:** #43, #44 y #114 (enfocar exige elegir la ventana).
- **Archivos:** #48, #50, #53–55 y #117, y renombrar o mover: #121, #122 (lectura, permisos y destino).
- **Cerrar:** #51, #52, #119, #120.
- **Mouse y teclado:** #56–59, #123–126.

**Total:** 17 (#1–12, #65, #101, #103, #104 y #130); las ampliaciones las aprobó el usuario.
