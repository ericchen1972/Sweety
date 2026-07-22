from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "Sweety"
APP_VERSION = "1.0.1"
API_HOST = "127.0.0.1"
API_PORT = 8891
MANAGEMENT_URL = f"http://{API_HOST}:{API_PORT}/"
REMOTE_CATALOG_URL = os.getenv("SWEETY_REMOTE_CATALOG_URL", "https://sweety.tw/sweety-catalog.php")
SWEETY_APP_TOKEN = os.getenv("SWEETY_APP_TOKEN", "sweety-desktop-catalog-v1")
REMOTE_METRICS_URL = os.getenv("SWEETY_REMOTE_METRICS_URL", "https://sweety.tw/sweety-metrics.php")
REMOTE_UPDATE_URL = os.getenv("SWEETY_UPDATE_URL", "https://sweety.tw/sweety-update.json").strip()
SWEETY_METRICS_APP_TOKEN = os.getenv("SWEETY_METRICS_APP_TOKEN", "").strip()
REGION_LOOKUP_URL = os.getenv("SWEETY_REGION_LOOKUP_URL", "https://api.country.is/")
ABOUT_SWEETY_URL = os.getenv("SWEETY_ABOUT_URL", "https://sweety.tw/about_sweety.html")

PROJECT_DIR = Path(__file__).resolve().parents[4]
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_DIR))
FRONTEND_DIST = (
    RESOURCE_DIR / "frontend"
    if getattr(sys, "frozen", False)
    else PROJECT_DIR / "app" / "frontend" / "dist"
)
LOGO_PATH = (
    RESOURCE_DIR / "logo.png"
    if getattr(sys, "frozen", False)
    else PROJECT_DIR / "web" / "images" / "logo.png"
)

if sys.platform == "darwin":
    DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
    CACHE_DIR = Path.home() / "Library" / "Caches" / APP_NAME
else:
    DATA_DIR = Path.home() / f".{APP_NAME.lower()}"
    CACHE_DIR = DATA_DIR / "cache"

DATABASE_PATH = DATA_DIR / "sweety.sqlite3"
BUNDLED_AGNES_KEY = os.getenv("SWEETY_AGNES_KEY", "").strip()


def normalize_locale(identifier: str | None) -> str:
    language = (identifier or "").replace("_", "-").lower()
    if language == "zh-tw" or language.startswith("zh-hant"):
        return "zh-TW"
    return "en"


def preferred_locale(fallback: str | None = None) -> str:
    try:
        from Foundation import NSUserDefaults

        languages = NSUserDefaults.standardUserDefaults().objectForKey_("AppleLanguages") or []
        if languages:
            return normalize_locale(str(languages[0]))
    except ImportError:
        pass
    return normalize_locale(fallback)
