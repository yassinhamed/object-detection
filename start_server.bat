@echo off
setlocal enabledelayedexpansion

REM Start Video Server on Windows
REM This allows receivers to browse and download recordings from your PC

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ======================================
    echo ERROR: Python not found!
    echo ======================================
    echo Please install Python and add it to PATH.
    echo Download from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Try to get local IP address
setlocal enabledelayedexpansion
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R "IPv4"') do (
    set "IP_ADDR=%%a"
    goto :got_ip
)

:got_ip
if not "!IP_ADDR!"=="" (
    REM Remove leading spaces
    for /f "tokens=* delims= " %%a in ("!IP_ADDR!") do set "IP_ADDR=%%a"
) else (
    set "IP_ADDR=localhost"
)

echo.
echo ========================================
echo 📹 Video Recording Server
echo ========================================
echo.
echo Server will start on:
echo   Local: http://localhost:8000
echo   Network: http://!IP_ADDR!:8000
echo.
echo Receiver can connect using:
echo   python video_client.py !IP_ADDR!:8000
echo.
echo Or open in browser:
echo   http://!IP_ADDR!:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
python video_server.py --host 0.0.0.0 --port 8000

pause

