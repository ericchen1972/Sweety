from __future__ import annotations

import json
from pathlib import Path
import tomllib

from sweety_app import config


ROOT = Path(__file__).resolve().parents[3]
DESKTOP_DIR = ROOT / "app" / "desktop"
FRONTEND_DIR = ROOT / "app" / "frontend"


def test_release_version_is_1_0_1_across_product_surfaces():
    pyproject = tomllib.loads((DESKTOP_DIR / "pyproject.toml").read_text())
    frontend_package = json.loads((FRONTEND_DIR / "package.json").read_text())
    frontend_lock = json.loads((FRONTEND_DIR / "package-lock.json").read_text())
    spec = (DESKTOP_DIR / "Sweety.spec").read_text()

    assert config.APP_VERSION == "1.0.1"
    assert pyproject["project"]["version"] == "1.0.1"
    assert frontend_package["version"] == "1.0.1"
    assert frontend_lock["version"] == "1.0.1"
    assert frontend_lock["packages"][""]["version"] == "1.0.1"
    assert '"CFBundleShortVersionString": "1.0.1"' in spec
    assert '"CFBundleVersion": "101"' in spec
