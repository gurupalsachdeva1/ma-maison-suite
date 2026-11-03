@echo off
title Ma Maison • EXECUTIVE BI SUITE (Desktop & Office LAN)
color 0B

echo ===============================================================================
echo        🏢 MA MAISON • EXECUTIVE BI SUITE (DESKTOP & SQL MULTI-USER)
echo ===============================================================================
echo [*] Working directory: %~dp0
cd /d "%~dp0"

echo [*] Checking if Python is installed...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH! Please install Python 3.9+.
    pause
    exit /b 1
)

echo [*] Checking if Port 8050 server is active...
netstat -ano | findstr /R /C:":8050 .*LISTENING" >nul 2>&1

if %errorlevel% equ 0 (
    echo [OK] Ma Maison Backend Server is ALREADY RUNNING on Port 8050!
) else (
    echo [*] Starting Ma Maison Multi-User SQL Backend Server on 0.0.0.0:8050...
    start "Ma_Maison_SQL_Backend" /min cmd /c "python -m uvicorn app:app --host 0.0.0.0 --port 8050"
    echo [*] Waiting 3 seconds for server to initialize...
    timeout /t 3 /nobreak >nul
)

echo [*] Launching Desktop Software Application Window...
python desktop_launcher.py

echo.
echo ===============================================================================
echo   🚀 MA MAISON SUITE IS RUNNING!
echo   - 💻 Desktop Window Opened (Native App Mode)
echo   - 🗄️ SQL Database: ma_maison.db (Local & Secure)
echo   - 🌐 Local URL: http://localhost:8050
echo.
echo   👥 TO SHARE WITH OFFICE COLLEAGUES:
echo      Colleagues on the same office Wi-Fi / LAN can open:
echo      Run 'SHARE_WITH_OFFICE_COLLEAGUES.bat' to view your LAN IP address!
echo ===============================================================================
echo This console will remain running to keep the multi-user server active.
echo Press CTRL+C to stop the server anytime.
pause

