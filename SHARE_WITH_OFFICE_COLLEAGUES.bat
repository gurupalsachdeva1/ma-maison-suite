@echo off
title Share Ma Maison with Office Colleagues
color 0A

echo ===============================================================================
echo        👥 MA MAISON SUITE • OFFICE LAN CONNECTION GUIDE
echo ===============================================================================
cd /d "%~dp0"

echo [*] Detecting your Office Local Network (LAN) IP Address...
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0.*0.0.0.0') do set MY_IP=%%a

echo.
echo -------------------------------------------------------------------------------
echo   🌐 HOW COLLEAGUES JOIN FROM THEIR COMPUTER:
echo -------------------------------------------------------------------------------
echo   Tell your office colleagues to open their web browser (Chrome / Edge / Firefox)
echo   and type this address:
echo.
echo         http://%MY_IP%:8050
echo.
echo -------------------------------------------------------------------------------
echo   🔐 DEFAULT LOGIN CREDENTIALS:
echo -------------------------------------------------------------------------------
echo   - Sarah M. (Manager):        Username: sarah    Password: sarah123
echo   - Priya K. (Manager):        Username: priya    Password: priya123
echo   - Alex R. (Merchandiser):    Username: alex     Password: alex123
echo   - David L. (Merchandiser):   Username: david    Password: david123
echo   - Administrator:             Username: admin    Password: admin123
echo.
echo   * All changes made by colleagues are saved instantly to the shared SQL database!
echo ===============================================================================
pause

