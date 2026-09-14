"""Helper script to create Desktop shortcuts and launchers for Writers Reference Builder."""

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DESKTOP = Path.home() / "Desktop"
ICON_PATH = REPO_ROOT / "assets" / "writers_reference.ico"
BUILDER_PY = REPO_ROOT / "tools" / "reference_builder.py"
PYTHONW = Path(r"C:\Users\thele\AppData\Local\Programs\Python\Python312\pythonw.exe")
if not PYTHONW.exists():
    PYTHONW = Path("pythonw.exe")


def create_desktop_shortcut():
    shortcut_path = DESKTOP / "Writers Reference Builder.lnk"
    ps1_content = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{str(shortcut_path)}')
$Shortcut.TargetPath = '{str(PYTHONW)}'
$Shortcut.Arguments = '"{str(BUILDER_PY)}"'
$Shortcut.WorkingDirectory = '{str(REPO_ROOT)}'
$Shortcut.IconLocation = '{str(ICON_PATH)}'
$Shortcut.Description = 'Writers Reference Knowledge Base Builder and PDF Ingestor'
$Shortcut.Save()
"""
    ps1_path = REPO_ROOT / "temp_create_shortcut.ps1"
    try:
        with open(ps1_path, "w", encoding="utf-8") as f:
            f.write(ps1_content)
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1_path)], check=True)
        print(f"[OK] Created Desktop Shortcut: {shortcut_path}")
    finally:
        if ps1_path.exists():
            ps1_path.unlink()


def create_batch_launchers():
    # 1. Root batch launcher
    root_bat = REPO_ROOT / "Launch_Reference_Builder.bat"
    root_bat_content = f"""@echo off
setlocal
cd /d "%~dp0"
set "PY_EXE={str(PYTHONW)}"
if not exist "%PY_EXE%" set "PY_EXE=pythonw.exe"

start "" "%PY_EXE%" "tools\\reference_builder.py" %*
"""
    with open(root_bat, "w", encoding="utf-8") as f:
        f.write(root_bat_content)
    print(f"[OK] Created Repository Launcher: {root_bat}")

    # 2. Desktop Drag & Drop Ingestor
    desktop_bat = DESKTOP / "Auto-Ingest PDF (Drag & Drop).bat"
    desktop_bat_content = f"""@echo off
setlocal
cd /d "{str(REPO_ROOT)}"
set "PY_EXE={str(PYTHONW)}"
if not exist "%PY_EXE%" set "PY_EXE=pythonw.exe"

if "%~1"=="" (
    start "" "%PY_EXE%" "tools\\reference_builder.py"
) else (
    start "" "%PY_EXE%" "tools\\reference_builder.py" "%~1"
)
"""
    with open(desktop_bat, "w", encoding="utf-8") as f:
        f.write(desktop_bat_content)
    print(f"[OK] Created Desktop Drag-and-Drop Batch: {desktop_bat}")


if __name__ == "__main__":
    create_desktop_shortcut()
    create_batch_launchers()
