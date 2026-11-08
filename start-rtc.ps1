param([switch]$Production, [switch]$InitializeDemo)
$ErrorActionPreference = "Stop"
$rtcRoot = $PSScriptRoot
Set-Location -LiteralPath $rtcRoot
$pythonPath = (Get-Command python -ErrorAction Stop).Source
$nodePath = $null
if (!$Production) { $nodePath = (Get-Command node -ErrorAction Stop).Source }
& $pythonPath -c "import fastapi, sqlalchemy, uvicorn, alembic"
if ($LASTEXITCODE -ne 0) { throw "Install requirements.txt before starting." }
if (!$Production -and !(Test-Path -LiteralPath "frontend/node_modules/vite/bin/vite.js")) { throw "Run npm ci --prefix frontend during online setup first." }
if ($Production -and !(Test-Path -LiteralPath "frontend/dist/index.html")) { throw "Run npm run build --prefix frontend first." }
foreach ($port in $(if ($Production) { @(8000) } else { @(8000,5173) })) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port is already in use. Stop that RTC instance first." }
}
$env:PYTHONPATH = Join-Path $rtcRoot "backend"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
& $pythonPath -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
if ($InitializeDemo) {
    foreach ($module in @("app.seed","app.demo","app.nlp_seed","app.taxonomy_seed")) {
        & $pythonPath -m $module
        if ($LASTEXITCODE -ne 0) { throw "Demo setup failed: $module" }
    }
}
if (!$env:RTC_ADMIN_TOKEN) {
    $rtcTokenBytes = New-Object byte[] 32
    $rtcGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
    $rtcGenerator.GetBytes($rtcTokenBytes)
    $rtcGenerator.Dispose()
    $env:RTC_ADMIN_TOKEN = [Convert]::ToBase64String($rtcTokenBytes)
    Write-Host "Temporary local administrator token (this run only): $env:RTC_ADMIN_TOKEN"
}
New-Item -ItemType Directory -Force "data/runtime" | Out-Null
$backendProcess = $null
$frontendProcess = $null
try {
    $backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @("-m","uvicorn","app.main:app","--app-dir","backend","--host","127.0.0.1","--port","8000") -WorkingDirectory $rtcRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "data/runtime/backend.log" -RedirectStandardError "data/runtime/backend-error.log"
    if (!$Production) {
        $frontendProcess = Start-Process -FilePath $nodePath -ArgumentList @("frontend/node_modules/vite/bin/vite.js","frontend","--host","127.0.0.1","--port","5173","--strictPort") -WorkingDirectory $rtcRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "data/runtime/frontend.log" -RedirectStandardError "data/runtime/frontend-error.log"
    }
    $ready = $false
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        if ($backendProcess.HasExited -or ($frontendProcess -and $frontendProcess.HasExited)) { throw "RTC process exited. Check data/runtime logs." }
        try { $null=Invoke-RestMethod "http://127.0.0.1:8000/api/v1/nlp/health"; $ready=$true; break } catch { Start-Sleep -Seconds 1 }
    }
    if (!$ready) { throw "Backend startup timed out. Check data/runtime logs." }
    Write-Host "RTC app: $(if ($Production) {'http://127.0.0.1:8000'} else {'http://127.0.0.1:5173'})"
    Write-Host "API docs: http://127.0.0.1:8000/docs"
    Write-Host "Ctrl+C stops both processes. No packages download at runtime."
    while (!$backendProcess.HasExited) { Start-Sleep -Seconds 1 }
} finally {
    if ($frontendProcess -and !$frontendProcess.HasExited) { $frontendProcess.Kill() }
    if ($backendProcess -and !$backendProcess.HasExited) { $backendProcess.Kill() }
}
