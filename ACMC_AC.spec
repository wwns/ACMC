# -*- mode: python ; coding: utf-8 -*-
# ACMC - Bramka Modbus LG
# PyInstaller specification file
# Build: pyinstaller ACMC_AC.spec

a = Analysis(
    ['acmc_app_pl.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('acmc.ico', '.'),
        ('acmc.png', '.'),
        ('LG.png', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk', 
        'tkinter.scrolledtext',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'pymodbus',
        'sqlite3',
        'PIL',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='ACMC_AC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='acmc.ico',
)
