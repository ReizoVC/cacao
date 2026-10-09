$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $raiz ".comparacion-runtime\llama.cpp-b11429"
$pidFile = Join-Path $runtime "server.pid"
if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output "No hay PID registrado."
    exit 0
}
$serverPid = [int](Get-Content -LiteralPath $pidFile)
$proceso = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if ($null -ne $proceso) {
    $ruta = $proceso.Path
    $esperada = Join-Path $runtime "bin\llama-server.exe"
    if ([IO.Path]::GetFullPath($ruta) -ne [IO.Path]::GetFullPath($esperada)) {
        throw "El PID $serverPid ya no pertenece al motor aislado; no se detuvo."
    }
    Stop-Process -Id $serverPid
    [void]$proceso.WaitForExit(15000)
}
Remove-Item -LiteralPath $pidFile -Force
Write-Output "Motor de pruebas detenido."
