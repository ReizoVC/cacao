$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $root '.comparacion-runtime'
$outDir = Join-Path $runtime 'full-wsl'
$samplesPath = Join-Path $outDir 'windows_ram_samples.json'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$samples = [System.Collections.Generic.List[object]]::new()
$started = Get-Date
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class CacaoMemory {
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
  public class MEMORYSTATUSEX {
    public uint dwLength = (uint)Marshal.SizeOf(typeof(MEMORYSTATUSEX));
    public uint dwMemoryLoad; public ulong ullTotalPhys; public ulong ullAvailPhys;
    public ulong ullTotalPageFile; public ulong ullAvailPageFile;
    public ulong ullTotalVirtual; public ulong ullAvailVirtual; public ulong ullAvailExtendedVirtual;
  }
  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern bool GlobalMemoryStatusEx([In, Out] MEMORYSTATUSEX buffer);
}
'@
$job = Start-Job -ScriptBlock {
    wsl.exe -d Ubuntu-24.04 -- bash /mnt/c/asistente/.comparacion-runtime/run_full_wsl.sh 2>&1
}
try {
    while ($job.State -in @('NotStarted', 'Running')) {
        $memory = [CacaoMemory+MEMORYSTATUSEX]::new()
        if (-not [CacaoMemory]::GlobalMemoryStatusEx($memory)) { throw 'No pude leer la RAM de Windows.' }
        $total = [double]$memory.ullTotalPhys
        $free = [double]$memory.ullAvailPhys
        $samples.Add([ordered]@{
            timestamp = (Get-Date).ToString('o')
            elapsed_s = [math]::Round(((Get-Date) - $started).TotalSeconds, 3)
            windows_total_gib = [math]::Round($total / 1GB, 3)
            windows_used_including_wsl_gib = [math]::Round(($total - $free) / 1GB, 3)
            windows_available_gib = [math]::Round($free / 1GB, 3)
        })
        Start-Sleep -Milliseconds 250
    }
    Wait-Job $job | Out-Null
    Receive-Job $job -OutVariable output | Write-Output
    if ($job.State -ne 'Completed') { throw "La prueba WSL terminó en estado $($job.State)." }
}
finally {
    $samples | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $samplesPath -Encoding utf8
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}
