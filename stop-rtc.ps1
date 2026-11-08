$ErrorActionPreference = 'Stop'
$rtcStop = Join-Path $PSScriptRoot 'data/runtime/shutdown.request'
New-Item -ItemType Directory -Force (Split-Path $rtcStop) | Out-Null
Set-Content -LiteralPath $rtcStop -Value 'graceful shutdown' -Encoding utf8
Write-Host 'Graceful shutdown requested. Allow up to 35 seconds for active requests.'
