param(
    [ValidateSet("gemma_q4", "gemma_q5", "qwen_q5", "qwen_wrench_q4", "ui_mate_q5")]
    [string]$Modelo = "gemma_q4",
    [switch]$Vision,
    [switch]$PensamientoNativo,
    [int]$Puerto = 18081
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $raiz ".comparacion-runtime\llama.cpp-b11429"
$exe = Join-Path $runtime "bin\llama-server.exe"
$pythonPruebas = Join-Path $raiz ".venv-pruebas\Scripts\python.exe"
$modelos = @{
    gemma_q4 = Join-Path $raiz "modelos\comparacion\gemma-4-12b-it-UD-Q4_K_XL.gguf"
    gemma_q5 = Join-Path $raiz "modelos\gemma-4-12b-it-Q5_K_M.gguf"
    qwen_q5 = Join-Path $raiz "modelos\comparacion\Qwen3.5-9B-UD-Q5_K_XL.gguf"
    qwen_wrench_q4 = Join-Path $raiz "modelos\comparacion\Wrench-9B-Q4_K_M.gguf"
    ui_mate_q5 = Join-Path $raiz "modelos\comparacion\UI-Mate-9B.Q5_K_M.gguf"
}
$rutaModelo = $modelos[$Modelo]
if (-not (Test-Path -LiteralPath $exe)) { throw "Falta el motor de pruebas: ejecuta actualizar_motor_llama_cpp.ps1." }
if (-not (Test-Path -LiteralPath $rutaModelo)) { throw "Falta el modelo $Modelo." }

# Respeta las mismas guardias de las rondas anteriores: no compite con Cacao ni con un juego.
$cacao = @()
try {
    $cacao = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.Name -in @("python.exe", "pythonw.exe") -and $_.CommandLine -match '\bvoz\.py\b'
    }
} catch {
    # Algunas sesiones remotas no permiten consultar CIM. Sin la línea de
    # comandos, cualquier Python activo se trata como posible Cacao.
    $cacao = Get-Process python, pythonw -ErrorAction SilentlyContinue
}
if ($cacao) { throw "Cacao sigue abierto; ciérralo antes de cargar el motor de pruebas." }
if (Test-Path -LiteralPath $pythonPruebas) {
    & $pythonPruebas -B -c "from guardia_juego import exigir_gpu_libre; exigir_gpu_libre('motor de pruebas', esperar=True)"
    if ($LASTEXITCODE -ne 0) { throw "La guardia de juegos no permitió iniciar la prueba." }
}
$gpuLibre = [int]((nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits).Trim())
$minimoLibre = if ($Modelo -in @("qwen_wrench_q4", "ui_mate_q5")) { 8500 } else { 12000 }
if ($gpuLibre -lt $minimoLibre) { throw "La GPU tiene solo $gpuLibre MiB libres; no se carga el modelo." }

$pidFile = Join-Path $runtime "server.pid"
if (Test-Path -LiteralPath $pidFile) {
    $anterior = [int](Get-Content -LiteralPath $pidFile)
    if (Get-Process -Id $anterior -ErrorAction SilentlyContinue) {
        throw "Ya hay un motor de pruebas activo (PID $anterior)."
    }
}

New-Item -ItemType Directory -Force -Path (Join-Path $runtime "slots") | Out-Null

$argumentos = @(
    "--model", $rutaModelo,
    "--ctx-size", "16384",
    "--gpu-layers", "all",
    "--flash-attn", "on",
    "--cache-type-k", "q8_0",
    "--cache-type-v", "q8_0",
    "--load-mode", "none",
    "--fit", "off",
    "--parallel", "1",
    "--slot-save-path", (Join-Path $runtime "slots"),
    "--host", "127.0.0.1",
    "--port", "$Puerto",
    "--alias", "cacao-test-$($Modelo.Replace('_','-'))",
    "--jinja",
    "--metrics",
    "--no-ui"
)
if ($PensamientoNativo) {
    $argumentos += @("--reasoning", "on", "--reasoning-format", "none")
} else {
    $argumentos += @("--reasoning", "off", "--reasoning-format", "deepseek")
}
if ($Vision) {
    if ($Modelo -like "gemma_*") {
        $mmproj = Join-Path $raiz "modelos\mmproj\mmproj-F16.gguf"
    } elseif ($Modelo -eq "ui_mate_q5") {
        $mmproj = Join-Path $raiz "modelos\comparacion\UI-Mate-9B.mmproj-f16.gguf"
    } else {
        $mmproj = Join-Path $raiz "modelos\comparacion\mmproj-F16.gguf"
    }
    if (-not (Test-Path -LiteralPath $mmproj)) { throw "Falta el proyector multimodal." }
    $argumentos += @("--mmproj", $mmproj, "--image-max-tokens", "1120")
}

$salida = Join-Path $runtime "server.stdout.log"
$errores = Join-Path $runtime "server.stderr.log"
$proceso = Start-Process -FilePath $exe -ArgumentList $argumentos -WorkingDirectory (Split-Path $exe) `
    -RedirectStandardOutput $salida -RedirectStandardError $errores -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $pidFile -Value $proceso.Id
$listo = $false
for ($i = 0; $i -lt 120; $i++) {
    if ($proceso.HasExited) { break }
    try {
        $respuesta = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Puerto/health" -TimeoutSec 2
        if ($respuesta.StatusCode -eq 200) { $listo = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
}
if (-not $listo) {
    if (-not $proceso.HasExited) { Stop-Process -Id $proceso.Id }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Get-Content -LiteralPath $errores -Tail 120
    throw "El motor no quedó listo."
}
Write-Output "Motor listo: PID $($proceso.Id), http://127.0.0.1:$Puerto"
