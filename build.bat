@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   Engineer Desk - Build Script
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found in PATH
    pause
    exit /b 1
)

echo [1/3] Installing PyInstaller...
python -m pip install pyinstaller --quiet
if %errorlevel% neq 0 (
    echo Error: Failed to install PyInstaller
    pause
    exit /b 1
)

echo [2/3] Cleaning old builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec" 2>nul

echo [3/3] Building...
python -m PyInstaller --onefile --windowed --name "EngineerDesk" --distpath "dist\EngineerDesk" --hidden-import PySide6 --add-data "resources\sketch;resources\sketch" --clean main.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   Build SUCCESS
    echo   Output: dist\EngineerDesk\EngineerDesk.exe
    echo ========================================
) else (
    echo.
    echo Build FAILED, check errors above
)

pause
