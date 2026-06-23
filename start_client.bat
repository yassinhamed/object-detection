@echo off
REM Video Client Launcher for Windows
REM Automatically discovers and connects to the video server

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python and add it to PATH.
    pause
    exit /b 1
)

echo.
echo ========================================
echo 📥 Video Recording Client
echo ========================================
echo.
echo Auto-discovering server on local network...
echo.

REM Start the client without arguments (auto-discovery)
python video_client.py

pause

