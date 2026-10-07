$ErrorActionPreference = 'Stop'
$destino = 'C:\asistente\modelos\comparacion'
New-Item -ItemType Directory -Force -Path $destino | Out-Null
$archivos = @(
    @('unsloth/gemma-4-12b-it-GGUF','fc034cfff751157913579611efad8462ac1be606','gemma-4-12b-it-UD-Q4_K_XL.gguf',7366423360,'90fd944d227e9d9b68e7e2c7d5b57b79d4c66ed521b0919fbbd932cf834f6f8e'),
    @('unsloth/Qwen3.5-9B-GGUF','3885219b6810b007914f3a7950a8d1b469d598a5','Qwen3.5-9B-UD-Q4_K_XL.gguf',5966095584,'6f5d30666c2d8ae16a306e616d95341dcf3cc46810df84d7e6f5a7d1e4c1b293'),
    @('unsloth/Qwen3.5-9B-GGUF','3885219b6810b007914f3a7950a8d1b469d598a5','Qwen3.5-9B-UD-Q5_K_XL.gguf',6743680224,'96cf42ddb97f9572410a72b9ed6f2299b1e887ee08da4c2a6c01e897cfa9f673'),
    @('unsloth/Qwen3.5-9B-GGUF','3885219b6810b007914f3a7950a8d1b469d598a5','mmproj-F16.gguf',918166080,'f70dc3509053962b0d0d3ee8a7eacebf5d60aa560cad78254ae8698516ae029f')
)
foreach ($a in $archivos) {
    $salida = Join-Path $destino $a[2]
    $existe = if (Test-Path -LiteralPath $salida) { (Get-Item -LiteralPath $salida).Length } else { 0 }
    if ((Get-PSDrive C).Free -lt ([long]$a[3] - $existe + 4GB)) { throw 'No hay margen de 4 GiB; descarga detenida.' }
    if ($existe -ne $a[3]) {
        Write-Output ('Descargando ' + $a[2])
        & curl.exe --fail --location --retry 4 --continue-at - --output $salida ('https://huggingface.co/' + $a[0] + '/resolve/' + $a[1] + '/' + $a[2]) --silent --show-error
        if ($LASTEXITCODE -ne 0) { throw ('Fallo curl: ' + $LASTEXITCODE) }
    }
    if ((Get-Item -LiteralPath $salida).Length -ne $a[3]) { throw 'Tamano incorrecto' }
    if ((Get-FileHash -LiteralPath $salida -Algorithm SHA256).Hash.ToLowerInvariant() -ne $a[4]) { throw 'SHA256 incorrecto' }
    Write-Output ('Verificado ' + $a[2])
}
