$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz ".venv-pruebas\Scripts\python.exe"
$pidFile = Join-Path $raiz ".comparacion-runtime\llama.cpp-b11429\server.pid"

if (Test-Path -LiteralPath $pidFile) {
    $anterior = [int](Get-Content -LiteralPath $pidFile)
    if (-not (Get-Process -Id $anterior -ErrorAction SilentlyContinue)) {
        Remove-Item -LiteralPath $pidFile -Force
    }
}

& (Join-Path $PSScriptRoot "probar_ui_mate_vision_nativa.ps1")
if ($LASTEXITCODE -ne 0) { throw "La prueba visual nativa de UI-Mate falló." }

try {
    # El contrato JSON de Cacao requiere pensamiento desactivado. Se conserva el
    # proyector cargado para medir el margen real del candidato multimodal.
    & (Join-Path $PSScriptRoot "iniciar_motor_llama_cpp.ps1") -Modelo ui_mate_q5 -Vision
    & $python -B -u (Join-Path $PSScriptRoot "ejecutar_ui_mate.py") ui_mate_q5 --smoke `
        --server-url http://127.0.0.1:18081 --engine-tag ui_mate_b11429
    if ($LASTEXITCODE -ne 0) { throw "La prueba corta de integración Cacao falló." }
    & $python -B -u (Join-Path $PSScriptRoot "ejecutar_ui_mate.py") ui_mate_q5 --round3 `
        --server-url http://127.0.0.1:18081 --engine-tag ui_mate_b11429
    if ($LASTEXITCODE -ne 0) { throw "La ronda completa de UI-Mate falló." }
} finally {
    & (Join-Path $PSScriptRoot "detener_motor_llama_cpp.ps1")
}
