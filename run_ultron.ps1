$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
Write-Host "[ULTRON] Starting launcher..." -ForegroundColor Red

# Detect and activate virtual environment if present
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[ULTRON] Activating virtual environment (.venv)..." -ForegroundColor Gray
    . .venv\Scripts\Activate.ps1
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[ULTRON] Activating virtual environment (venv)..." -ForegroundColor Gray
    . venv\Scripts\Activate.ps1
}

Write-Host "[ULTRON] Booting application entry point..." -ForegroundColor Red
python main.py
if ($LastExitCode -ne 0 -and $null -ne $LastExitCode) {
    Write-Host ""
    Write-Host "[ULTRON] [ERROR] Application exited with error code $LastExitCode." -ForegroundColor DarkRed
    Read-Host "Press Enter to exit"
}
