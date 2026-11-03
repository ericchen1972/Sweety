"""Platform-neutral update presentation shared by desktop hosts."""
from __future__ import annotations

from typing import Any

from .updates import SUPPORTED_PLATFORMS, is_valid_https_url


def panel_update_downloads(update: dict[str, Any]) -> list[tuple[str, str]]:
    if not update.get("updateAvailable"):
        return []
    downloads = update.get("downloads")
    if not isinstance(downloads, dict):
        return []
    return [
        (platform, url)
        for platform in SUPPORTED_PLATFORMS
        if is_valid_https_url(url := downloads.get(platform))
    ]


def panel_update_copy(locale: str, update: dict[str, Any]) -> dict[str, str]:
    version = str(update.get("latestVersion", ""))
    if locale == "zh-TW":
        return {
            "heading": f"新版 {version}，立即下載",
            "note": "文字功能只需登入 LINE，不需要桌面操作權限。",
            "emphasis": "不需要桌面操作權限",
            "windows": "Win 版",
            "macos": "Mac OS 版",
        }
    if locale == "ja":
        return {
            "heading": f"バージョン {version} をダウンロードできます",
            "note": "文字機能はLINEログインのみで利用できます。",
            "emphasis": "LINEログイン",
            "windows": "Windows版",
            "macos": "Mac OS版",
        }
    return {
        "heading": f"Version {version} is ready to download",
        "note": "Text features only require LINE sign-in. No desktop control permissions needed.",
        "emphasis": "No desktop control permissions needed",
        "windows": "Windows",
        "macos": "Mac OS",
    }


