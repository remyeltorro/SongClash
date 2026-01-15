@echo off
cd /d "%~dp0"

echo Checking for Virtual Environment...
if not exist ".venv" (
    echo Creating Virtual Environment...
    python -m venv .venv
)

echo Activating Virtual Environment...
call .venv\Scripts\activate

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing Requirements...
pip install -r requirements.txt

echo Cleaning up previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "UltimateSongRanker.spec" del UltimateSongRanker.spec

echo Building Executable...
:: --onefile: Create a single EXE
:: --windowed: No console window (GUI only)
:: --hidden-import: Ensure fetch_data is included since it's imported conditionally
:: --name: Output filename
:: Note: Anaconda path might not be needed if installing PyQt6 via pip in venv
:: set PATH=%PATH%;C:\ProgramData\anaconda3\Library\bin 
pyinstaller --noconfirm --onefile --windowed --name "SongClash" --hidden-import=fetch_data --exclude-module PyQt5 --icon="app.ico" __main__.py

echo Build complete! Executable is in the 'dist' folder.
pause
