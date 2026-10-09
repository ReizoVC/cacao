$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz ".venv-pruebas\Scripts\python.exe"
$pidFile = Join-Path $raiz ".comparacion-runtime\llama.cpp-b11429\server.pid"

# El host de ejecución conserva procesos hijos solo mientras vive este script;
# por eso arranque, prueba corta, ronda completa y cierre forman una operación.
if (Test-Path -LiteralPath $pidFile) {
    $anterior = [int](Get-Content -LiteralPath $pidFile)
    if (-not (Get-Process -Id $anterior -ErrorAction SilentlyContinue)) {
        Remove-Item -LiteralPath $pidFile -Force
    }
}

try {
    & (Join-Path $PSScriptRoot "iniciar_motor_llama_cpp.ps1") -Modelo qwen_wrench_q4
    & $python -B -u (Join-Path $PSScriptRoot "ejecutar.py") qwen_wrench_q4 --smoke `
        --server-url http://127.0.0.1:18081 --engine-tag wrench_b11429
    if ($LASTEXITCODE -ne 0) { throw "La prueba corta de Wrench falló." }
    & $python -B -u (Join-Path $PSScriptRoot "ejecutar.py") qwen_wrench_q4 --round3 `
        --server-url http://127.0.0.1:18081 --engine-tag wrench_b11429
    if ($LASTEXITCODE -ne 0) { throw "La ronda completa de Wrench falló." }
} finally {
    & (Join-Path $PSScriptRoot "detener_motor_llama_cpp.ps1")
}
