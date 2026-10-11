# Registro del cerebro

Una entrada por tarea, la más reciente al final: fecha, qué cambió y commit.

Entradas anteriores: [[log-2026-10-10]], [[log-2026-10-11-isla]] y [[log-2026-10-11-b]].

## 2026-10-11: 65 × 3 con producción restaurada (sin swa_full)

- `probar_swa_cache.py C --casos todos` (dbb0e42): 1.ª herramienta 195/195, completas 194/195 (base 193/195).
  Semilla 11 sin fallos en #26–42. Detalle en `evaluacion-65-frases`.

## 2026-10-11: brazo A sobre #1–42 (swa_full=false, sin vaciar): 42/42

- Los fallos de la primera corrida no se reproducen ni con la secuencia larga; ningún umbral de tokens coincide
  (tabla en `swa-full-false`). Causa abierta; sin arreglos ni entrada en `lecciones.md`.

## 2026-10-11: música en la isla implementada (protocolo v3), sin compilar

- Isla, rama `claude/musica`: 1daebe0 (Rust), 712a893 (protocolo v3 y arnés) y a90ddc9 (invariante 11).
- Cacao, rama `claude/musica-v3`: a9797ed (`ui_isla.PROTOCOLO = 3` y `musica` informativa).
- No van a `main` hasta compilar: v2 y v3 no se conectan (4003). Página `musica-isla` al día.
- Al revisar la línea mínima de Codex (e30e4fe, e441b90) se pidieron correcciones: con la línea apagada cambiaba
  el comportamiento. No se fusionó.
