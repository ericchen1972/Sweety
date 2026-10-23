# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parents[1]
BUILD = Path(os.environ['SWEETY_BUILD_ROOT'])
ok_data, ok_binaries, ok_imports = collect_all('okline')
datas = ok_data + [
    (str(BUILD / 'frontend'), 'frontend'),
    (str(ROOT / 'web/images/logo.png'), '.'),
    (str(BUILD / 'runtime-config.json'), '.'),
    (str(BUILD / 'third-party'), 'third-party'),
]
a = Analysis(
    [str(Path(SPECPATH) / 'launcher.py')],
    pathex=[str(Path(SPECPATH) / 'src')],
    binaries=ok_binaries + [(str(BUILD / 'node/node.exe'), 'runtime')],
    datas=datas,
    hiddenimports=ok_imports + ['keyring.backends.Windows', 'win32ctypes.pywin32.win32cred',
        'win32ctypes.pywin32.win32api', 'uvicorn.logging', 'uvicorn.loops.asyncio',
        'uvicorn.protocols.http.h11_impl', 'uvicorn.lifespan.on'],
    excludes=['sweety_app.__main__', 'sweety_app.panel', 'sweety_app.permissions',
        'sweety_app.microphone', 'AppKit', 'Foundation', 'objc', 'numpy',
        'onnxruntime', 'rapidocr_onnxruntime', 'pyautogui', 'mss'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Sweety',
          console=False, debug=False, strip=False, upx=False,
          icon=str(BUILD / 'Sweety.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Sweety')
