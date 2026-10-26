from __future__ import annotations

import os
import sys
import json
from pathlib import Path


APP_NAME = "Sweety"
APP_VERSION = "2.0.1"
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
ABOUT_SWEETY_JA_URL = os.getenv("SWEETY_ABOUT_JA_URL", "https://sweety.tw/about_sweety_ja.html")

PROJECT_DIR = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[4]
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

PANEL_BACKGROUND_PATH = RESOURCE_DIR / "assets" / "panel-background.png"

if sys.platform == "darwin":
    DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
    CACHE_DIR = Path.home() / "Library" / "Caches" / APP_NAME
    LOG_DIR = Path.home() / "Library" / "Logs" / APP_NAME
else:
    DATA_DIR = Path.home() / f".{APP_NAME.lower()}"
    CACHE_DIR = DATA_DIR / "cache"
    LOG_DIR = DATA_DIR / "logs"

DATABASE_PATH = DATA_DIR / "sweety.sqlite3"
LOG_PATH = LOG_DIR / "sweety.log"
BUNDLED_AGNES_KEY = os.getenv("SWEETY_AGNES_KEY", "").strip()
def _bundled_log_setting() -> str:
    if getattr(sys, "frozen", False):
        try:
            settings = json.loads((RESOURCE_DIR / "runtime-config.json").read_text(encoding="utf-8"))
            return str(settings.get("SWEETY_LOG_ENABLED", "0"))
        except (OSError, ValueError, AttributeError):
            pass
    return "0"


LOG_ENABLED = os.getenv("SWEETY_LOG_ENABLED", _bundled_log_setting()).strip() == "1"


def normalize_locale(identifier: str | None) -> str:
    language = (identifier or "").replace("_", "-").lower()
    if language == "zh-tw" or language.startswith("zh-hant"):
        return "zh-TW"
    if language == "ja" or language.startswith("ja-"):
        return "ja"
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


def about_url_for_locale(locale: str) -> str:
    return ABOUT_SWEETY_JA_URL if normalize_locale(locale) == "ja" else ABOUT_SWEETY_URL
