# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH).parents[1]
app_environment = {
    key: value
    for key, value in {
        "SWEETY_AGNES_KEY": os.getenv("SWEETY_AGNES_KEY", "").strip(),
        "SWEETY_METRICS_APP_TOKEN": os.getenv("SWEETY_METRICS_APP_TOKEN", "").strip(),
    }.items()
    if value
}
datas = [
    (str(ROOT / "app" / "frontend" / "dist"), "frontend"),
    (str(ROOT / "web" / "images" / "logo.png"), "."),
]
binaries = []
hiddenimports = [
    "ApplicationServices",
    "CoreFoundation",
    "Foundation",
    "Quartz",
]

ocr_data, ocr_binaries, ocr_hidden = collect_all("rapidocr_onnxruntime")
datas += ocr_data
binaries += ocr_binaries
hiddenimports += ocr_hidden

a = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="Sweety",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file="Sweety.entitlements",
    icon="build/Sweety.icns",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Sweety",
)
app = BUNDLE(
    coll,
    name="Sweety.app",
    icon="build/Sweety.icns",
    bundle_identifier="tw.sweety.app",
    info_plist={
        "CFBundleDisplayName": "Sweety",
        "CFBundleName": "Sweety",
        "CFBundleShortVersionString": "1.0.1",
        "CFBundleVersion": "101",
        "LSMinimumSystemVersion": "13.0",
        "NSAppleEventsUsageDescription": "Sweety needs permission to operate LINE and System Events for selected anti-scam conversations.",
        "NSHighResolutionCapable": True,
        **(
            {"LSEnvironment": app_environment}
            if app_environment
            else {}
        ),
    },
)
