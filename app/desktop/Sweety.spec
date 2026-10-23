# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH).parents[1]
BUILD_ROOT = Path(os.getenv("SWEETY_BUILD_ROOT", "/Users/eric/Documents/Codex-Temp/sweety-build"))
BUILD_ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(SPECPATH) / "src"))
from sweety_app.okline_session import node_path
app_environment = {
    key: value
    for key, value in {
        "SWEETY_METRICS_APP_TOKEN": os.getenv("SWEETY_METRICS_APP_TOKEN", "").strip(),
        "SWEETY_LOG_ENABLED": os.getenv("SWEETY_LOG_ENABLED", "0").strip(),
    }.items()
    if value
}
datas = [
    (os.getenv("SWEETY_FRONTEND_DIST", str(ROOT / "app" / "frontend" / "dist")), "frontend"),
    (str(ROOT / "web" / "images" / "logo.png"), "."),
    (str(ROOT / "assets" / "panel-background.png"), "assets"),
]
binaries = [(node_path(), "runtime")]
node_license = BUILD_ROOT / "Node-LICENSE.txt"
node_license.write_bytes((Path(node_path()).resolve().parent.parent / "LICENSE").read_bytes())
datas += [(str(node_license), "third-party"), (str(ROOT / "docs" / "third-party-okline.md"), "third-party")]
okline_data, okline_binaries, okline_hidden = collect_all("okline")
datas += okline_data
binaries += okline_binaries
hiddenimports = [*okline_hidden, "qrcode", "keyring.backends.macOS", "cryptography.fernet", "AppKit", "Foundation"]

a = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["rapidocr_onnxruntime", "onnxruntime", "numpy", "pyautogui", "mss"],
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
    icon=str(BUILD_ROOT / "Sweety.icns"),
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
    icon=str(BUILD_ROOT / "Sweety.icns"),
    bundle_identifier="tw.sweety.app",
    info_plist={
        "CFBundleDisplayName": "Sweety",
        "CFBundleName": "Sweety",
        "CFBundleShortVersionString": "2.0.0",
        "CFBundleVersion": "200",
        "LSMinimumSystemVersion": "13.0",
        "NSHighResolutionCapable": True,
        **(
            {"LSEnvironment": app_environment}
            if app_environment
            else {}
        ),
    },
)
