param([switch]$Production, [switch]$Check)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$rtcPython = if ($env:RTC_PYTHON) { $env:RTC_PYTHON } elseif (Test-Path -LiteralPath '.venv/Scripts/python.exe') { Join-Path $PSScriptRoot '.venv/Scripts/python.exe' } else { (Get-Command python -ErrorAction Stop).Source }
$rtcArguments = @('scripts/serve_rtc.py')
if ($Check) { $rtcArguments += '--check' }
& $rtcPython @rtcArguments
exit $LASTEXITCODE
