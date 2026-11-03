from __future__ import annotations

import re
import sys
from threading import Lock
from typing import Any, Protocol
from urllib.parse import urlparse

import requests


SUPPORTED_PLATFORMS = ("windows", "macos")
_VERSION_PATTERN = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)")


class HttpSession(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


def parse_version(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def normalize_manifest(payload: Any, current_version: Any, *, platform: str | None = None) -> dict[str, Any]:
    platform = platform if platform is not None else {"win32": "windows", "darwin": "macos"}.get(sys.platform)
    if platform not in SUPPORTED_PLATFORMS or not isinstance(payload, dict):
        return _no_update()
    platforms = payload.get("platforms")
    if not isinstance(platforms, dict):
        return _no_update()
    release = platforms.get(platform)
    if not isinstance(release, dict):
        return _no_update()
    latest_version = release.get("latestVersion")
    parsed_current = parse_version(current_version)
    parsed_latest = parse_version(latest_version)
    if parsed_current is None or parsed_latest is None or parsed_latest <= parsed_current:
        return _no_update()
    url = release.get("downloadUrl")
    if not is_valid_https_url(url):
        return _no_update()
    return {
        "checked": True,
        "updateAvailable": True,
        "latestVersion": latest_version,
        "downloads": {platform: url},
    }


def is_valid_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


class UpdateState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._finished = False
        self._result: dict[str, Any] = {"checked": False, "updateAvailable": False}

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return _copy_result(self._result)

    def finish(self, result: dict[str, Any]) -> None:
        with self._lock:
            if self._finished:
                return
            self._result = _copy_result(result)
            self._finished = True


def check_remote_update(
    state: UpdateState,
    current_version: str,
    url: str,
    *,
    session: HttpSession | None = None,
) -> None:
    try:
        client = session if session is not None else requests.Session()
        response = client.get(url, timeout=5)
        response.raise_for_status()
        state.finish(normalize_manifest(response.json(), current_version))
    except Exception:
        state.finish(_no_update())


def _no_update() -> dict[str, bool]:
    return {"checked": True, "updateAvailable": False}


def _copy_result(result: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(result)
    downloads = snapshot.get("downloads")
    if isinstance(downloads, dict):
        snapshot["downloads"] = dict(downloads)
    return snapshot
