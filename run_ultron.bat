@echo off
echo Starting ULTRON...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe main.py
) else (
    python main.py
)
echo.
echo ============================
echo ULTRON exited.
echo Press any key to continue...
pause
