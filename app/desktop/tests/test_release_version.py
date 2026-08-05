from __future__ import annotations

import json
from pathlib import Path
import tomllib

from sweety_app import config


ROOT = Path(__file__).resolve().parents[3]
DESKTOP_DIR = ROOT / "app" / "desktop"
FRONTEND_DIR = ROOT / "app" / "frontend"


def test_release_version_is_1_0_2_across_product_surfaces():
    pyproject = tomllib.loads((DESKTOP_DIR / "pyproject.toml").read_text())
    frontend_package = json.loads((FRONTEND_DIR / "package.json").read_text())
    frontend_lock = json.loads((FRONTEND_DIR / "package-lock.json").read_text())
    spec = (DESKTOP_DIR / "Sweety.spec").read_text()
    readme = (ROOT / "README.md").read_text()
    windows_deploy = (ROOT / "app" / "tools" / "deploy_windows_release.php").read_text()

    assert config.APP_VERSION == "1.0.2"
    assert pyproject["project"]["version"] == "1.0.2"
    assert frontend_package["version"] == "1.0.2"
    assert frontend_lock["version"] == "1.0.2"
    assert frontend_lock["packages"][""]["version"] == "1.0.2"
    assert '"CFBundleShortVersionString": "1.0.2"' in spec
    assert '"CFBundleVersion": "102"' in spec
    assert "目前版本：`1.0.2`" in readme
    assert "Sweety-Setup-1.0.2-Windows-x64.exe" in windows_deploy
