@echo off
setlocal
cd /d "%~dp0"
set "PY_EXE=C:\Users\thele\AppData\Local\Programs\Python\Python312\pythonw.exe"
if not exist "%PY_EXE%" set "PY_EXE=pythonw.exe"

start "" "%PY_EXE%" "tools\reference_builder.py" %*
