@echo off
rem Build dist\SongClash.exe. The build itself is defined in packaging\songclash.spec.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv || goto :error
)
set PY=.venv\Scripts\python.exe

echo Installing build requirements...
%PY% -m pip install --upgrade pip || goto :error
%PY% -m pip install -e ".[build]" || goto :error

echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

echo Generating icon...
%PY% scripts\make_icon.py || goto :error

echo Building executable...
%PY% -m PyInstaller --noconfirm packaging\songclash.spec || goto :error

echo.
echo Build complete! Executable is in the 'dist' folder.
pause
exit /b 0

:error
echo.
echo Build FAILED.
pause
exit /b 1
