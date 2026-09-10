# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Motor Spares System
# Run: pyinstaller motor_spares.spec

block_cipher = None

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
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['pytest', 'tests', '_pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MotorSparesSystem',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icons/favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='MotorSparesSystem',
)
