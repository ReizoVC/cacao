# Arranque de Cacao: el agente en modo voz (voz.py), que abre la isla y escucha la palabra "Cacao".
#
# Lo lanza el acceso directo Cacao.lnk (crear_acceso_directo.ps1). Sin permisos de administrador.
#   -AlInicio  espera 60 s antes de arrancar (driver de la GPU, audio y WebView2 listos tras iniciar sesion).
#   -Simular   solo comprueba y muestra lo que haria, sin cargar nada (no usa la GPU ni el microfono).
# Si ya hay un Cacao en marcha, no abre otro. Con un juego activo, el agente espera a que se cierre antes de cargar
# Gemma y Whisper (guardia_juego.py), asi que no le quita la GPU a nadie.
param([switch]$AlInicio, [switch]$Simular, [int]$EsperaS = 60)

$ErrorActionPreference = "Stop"
$base = $PSScriptRoot
$python = Join-Path $base ".venv\Scripts\python.exe"
$script = Join-Path $base "voz.py"
$Host.UI.RawUI.WindowTitle = "Cacao"

function Get-CacaoEnMarcha {
    # procesos de Python de este .venv que ejecutan voz.py o agente_minimo.py
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" |
        Where-Object { ($_.ExecutablePath -like "$base*" -or $_.CommandLine -like "*$base*") -and
                       $_.CommandLine -match '(voz|agente_minimo)\.py' }
}

$faltan = @()
foreach ($ruta in @($python, $script, (Join-Path $base "config.json"), (Join-Path $base "herramientas.json"))) {
    if (-not (Test-Path $ruta)) { $faltan += $ruta }
}
$config = Get-Content (Join-Path $base "config.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$isla = $config.ui.exe
$avisos = @()
if ($config.ui.lanzar -and -not (Test-Path $isla)) { $avisos += "No encuentro la isla ($isla): Cacao funcionara sin ella." }
if (-not $config.voz.palabra_activacion.activa) { $avisos += "La palabra de activacion esta desactivada en config.json." }

$enMarcha = @(Get-CacaoEnMarcha)
if ($Simular) {
    Write-Host "[simulacion] Carpeta: $base"
    Write-Host "[simulacion] Faltan: $(if ($faltan) { $faltan -join ', ' } else { 'nada' })"
    Write-Host "[simulacion] Avisos: $(if ($avisos) { $avisos -join ' ' } else { 'ninguno' })"
    Write-Host "[simulacion] Cacao ya en marcha: $(if ($enMarcha) { 'si, PID ' + ($enMarcha.ProcessId -join ', ') } else { 'no' })"
    Write-Host "[simulacion] Esperaria: $(if ($AlInicio) { "$EsperaS s" } else { '0 s' })"
    Write-Host "[simulacion] Ejecutaria: `$env:ESPERAR_JUEGO=1; & `"$python`" `"$script`""
    exit 0
}
if ($faltan) {
    Write-Host "No puedo arrancar Cacao; faltan: $($faltan -join ', ')"
    Read-Host "Pulsa Enter para cerrar"
    exit 1
}
if ($enMarcha) {
    Write-Host "Cacao ya esta en marcha (PID $($enMarcha.ProcessId -join ', ')); no abro otro."
    Start-Sleep -Seconds 5
    exit 0
}
foreach ($a in $avisos) { Write-Host "Aviso: $a" }
if ($AlInicio) {
    Write-Host "Cacao arranca en $EsperaS s (Ctrl+C para no arrancarlo ahora)."
    Start-Sleep -Seconds $EsperaS
}

Set-Location $base
$env:ESPERAR_JUEGO = "1"        # con un juego activo, esperar en vez de salir
$env:PYTHONIOENCODING = "utf-8"
& $python $script
$codigo = $LASTEXITCODE
if ($codigo -ne 0) {
    Write-Host "`nCacao termino con el codigo $codigo. Revisa los mensajes de arriba y errores_llama.log."
    Read-Host "Pulsa Enter para cerrar"
}
exit $codigo
