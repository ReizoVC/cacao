---
estado: sin verificar
verificado_commit: 10b63cc
verificado_fecha: 2026-10-10
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
6. **Grabar la isla** con «Permitir capturas».
7. **Mando:** detección de actividad (`entrada.py`).
8. **Datos reales:**
   - Obsidian, la reflexión y las sugerencias tras una semana de hábitos;
   - la lista de apps de banco (está en los datos locales; no la leas).
9. **Modo sin confirmación** con acciones reales (SRS §9).
10. **Activaciones falsas tras la segunda etapa**, latencia y CPU de la escucha (RNF-25, no medido).

## Del trabajo con modelos

11. Puntuar las evaluaciones a ciegas: `resultados_ciegas.md` y `resultados_ciegas_q4.md` ([[backlog]] #20–21).
12. Decidir los cambios de producción: swa_full, la regla JSON y el cierre rápido ([[backlog]] #3–5).
