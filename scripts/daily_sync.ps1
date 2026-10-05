# Daily automatic refresh (run by Windows Task Scheduler, or at login with -IfNotRunToday — see docs/DEPLOY.md / USER_MANUAL_HI.md):
#   1. Google Ads sync  2. GA4 + Search Console sync  3. Monitoring checks (alerts)
# All three are READ-ONLY toward Google; nothing in Google Ads is changed. Log: %USERPROFILE%\.ads-command-center\logs\daily_sync.log
param([switch]$IfNotRunToday)   # at-login mode: skip if a sync already succeeded today
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$py = Join-Path $backend ".venv\Scripts\python.exe"
$logDir = Join-Path $env:USERPROFILE ".ads-command-center\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "daily_sync.log"
$stamp = Join-Path $logDir "daily_sync.last_success"
if ($IfNotRunToday -and (Test-Path $stamp) -and ((Get-Content $stamp -ErrorAction SilentlyContinue) -eq (Get-Date -Format "yyyy-MM-dd"))) { exit 0 }
if ((Test-Path $log) -and ((Get-Item $log).Length -gt 5MB)) { Move-Item -Force $log "$log.old" }

function Write-Log($text) { Add-Content -Path $log -Encoding utf8 -Value $text }

function Invoke-Step($name, $module, $moduleArgs) {
    Write-Log ("[{0}] START {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $name)
    & $py -m $module @moduleArgs 2>&1 | ForEach-Object { Write-Log ("    " + $_) }
    $code = $LASTEXITCODE
    Write-Log ("[{0}] END   {1} (exit {2})" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $name, $code)
    return $code
}

if (-not (Test-Path $py)) { Write-Log "ERROR: $py not found"; exit 2 }
Set-Location $backend
$failed = 0
if ((Invoke-Step "Google Ads sync" "app.modules.p05_ads_sync.cli" @("sync")) -ne 0) { $failed++ }
if ((Invoke-Step "GA4 + Search Console sync" "app.modules.p06_analytics.cli" @("sync")) -ne 0) { $failed++ }
if ((Invoke-Step "Monitoring checks" "app.modules.p18_monitoring.run" @()) -ne 0) { $failed++ }
if ($failed -eq 0) { Set-Content -Path $stamp -Value (Get-Date -Format "yyyy-MM-dd") }
Write-Log ("[{0}] DONE  {1} step(s) failed" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $failed)
exit $failed
