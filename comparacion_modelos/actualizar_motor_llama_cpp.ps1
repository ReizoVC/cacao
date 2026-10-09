param(
    [string]$Version = "b11429"
)

$ErrorActionPreference = "Stop"
if ($Version -ne "b11429") {
    throw "Esta receta solo tiene huellas comprobadas para b11429."
}

$raiz = Split-Path -Parent $PSScriptRoot
$destino = Join-Path $raiz ".comparacion-runtime\llama.cpp-b11429"
$descargas = Join-Path $destino "downloads"
$bin = Join-Path $destino "bin"
$archivos = @(
    @{
        Nombre = "llama-b11429-bin-win-cuda-13.4-x64.zip"
        Sha256 = "76ddc6eff2389570789ed608881efc6977751a722015d8e8c94f302224ff1a3a"
    },
    @{
        Nombre = "cudart-llama-bin-win-cuda-13.4-x64.zip"
        Sha256 = "738f8c251ac22b70c3ae6f83a10cf222725df0395246a2cf58f32bdb85fbe668"
    }
)

$libre = (Get-PSDrive -Name C).Free
if ($libre -lt 2GB) {
    throw "Se requieren al menos 2 GiB libres para descargar y extraer el motor."
}

New-Item -ItemType Directory -Force -Path $descargas, $bin | Out-Null
foreach ($archivo in $archivos) {
    $ruta = Join-Path $descargas $archivo.Nombre
    if (-not (Test-Path -LiteralPath $ruta)) {
        $url = "https://github.com/ggml-org/llama.cpp/releases/download/$Version/$($archivo.Nombre)"
        Invoke-RestMethod -Uri $url -OutFile $ruta
    }
    $real = (Get-FileHash -LiteralPath $ruta -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($real -ne $archivo.Sha256) {
        throw "Huella incorrecta para $($archivo.Nombre): $real"
    }
    Expand-Archive -LiteralPath $ruta -DestinationPath $bin -Force
}

& (Join-Path $bin "llama-server.exe") --version
