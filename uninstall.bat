@echo off
setlocal enabledelayedexpansion

title Volumenodex Uninstaller
cls
echo ======================================================================
echo                     Volumenodex Uninstaller
echo ======================================================================
echo.
set "TARGET_DIR=%LOCALAPPDATA%\Programs\Volumenodex"

echo This will remove Volumenodex and all its desktop shortcuts.
set /p CONFIRM="Are you sure you want to uninstall Volumenodex? (Y/N): "
if /i not "!CONFIRM!"=="Y" (
    echo Uninstallation cancelled.
    pause
    exit /b 0
)

echo.
echo [*] Removing shortcuts...
del /f /q "%USERPROFILE%\Desktop\Volumenodex.lnk" >nul 2>&1
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Volumenodex.lnk" >nul 2>&1

echo [*] Removing program files...
if exist "%TARGET_DIR%" (
    rmdir /s /q "%TARGET_DIR%" >nul 2>&1
)

echo.
echo ======================================================================
echo                 Uninstallation Complete!
echo ======================================================================
echo.
pause
exit /b 0
