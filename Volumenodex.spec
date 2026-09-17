# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files

# Determine icon by platform
if sys.platform == 'darwin':
    app_icon = 'assets/app_icon.icns'
elif sys.platform == 'win32':
    app_icon = 'assets/app_icon.ico'
else:
    app_icon = 'assets/icon.png'

if not os.path.exists(app_icon):
    app_icon = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('volumenodex/reference/bundled_knowledge.json', 'volumenodex/reference'),
        ('volumenodex/resources', 'volumenodex/resources'),
    ] + collect_data_files('spellchecker'),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Volumenodex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Volumenodex',
)

# macOS Application Bundle (.app)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Volumenodex.app',
        icon=app_icon,
        bundle_identifier='com.volumenodex.studio',
        info_plist={
            'CFBundleName': 'Volumenodex',
            'CFBundleDisplayName': 'Volumenodex Word Studio',
            'CFBundleVersion': '1.2.0',
            'CFBundleShortVersionString': '1.2.0',
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
        },
    )
