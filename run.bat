@echo off
rem Run SongClash from source, creating a virtual environment on first use.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Setting up virtual environment...
    python -m venv .venv || goto :error
)
.venv\Scripts\python.exe -c "import songclash" 2>nul || (
    echo Installing SongClash and its dependencies...
    .venv\Scripts\python.exe -m pip install -e ".[desktop]" || goto :error
)
.venv\Scripts\python.exe -m songclash %* || goto :error
exit /b 0

:error
pause
exit /b 1
