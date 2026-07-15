$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
Write-Host "Starting ULTRON Model Context Protocol (MCP) Server..." -ForegroundColor Red
python server.py
if ($LastExitCode -ne 0 -and $null -ne $LastExitCode) {
    Write-Host "[ERROR] MCP Server exited with error code $LastExitCode." -ForegroundColor DarkRed
    Read-Host "Press Enter to exit"
}
