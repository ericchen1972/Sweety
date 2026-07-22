from __future__ import annotations

import importlib

import pytest
import requests

from sweety_app.updates import UpdateState, check_remote_update, normalize_manifest, parse_version


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if self.error:
            raise self.error
        return self.response


def manifest(version="1.10.0", downloads=None):
    return {
        "latestVersion": version,
        "downloads": downloads
        or {
            "windows": "https://downloads.example.test/Sweety.exe",
            "macos": "https://downloads.example.test/Sweety.dmg",
        },
    }


def test_remote_update_url_uses_stripped_environment_value(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setenv("SWEETY_UPDATE_URL", "  https://updates.example.test/manifest.json  ")
        config = importlib.reload(importlib.import_module("sweety_app.config"))
        assert config.REMOTE_UPDATE_URL == "https://updates.example.test/manifest.json"
    importlib.reload(config)


def test_remote_update_url_uses_default_when_environment_is_missing(monkeypatch):
    with monkeypatch.context() as patch:
        patch.delenv("SWEETY_UPDATE_URL", raising=False)
        config = importlib.reload(importlib.import_module("sweety_app.config"))
        assert config.REMOTE_UPDATE_URL == "https://sweety.tw/sweety-update.json"
    importlib.reload(config)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1.10.0", (1, 10, 0)),
        ("0.0.0", (0, 0, 0)),
    ],
)
def test_parse_version_accepts_three_numeric_parts(value, expected):
    assert parse_version(value) == expected


@pytest.mark.parametrize("value", ["1.0", "v1.0.1", "1.0.1-rc", "-1.0.1", "1.0.1.0", 101, None])
def test_parse_version_rejects_non_standard_values(value):
    assert parse_version(value) is None


def test_normalize_manifest_marks_newer_numeric_version_available_in_supported_order():
    result = normalize_manifest(
        manifest(
            downloads={
                "macos": "https://downloads.example.test/Sweety.dmg",
                "windows": "https://downloads.example.test/Sweety.exe",
            }
        ),
        "1.9.9",
    )

    assert result == {
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.10.0",
        "downloads": {
            "windows": "https://downloads.example.test/Sweety.exe",
            "macos": "https://downloads.example.test/Sweety.dmg",
        },
    }


@pytest.mark.parametrize(
    ("payload", "current_version"),
    [
        (manifest("1.0.0"), "1.0.0"),
        (manifest("0.9.9"), "1.0.0"),
        (manifest("invalid"), "1.0.0"),
        (manifest(), "invalid"),
        ({}, "1.0.0"),
        (None, "1.0.0"),
    ],
)
def test_normalize_manifest_rejects_equal_older_invalid_or_empty_data(payload, current_version):
    assert normalize_manifest(payload, current_version) == {"checked": True, "updateAvailable": False}


def test_normalize_manifest_rejects_http_download_urls():
    assert normalize_manifest(
        manifest(downloads={"windows": "http://downloads.example.test/Sweety.exe"}),
        "1.0.0",
    ) == {"checked": True, "updateAvailable": False}


def test_normalize_manifest_allows_one_supported_platform():
    assert normalize_manifest(
        manifest(downloads={"macos": "https://downloads.example.test/Sweety.dmg"}),
        "1.0.0",
    ) == {
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.10.0",
        "downloads": {"macos": "https://downloads.example.test/Sweety.dmg"},
    }


def test_normalize_manifest_omits_unknown_platforms_and_invalid_urls():
    assert normalize_manifest(
        manifest(
            downloads={
                "linux": "https://downloads.example.test/Sweety.AppImage",
                "windows": "https://downloads.example.test/Sweety.exe",
                "macos": "https:///missing-host.dmg",
            }
        ),
        "1.0.0",
    ) == {
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.10.0",
        "downloads": {"windows": "https://downloads.example.test/Sweety.exe"},
    }


def test_update_state_only_accepts_its_first_finish_and_returns_defensive_copies():
    state = UpdateState()

    assert state.snapshot() == {"checked": False, "updateAvailable": False}
    state.finish({"checked": True, "updateAvailable": True, "downloads": {"windows": "https://example.test"}})
    first = state.snapshot()
    first["downloads"]["windows"] = "https://changed.example.test"
    state.finish({"checked": True, "updateAvailable": False})

    assert state.snapshot() == {
        "checked": True,
        "updateAvailable": True,
        "downloads": {"windows": "https://example.test"},
    }


def test_check_remote_update_makes_one_timed_request_and_finishes_normalized_result():
    state = UpdateState()
    session = FakeSession(FakeResponse(manifest()))

    check_remote_update(state, "1.0.0", "https://updates.example.test/manifest.json", session=session)

    assert session.calls == [{"url": "https://updates.example.test/manifest.json", "timeout": 5}]
    assert state.snapshot()["updateAvailable"] is True


def test_check_remote_update_converts_network_failure_into_checked_no_update():
    state = UpdateState()

    check_remote_update(
        state,
        "1.0.0",
        "https://updates.example.test/manifest.json",
        session=FakeSession(error=requests.Timeout("offline")),
    )

    assert state.snapshot() == {"checked": True, "updateAvailable": False}
