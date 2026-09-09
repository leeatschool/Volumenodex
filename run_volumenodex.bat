@echo off
title Volumenodex Word Processing Studio Launcher
cd /d "%~dp0"
echo ===================================================
echo Launching Volumenodex Word Processing Studio...
echo ===================================================

python main.py
if %ERRORLEVEL% NEQ 0 (
    if exist "C:\Users\thele\AppData\Local\Programs\Python\Python312\python.exe" (
        "C:\Users\thele\AppData\Local\Programs\Python\Python312\python.exe" main.py
    ) else (
        echo.
        echo [ERROR] Volumenodex encountered an issue during startup.
        pause
    )
)
