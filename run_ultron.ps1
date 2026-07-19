$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
Write-Host "[ULTRON] Starting launcher..." -ForegroundColor Red

if (Test-Path ".venv\Scripts\python.exe") {
    & .venv\Scripts\python.exe main.py
} else {
    python main.py
}
if ($LastExitCode -ne 0 -and $null -ne $LastExitCode) {
    Write-Host ""
    Write-Host "[ULTRON] [ERROR] Application exited with error code $LastExitCode." -ForegroundColor DarkRed
    Read-Host "Press Enter to exit"
}
