@echo off
setlocal enabledelayedexpansion

title Volumenodex Installer
cls
echo ======================================================================
echo                     Volumenodex v1.3.0 Installer
echo ======================================================================
echo.
echo Installing Volumenodex to your local application directory...
echo.

set "SOURCE_DIR=%~dp0Volumenodex"
set "TARGET_DIR=%LOCALAPPDATA%\Programs\Volumenodex"
set "ICON_SRC=%~dp0app_icon.ico"

if not exist "%SOURCE_DIR%\Volumenodex.exe" (
    echo [ERROR] Could not find Volumenodex files in "%SOURCE_DIR%".
    echo Please make sure the 'Volumenodex' folder is in the same directory as this script.
    echo.
    pause
    exit /b 1
)

:: Create target directory
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

:: Copy application files
echo [*] Copying application files...
robocopy "%SOURCE_DIR%" "%TARGET_DIR%" /E /R:2 /W:1 /NP /NDL /NFL >nul
if %ERRORLEVEL% GEQ 8 (
    echo [ERROR] Failed to copy files to "%TARGET_DIR%".
    pause
    exit /b 1
)

:: Copy icon if available
if exist "%ICON_SRC%" (
    copy /y "%ICON_SRC%" "%TARGET_DIR%\app_icon.ico" >nul
)

:: Create Desktop shortcut
echo [*] Creating Desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$sc = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Volumenodex.lnk')); " ^
    "$sc.TargetPath = '%TARGET_DIR%\Volumenodex.exe'; " ^
    "$sc.WorkingDirectory = '%TARGET_DIR%'; " ^
    "if (Test-Path '%TARGET_DIR%\app_icon.ico') { $sc.IconLocation = '%TARGET_DIR%\app_icon.ico,0' }; " ^
    "$sc.Description = 'Volumenodex Writer Reference'; " ^
    "$sc.Save()"

:: Create Start Menu shortcut
echo [*] Creating Start Menu shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$startDir = [IO.Path]::Combine([Environment]::GetFolderPath('StartMenu'), 'Programs'); " ^
    "if (-not (Test-Path $startDir)) { New-Item -ItemType Directory -Path $startDir -Force | Out-Null }; " ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$sc = $ws.CreateShortcut([IO.Path]::Combine($startDir, 'Volumenodex.lnk')); " ^
    "$sc.TargetPath = '%TARGET_DIR%\Volumenodex.exe'; " ^
    "$sc.WorkingDirectory = '%TARGET_DIR%'; " ^
    "if (Test-Path '%TARGET_DIR%\app_icon.ico') { $sc.IconLocation = '%TARGET_DIR%\app_icon.ico,0' }; " ^
    "$sc.Description = 'Volumenodex Writer Reference'; " ^
    "$sc.Save()"

:: Copy uninstaller to target
copy /y "%~dp0uninstall.bat" "%TARGET_DIR%\uninstall.bat" >nul 2>&1

echo.
echo ======================================================================
echo                  Installation Complete!
echo ======================================================================
echo.
echo Volumenodex has been successfully installed to:
echo   %TARGET_DIR%
echo.
echo Shortcuts have been added to your Desktop and Start Menu.
echo.
set /p LAUNCH="Would you like to launch Volumenodex now? (Y/N, default Y): "
if /i "!LAUNCH!"=="" set LAUNCH=Y
if /i "!LAUNCH!"=="Y" (
    start "" "%TARGET_DIR%\Volumenodex.exe"
)
exit /b 0
