import pytest

from sweety_app.updates import UpdateState, check_remote_update, normalize_manifest


def manifest():
    return {
        "latestVersion": "9.0.0",  # Legacy fields must never drive new clients.
        "downloads": {"windows": "https://example.test/legacy.exe"},
        "platforms": {
            "windows": {"latestVersion": "2.0.3", "downloadUrl": "https://example.test/win.exe"},
            "macos": {"latestVersion": "2.0.2", "downloadUrl": "https://example.test/mac.dmg"},
        },
    }


@pytest.mark.parametrize("platform,available", [("windows", True), ("macos", False)])
def test_only_updated_platform_is_notified(platform, available):
    result = normalize_manifest(manifest(), "2.0.2", platform=platform)
    assert result["updateAvailable"] is available
    if available:
        assert result["latestVersion"] == "2.0.3"
        assert result["downloads"] == {platform: "https://example.test/win.exe"}


def test_mac_release_does_not_notify_windows():
    payload = manifest()
    payload["platforms"]["macos"]["latestVersion"] = "2.0.4"
    payload["platforms"]["windows"]["latestVersion"] = "2.0.2"
    assert not normalize_manifest(payload, "2.0.2", platform="windows")["updateAvailable"]
    assert normalize_manifest(payload, "2.0.2", platform="macos")["downloads"] == {
        "macos": "https://example.test/mac.dmg"
    }


@pytest.mark.parametrize("entry", [None, {}, "bad", {"latestVersion": "2.0.3", "downloadUrl": "http://example.test"},
                                       {"latestVersion": "bad", "downloadUrl": "https://example.test"}])
def test_invalid_own_platform_never_falls_back(entry):
    payload = manifest()
    payload["platforms"]["windows"] = entry
    assert normalize_manifest(payload, "2.0.2", platform="windows") == {"checked": True, "updateAvailable": False}


@pytest.mark.parametrize("runtime,expected", [("win32", "windows"), ("darwin", "macos"), ("linux", None)])
def test_request_uses_runtime_platform(monkeypatch, runtime, expected):
    import sweety_app.updates as updates
    monkeypatch.setattr(updates.sys, "platform", runtime)
    class Response:
        def raise_for_status(self): pass
        def json(self): return manifest()
    class Session:
        def get(self, *args, **kwargs): return Response()
    state = UpdateState()
    check_remote_update(state, "2.0.1", "https://example.test", session=Session())
    result = state.snapshot()
    assert result["updateAvailable"] is bool(expected)
    if expected:
        assert list(result["downloads"]) == [expected]


def test_legacy_manifest_does_not_notify_new_clients():
    assert not normalize_manifest({"latestVersion": "9.0.0", "downloads": {"windows": "https://example.test"}},
                                  "2.0.2", platform="windows")["updateAvailable"]


@pytest.mark.parametrize("newer", ["windows", "macos"])
def test_2_0_3_installations_only_see_own_2_0_4_release(newer):
    payload = manifest()
    for platform in ("windows", "macos"):
        payload["platforms"][platform]["latestVersion"] = "2.0.4" if platform == newer else "2.0.3"
    for platform in ("windows", "macos"):
        result = normalize_manifest(payload, "2.0.3", platform=platform)
        assert result["updateAvailable"] is (platform == newer)
        if platform == newer:
            assert list(result["downloads"]) == [platform]
