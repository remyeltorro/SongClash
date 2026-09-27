@echo off
rem Build dist\SongClash.apk, an Android app you can install directly (see docs\ANDROID.md).
rem The first run downloads a JDK and the Android SDK (a few GB) into Briefcase's cache.
setlocal
cd /d "%~dp0"

if not exist ".venv-mobile\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv-mobile || goto :error
)
set PY=.venv-mobile\Scripts\python.exe

echo Installing build requirements...
%PY% -m pip install --upgrade pip || goto :error
%PY% -m pip install -e ".[mobile]" briefcase Pillow || goto :error

echo Generating icons...
%PY% scripts\make_icon.py --android || goto :error

echo Building the Android app...
rem -r (update requirements) and --update-resources pick up dependency and icon changes
%PY% -m briefcase build android --no-input -r --update-resources || goto :error
%PY% -m briefcase package android --no-input -p debug-apk || goto :error

if not exist dist mkdir dist
for %%f in (dist\SongClash-*.apk) do copy /y "%%f" dist\SongClash.apk >nul

echo.
echo Build complete: dist\SongClash.apk
echo Copy it to your phone and open it, or with USB debugging on run:
echo     adb install -r dist\SongClash.apk
pause
exit /b 0

:error
echo.
echo Build FAILED.
pause
exit /b 1
