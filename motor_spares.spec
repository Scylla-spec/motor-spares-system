# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Motor Spares System  v2.5.0
# Run: python -m PyInstaller motor_spares.spec

hidden_imports = [
    'managers',
    'models',
    'ui',
    'utils',
    'database',
    'sqlite3',
    'logging',
    'json',
    'csv',
    'pathlib',
    'datetime',
    'bcrypt',
    'openpyxl',
    'thefuzz',
    'thefuzz.fuzz',
    'thefuzz.process',
    'Levenshtein',
    'PIL',
    'PIL.Image',
    'PIL._imaging',
    'reportlab',
    'reportlab.graphics',
    'reportlab.platypus',
    'matplotlib',
    'matplotlib.backends.backend_agg',
]

datas = [
    ('assets', 'assets'),
    ('docs', 'docs'),
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tests', '_pytest'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MotorSparesSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MotorSparesSystem',
)
