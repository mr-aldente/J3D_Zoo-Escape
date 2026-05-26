# -*- mode: python ; coding: utf-8 -*-
# PyInstaller — Zoo Escape (menu.py)
# Usage : pyinstaller installer/zoo_escape.spec  (depuis la racine du dépôt)

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC = os.path.join(ROOT, "src")

distpath = os.path.join(SPECPATH, "dist")
workpath = os.path.join(SPECPATH, "build")
specpath = SPECPATH

block_cipher = None

added_files = [
    (os.path.join(SRC, "assets"), "assets"),
    (os.path.join(ROOT, "docs", "Map-overall.png"), "."),
]

a = Analysis(
    [os.path.join(SRC, "menu.py")],
    pathex=[SRC, ROOT],
    binaries=[],
    datas=added_files,
    hiddenimports=["cv2", "pygame", "client_reseau", "jeu", "app_paths"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ZooEscape",
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
    icon=None,
)
