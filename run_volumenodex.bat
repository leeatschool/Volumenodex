@echo off
cd /d "%~dp0"
if exist "volumenodex.pyw" (
    start "" pythonw volumenodex.pyw
) else (
    start "" pythonw main.py
)
exit /b 0
