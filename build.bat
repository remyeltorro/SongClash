@echo off
echo Activating Virtual Environment...
call .venv\Scripts\activate

echo Installing PyInstaller...
pip install pyinstaller

echo Cleaning up previous builds...
rmdir /s /q build
rmdir /s /q dist
del UltimateSongRanker.spec

echo Building Executable...
:: --onefile: Create a single EXE
:: --windowed: No console window (GUI only)
:: --hidden-import: Ensure fetch_data is included since it's imported conditionally
:: --name: Output filename
set PATH=%PATH%;C:\ProgramData\anaconda3\Library\bin
pyinstaller --noconfirm --onefile --windowed --name "UltimateSongRanker" --hidden-import=fetch_data --exclude-module PyQt5 __main__.py

echo Build complete! Executable is in the 'dist' folder.
pause
