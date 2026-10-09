$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$destino = Join-Path $raiz "modelos\comparacion\Wrench-9B-Q4_K_M.gguf"
$tamano = [long]5629108640
$sha256 = "e21435c7150794cccddf2ab0737fb5509eba681e7c9a89b1dc9e51948c4f78b7"
$revision = "6d4f489d2a1ebb0f41f6cc8779a07df5917e5ddc"
$archivo = "Wrench-9B-Q4_K_M-GGUF%20.gguf"
$url = "https://huggingface.co/ClankLabs/Wrench-9B-Q4_K_M-GGUF/resolve/$revision/$archivo"

New-Item -ItemType Directory -Force -Path (Split-Path $destino) | Out-Null
$existente = if (Test-Path -LiteralPath $destino) { (Get-Item -LiteralPath $destino).Length } else { 0 }
$restante = [math]::Max([long]0, $tamano - $existente)
if ((Get-PSDrive C).Free -lt ($restante + 4GB)) {
    throw "No hay espacio suficiente para descargar Wrench conservando 4 GiB de margen."
}
if ($existente -ne $tamano) {
    & curl.exe --fail --location --retry 4 --continue-at - --output $destino $url --silent --show-error
    if ($LASTEXITCODE -ne 0) { throw "Fallo curl: $LASTEXITCODE" }
}
if ((Get-Item -LiteralPath $destino).Length -ne $tamano) { throw "Tamaño incorrecto." }
$real = (Get-FileHash -LiteralPath $destino -Algorithm SHA256).Hash.ToLowerInvariant()
if ($real -ne $sha256) { throw "SHA256 incorrecto: $real" }
Write-Output "Wrench verificado: $destino"
