# Crea el acceso directo de Cacao (iniciar_cacao.ps1, en una ventana minimizada). Sin permisos de administrador.
#   sin parametros  Cacao.lnk en esta carpeta, para arrancarlo con doble clic (no arranca con Windows).
#   -Inicio         lo pone tambien en la carpeta de Inicio del usuario (shell:startup): Cacao arranca al iniciar
#                   sesion. Hazlo solo estando frente al PC.
#   -Quitar         lo quita de la carpeta de Inicio (Cacao.lnk de esta carpeta se queda).
param([switch]$Inicio, [switch]$Quitar)

$ErrorActionPreference = "Stop"
$base = $PSScriptRoot
$nombre = "Cacao.lnk"
$carpetaInicio = [Environment]::GetFolderPath("Startup")

if ($Quitar) {
    $ruta = Join-Path $carpetaInicio $nombre
    if (Test-Path $ruta) { Remove-Item $ruta; Write-Host "Quitado de Inicio: $ruta" }
    else { Write-Host "No estaba en Inicio ($ruta)." }
    exit 0
}

function New-AccesoCacao([string]$ruta, [bool]$alInicio) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($ruta)
    $lnk.TargetPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $extra = if ($alInicio) { " -AlInicio" } else { "" }
    $lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$base\iniciar_cacao.ps1`"$extra"
    $lnk.WorkingDirectory = $base
    $lnk.WindowStyle = 7  # minimizada
    $lnk.Description = "Cacao: asistente de escritorio (voz, isla y palabra de activacion)"
    $config = Get-Content (Join-Path $base "config.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    if (Test-Path $config.ui.exe) { $lnk.IconLocation = "$($config.ui.exe),0" }
    $lnk.Save()
    Write-Host "Creado: $ruta"
}

New-AccesoCacao (Join-Path $base $nombre) $false
if ($Inicio) {
    New-AccesoCacao (Join-Path $carpetaInicio $nombre) $true
    Write-Host "Cacao arrancara al iniciar sesion. Para quitarlo: .\crear_acceso_directo.ps1 -Quitar"
}
