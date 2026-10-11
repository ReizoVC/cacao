---
estado: sin verificar
verificado_commit: 77370e8
verificado_fecha: 2026-10-11
fuentes: [guia_instalacion_agente.md, SRS.md, config.json]
---
# Pendientes que necesitan al usuario frente al PC

Copiados de la guía (Fase 7, «Pendiente para cuando estés frente al PC») y del SRS §9.

**Estado: desconocido.** Desde el repositorio no se puede saber si ya se hicieron, y comprobarlo exigiría leer
registros o datos personales. Pregúntaselo al usuario y anota la respuesta aquí y en [[log]].

## Lista (en el orden de la guía)

1. **Cacao sin terminal:**
   - arrancar con `Cacao.lnk`, «Ver terminal», «Salir de Cacao», confirmar con la isla y el atajo de emergencia;
   - un juego con la isla dormida;
   - los íconos.
2. **Isla y escucha de seguimiento:**
   - tres tamaños, el cierre tras hablar y el indicador de 8 s;
   - hablar sin decir «Cacao»;
   - música sonando;
   - el Panel de control en el Explorador, donde no debe hacer clic.
3. **autocompletar_login:** activar Windows Hello en Chrome; luego `activa: true`, añadir frases al set y volver a
   pasar las 65. Hoy `config.json` la tiene en `false`.
4. **Arranque automático:** que Cacao aparezca a los ~60 s de iniciar sesión y que espere si se abre un juego.
5. **«Cacao» en el día a día:** revisar el contador de activaciones tras unos días. Lo revisa el usuario; Claude no
   lee ese archivo.
6. **Grabar la isla** con «Permitir capturas». El usuario tomó una captura el 2026-10-11 (~01:35) durante la
   prueba de la bandeja; no se comprobó qué salió en ella.
8. **De la lista del usuario (2026-10-11):** Whisper pequeño en CPU con audio real («estoy jugando», «ya
   terminé»), un «sí» solo rechazado en vivo, y el mando o joystick.
7. **Bandeja de la isla v2 con el arnés: HECHA el 2026-10-11** (01:33–07:26, con el usuario). Resultados en
   [[compilar-isla]]. Quedan dos cosas:
   - «Pausar» no se probó con el teclado;
   - un «Escuchar «Cacao»» con `fisico=false` a las 01:59:15 que el usuario no supo explicar (se rechazó, como
     debía).

   Procedimiento, por si hay que repetirla:
   - **Preparación (Claude):**
     - comprueba que Cacao y la isla están cerrados y el puerto 8765 libre;
     - lanza `mock_agente.py --escenario ninguno`;
     - **espera el aviso** para abrir `target\release\asistente-ui.exe`. El arnés debe decir «isla conectada
       (versión 2)».
   - **A. Con un clic físico:**
     - Abrir y Ajustes abren la isla;
     - Pausar la oculta y la vuelve a mostrar;
     - Ver terminal muestra el aviso del arnés;
     - con los dos modos, el arnés recibe `fisico: true` y marca la casilla;
     - Permitir capturas se marca y Recortes ve la isla (anotar la hora).
   - **B. Con el teclado** (flechas y Enter en el menú):
     - ninguna opción hace nada y la casilla de capturas no se queda marcada;
     - los modos llegan con `fisico: false` y la isla avisa «No cambio el modo».
   - **C. Clic inyectado (opcional, solo si el usuario lo pide en ese momento):** con el cursor sobre «Permitir
     capturas», un script inyecta un clic a los 3 s. No debe pasar nada.
   - **D. Ajustes:** el interruptor de capturas se enciende con un clic físico.
   - **E. Caducidad:** a los 10 minutos de encenderlo, se desmarca solo y Recortes ya no ve la isla.
   - **F. Reinicio:**
     - con capturas encendidas, «Salir de Cacao» cierra el arnés;
     - un segundo «Salir» cierra la isla;
     - al relanzar las dos, capturas aparece apagado.
   - **Pruebas:** la salida del arnés. Con permiso del usuario, también las líneas `bandeja:` y `captura:` de
     `%LOCALAPPDATA%\Asistente\asistente-ui.log`.
7. **Mando:** detección de actividad (`entrada.py`).
8. **Datos reales:**
   - Obsidian, la reflexión y las sugerencias tras una semana de hábitos;
   - la lista de apps de banco (está en los datos locales; no la leas).
9. **Modo sin confirmación** con acciones reales (SRS §9).
10. **Activaciones falsas tras la segunda etapa**, latencia y CPU de la escucha (RNF-25, no medido).

## Del trabajo con modelos

11. Puntuar las evaluaciones a ciegas: `resultados_ciegas.md` y `resultados_ciegas_q4.md` ([[backlog]] #20–21).
12. Cambios de producción: la regla JSON está en el código (7d31aa7); swa_full=false se revirtió para Gemma
    (397d0a2). Las 65 frases con producción dieron 194/195. El cierre rápido se valida y se apaga en Qwen
    (69297e4, d95855d; [[backlog]] #4).
