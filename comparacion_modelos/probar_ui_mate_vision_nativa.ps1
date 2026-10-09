$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz ".venv-pruebas\Scripts\python.exe"

try {
    & (Join-Path $PSScriptRoot "iniciar_motor_llama_cpp.ps1") `
        -Modelo ui_mate_q5 -Vision -PensamientoNativo
    & $python -B -u (Join-Path $PSScriptRoot "probar_ui_mate_nativo.py") `
        --salida (Join-Path $PSScriptRoot "ui_mate_q5_vision_nativa.json")
    if ($LASTEXITCODE -ne 0) { throw "La prueba visual nativa de UI-Mate falló." }
} finally {
    & (Join-Path $PSScriptRoot "detener_motor_llama_cpp.ps1")
}
